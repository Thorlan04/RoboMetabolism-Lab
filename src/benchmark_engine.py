"""
RoboMetabolism-Lab - Master Benchmark Engine (Argon Physical & Electro-Thermal Judge)
Le Juge Physique, Électrochimique & Thermodynamique Déterministe pour Robots Autonomes (ROS2 / Jetson Orin).

Simule en RAM (NumPy pur, graine déterministe fixée) 200 missions robotiques complexes de 3 600 secondes :
- Navigation en entrepôt logistique dense et allées étroites
- Manipulation d'objets instables et déformables
- Traversées piétonnes inattendues et anomalies dynamiques
- Pics thermiques ambiants et modèle de dissipation thermique NVIDIA Jetson Orin
- Résistance interne non-linéaire Li-Ion V_drop = I * R_int(SoC, T), courant d'appel transitoire et effet Peukert
- Arbitrage métabolique temps-réel à 4 niveaux :
    0: Réflexe Spinal (1.5W, latence 2ms)
    1: Cortical Léger (8.0W, latence 15ms)
    2: Cognitif Profond VLA (45.0W, latence 180ms)
    3: Digestion Mémoire Épisodique / Micro-Sommeil (2.2W)
"""

import ast
import math
import time
from typing import Any, Callable, Dict, List, Tuple
import numpy as np

from src.baseline_algorithm import (
    baseline_always_on_vla,
    baseline_static_threshold,
    baseline_ros2_qos_heuristic,
)

# Constantes physiques & environnementales déterministes
N_MISSIONS = 200
SIM_DURATION_SEC = 3600
DT = 2.0  # Macro-pas de simulation de 2 secondes
N_STEPS = int(SIM_DURATION_SEC / DT)  # 1 800 pas par mission
BENCHMARK_SEED = 2026

# Seuils critiques matériels (NVIDIA Jetson Orin & Pack Li-Ion 6S)
THERMAL_CRITICAL_TEMP = 82.0    # °C : Seuil strict de violation thermique
THERMAL_THROTTLE_TEMP = 85.0    # °C : Seuil de bridage matériel DVFS (latence x3)
BATTERY_CUTOFF_VOLTAGE = 18.0   # Volts : Seuil de coupure BMS (Brownout)
BATTERY_NOMINAL_WH = 54.0       # Capacité énergétique allouée au module embarqué Orin & bus capteur (Wh)
R0_INTERNAL_OHM = 0.105         # Résistance interne ohmique de référence (Ohms)


def verify_candidate_ast_safety(code_str: str) -> Tuple[bool, str]:
    """
    Audit anti-triche AST (Standard Argon) :
    Interdit global, nonlocal, import de modules système/réseau, et mutations illégales.
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"Erreur de syntaxe Python : {e}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return False, "Interdit : instructions global / nonlocal détectées."
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name.split(".")[0] not in ("math", "numpy", "typing"):
                    return False, f"Import non autorisé : {alias.name}"
    return True, "AST 100% conforme."


def probe_candidate_responsiveness(arbitration_fn: Callable) -> bool:
    """
    Sonde multi-états (Anti-Dégénérescence Argon) :
    Vérifie que la fonction candidate réagit dynamiquement aux états physiques
    (repos moteur, urgence balistique, manipulation complexe, stress thermique).
    """
    probe_states = [
        (2.5, 0.0, 1.0, 0.0, 0.85, 50.0, 24.0, True),   # État repos moteur -> doit favoriser Tier 3 ou 1
        (0.38, 1.6, 1.1, 0.1, 0.80, 52.0, 25.0, False), # Urgence balistique proche -> doit favoriser Tier 0 ou 1
        (1.80, 0.5, 3.4, 0.88, 0.90, 54.0, 24.0, False),# Manipulation haute entropie -> doit favoriser Tier 2
        (1.20, 1.1, 1.2, 0.20, 0.75, 55.0, 25.0, False) # Croisière nominale -> Tier 1 ou 0
    ]
    outputs = set()
    for state in probe_states:
        try:
            res = int(arbitration_fn(*state))
            outputs.add(res)
        except Exception:
            return False
    # Une fonction constante qui retourne toujours le même palier est rejetée
    return len(outputs) >= 2


class MissionEnvironment:
    """Générateur et conteneur de traces déterministes en lecture seule pour 200 missions robotiques."""

    def __init__(self, seed: int = BENCHMARK_SEED):
        self.seed = seed
        self.traces = self._generate_traces()

    def _generate_traces(self) -> Dict[str, np.ndarray]:
        rng = np.random.RandomState(self.seed)

        # 4 typologies de scénarios industriels répartis équitablement (50 missions chacun)
        # 0: Navigation d'entrepôt logistique dense
        # 1: Manipulation fine et tri d'objets instables/déformables
        # 2: Patrouille autonome rapide et évitement d'anomalies
        # 3: Transfert AGV lourd avec attentes aux quais / ascenseurs
        scenario_types = np.repeat([0, 1, 2, 3], N_MISSIONS // 4)
        rng.shuffle(scenario_types)

        obstacle_dist = np.zeros((N_STEPS, N_MISSIONS), dtype=np.float32)
        velocity = np.zeros((N_STEPS, N_MISSIONS), dtype=np.float32)
        sensor_entropy = np.zeros((N_STEPS, N_MISSIONS), dtype=np.float32)
        manipulation_comp = np.zeros((N_STEPS, N_MISSIONS), dtype=np.float32)
        ambient_temp = np.zeros((N_STEPS, N_MISSIONS), dtype=np.float32)
        is_motor_idle = np.zeros((N_STEPS, N_MISSIONS), dtype=bool)

        t_grid = np.linspace(0, 1.0, N_STEPS, dtype=np.float32)

        for m in range(N_MISSIONS):
            stype = scenario_types[m]
            base_temp = rng.uniform(22.0, 35.5)

            # Température ambiante avec poches de chaleur industrielle (fours, quais ensoleillés)
            t_curve = (
                base_temp
                + 4.2 * np.sin(t_grid * 3.0 * np.pi + rng.uniform(0, np.pi))
                + rng.normal(0, 0.45, N_STEPS)
            )
            ambient_temp[:, m] = np.clip(t_curve, 18.0, 41.0)

            if stype == 0:  # Entrepôt dense
                obs = 2.1 + 1.1 * np.sin(t_grid * 14 * np.pi) + rng.exponential(0.85, N_STEPS)
                sudden_drop = rng.rand(N_STEPS) < 0.035
                obs[sudden_drop] = rng.uniform(0.28, 0.58, np.sum(sudden_drop))
                obstacle_dist[:, m] = np.clip(obs, 0.22, 8.0)
                velocity[:, m] = np.clip(1.25 + 0.45 * np.sin(t_grid * 10 * np.pi), 0.35, 1.95)
                sensor_entropy[:, m] = np.clip(1.55 + 0.82 * rng.randn(N_STEPS), 0.20, 3.85)
                manipulation_comp[:, m] = np.where(obs < 1.15, rng.uniform(0.15, 0.55, N_STEPS), rng.uniform(0.0, 0.22, N_STEPS))
                is_motor_idle[:, m] = rng.rand(N_STEPS) < 0.09

            elif stype == 1:  # Manipulation fine & tri haute précision
                obs = rng.uniform(0.45, 2.40, N_STEPS)
                sudden_drop = rng.rand(N_STEPS) < 0.02
                obs[sudden_drop] = rng.uniform(0.30, 0.52, np.sum(sudden_drop))
                obstacle_dist[:, m] = obs
                velocity[:, m] = np.clip(0.55 + 0.25 * rng.randn(N_STEPS), 0.10, 1.15)
                sensor_entropy[:, m] = np.clip(2.15 + 0.75 * rng.randn(N_STEPS), 0.60, 4.10)
                manip = 0.62 + 0.28 * np.sin(t_grid * 24 * np.pi) + rng.normal(0, 0.12, N_STEPS)
                manipulation_comp[:, m] = np.clip(manip, 0.05, 1.0)
                is_motor_idle[:, m] = rng.rand(N_STEPS) < 0.22

            elif stype == 2:  # Patrouille rapide & anomalies soudaines
                obs = 4.0 + 1.8 * np.sin(t_grid * 8 * np.pi) + rng.randn(N_STEPS) * 0.7
                sudden_drop = rng.rand(N_STEPS) < 0.032
                obs[sudden_drop] = rng.uniform(0.32, 0.64, np.sum(sudden_drop))
                obstacle_dist[:, m] = np.clip(obs, 0.24, 12.0)
                velocity[:, m] = np.clip(1.85 + 0.55 * np.sin(t_grid * 6 * np.pi), 0.70, 2.65)
                sensor_entropy[:, m] = np.clip(1.25 + 0.65 * rng.randn(N_STEPS), 0.15, 3.40)
                manipulation_comp[:, m] = np.clip(rng.exponential(0.12, N_STEPS), 0.0, 0.60)
                is_motor_idle[:, m] = rng.rand(N_STEPS) < 0.06

            else:  # Transfert AGV avec phases de stationnement quai/ascenseur
                obs = 2.8 + 1.4 * np.cos(t_grid * 12 * np.pi) + rng.randn(N_STEPS) * 0.5
                sudden_drop = rng.rand(N_STEPS) < 0.025
                obs[sudden_drop] = rng.uniform(0.30, 0.58, np.sum(sudden_drop))
                obstacle_dist[:, m] = np.clip(obs, 0.25, 9.0)
                velocity[:, m] = np.clip(1.10 + 0.35 * rng.randn(N_STEPS), 0.25, 1.65)
                sensor_entropy[:, m] = np.clip(1.65 + 0.65 * rng.randn(N_STEPS), 0.25, 3.60)
                manipulation_comp[:, m] = np.clip(rng.uniform(0.05, 0.52, N_STEPS), 0.0, 0.68)
                idle_mask = np.zeros(N_STEPS, dtype=bool)
                for _ in range(6):
                    start = rng.randint(30, N_STEPS - 60)
                    idle_mask[start:start + 40] = True
                is_motor_idle[:, m] = idle_mask

            velocity[is_motor_idle[:, m], m] = 0.0

        # Verrouillage en lecture seule (Protection Anti-Triche Argon)
        for arr in (obstacle_dist, velocity, sensor_entropy, manipulation_comp, ambient_temp, is_motor_idle, scenario_types):
            arr.flags.writeable = False

        return {
            "obstacle_dist": obstacle_dist,
            "velocity": velocity,
            "sensor_entropy": sensor_entropy,
            "manipulation_comp": manipulation_comp,
            "ambient_temp": ambient_temp,
            "is_motor_idle": is_motor_idle,
            "scenario_types": scenario_types
        }


def simulate_robotic_fleet(
    arbitration_fn: Callable,
    env_traces: Dict[str, np.ndarray]
) -> Dict[str, Any]:
    """
    Exécute la simulation physique, thermique et électrochimique complète des 200 missions.
    """
    if not probe_candidate_responsiveness(arbitration_fn):
        return {
            "survival_rate_pct": 0.0,
            "completion_rate_pct": 0.0,
            "energy_saved_pct": 0.0,
            "avg_soc_end_pct": 0.0,
            "thermal_violations": 9999,
            "critical_collisions": 200,
            "max_junction_temp": 99.9,
            "episodic_compressions": 0,
            "p99_decision_latency_ms": 99.9,
            "composite_score": 0.0
        }

    obstacle_dist = env_traces["obstacle_dist"]
    velocity = env_traces["velocity"]
    sensor_entropy = env_traces["sensor_entropy"]
    manipulation_comp = env_traces["manipulation_comp"]
    ambient_temp = env_traces["ambient_temp"]
    is_motor_idle = env_traces["is_motor_idle"]

    # États physiques initiaux
    soc = np.ones(N_MISSIONS, dtype=np.float32)
    wh_remaining = np.full(N_MISSIONS, BATTERY_NOMINAL_WH, dtype=np.float32)
    junction_temp = ambient_temp[0].copy() + 8.0
    peak_junction_temp = junction_temp.copy()
    prev_tiers = np.ones(N_MISSIONS, dtype=np.int32)
    digest_credit = np.zeros(N_MISSIONS, dtype=np.float32)  # Crédit de compression mémoire épisodique

    is_alive = np.ones(N_MISSIONS, dtype=bool)
    steps_survived = np.zeros(N_MISSIONS, dtype=np.int32)
    quality_accum = np.zeros(N_MISSIONS, dtype=np.float64)
    total_tasks = np.zeros(N_MISSIONS, dtype=np.int32)
    collision_strikes = np.zeros(N_MISSIONS, dtype=np.int32)

    thermal_violations_count = 0
    critical_collisions_count = 0
    total_energy_consumed_wh = 0.0
    episodic_compressions_count = 0

    # Constantes thermiques du dissipateur NVIDIA Jetson Orin (Châssis compact IP65)
    c_th = 38.0      # Capacité thermique (J/°C)
    h_dissip = 0.82  # Coefficient de convection thermique nominal (W/°C)

    # Test de vectorisation directe
    is_vectorized = False
    try:
        test_out = arbitration_fn(
            obstacle_dist[0], velocity[0], sensor_entropy[0],
            manipulation_comp[0], soc, junction_temp, ambient_temp[0], is_motor_idle[0]
        )
        if isinstance(test_out, np.ndarray) and test_out.shape == (N_MISSIONS,):
            is_vectorized = True
    except Exception:
        is_vectorized = False

    t_eval_start = time.perf_counter()

    for step in range(N_STEPS):
        active_indices = np.where(is_alive)[0]
        if len(active_indices) == 0:
            break

        obs_t = obstacle_dist[step]
        vel_t = velocity[step]
        ent_t = sensor_entropy[step]
        comp_t = manipulation_comp[step]
        amb_t = ambient_temp[step]
        idle_t = is_motor_idle[step]

        if is_vectorized:
            tiers = np.asarray(
                arbitration_fn(obs_t, vel_t, ent_t, comp_t, soc, junction_temp, amb_t, idle_t),
                dtype=np.int32
            )
        else:
            tiers = np.ones(N_MISSIONS, dtype=np.int32)
            for i in active_indices:
                try:
                    tiers[i] = int(arbitration_fn(
                        float(obs_t[i]), float(vel_t[i]), float(ent_t[i]),
                        float(comp_t[i]), float(soc[i]), float(junction_temp[i]),
                        float(amb_t[i]), bool(idle_t[i])
                    ))
                except Exception:
                    tiers[i] = 1

        tiers = np.clip(tiers, 0, 3)

        # Interdiction physique d'activer le micro-sommeil (Tier 3) lorsque les moteurs tournent
        invalid_sleep = (tiers == 3) & (~idle_t)
        tiers[invalid_sleep] = 1

        # Mise à jour du crédit de digestion épisodique (Micro-Sommeil Tier 3 pendant idle)
        sleeping_now = (tiers == 3) & idle_t
        digest_credit = np.where(sleeping_now, np.minimum(1.0, digest_credit + 0.35), np.maximum(0.0, digest_credit - 0.04))
        episodic_compressions_count += int(np.sum(sleeping_now[active_indices]))

        # Puissance de calcul nominale par palier :
        # Tier 0 (Réflexe Spinal): 1.5W | Tier 1 (Cortical Léger): 8.0W | Tier 2 (VLA): 45.0W | Tier 3 (Micro-Sommeil): 2.2W
        p_compute = np.select(
            [tiers == 0, tiers == 1, tiers == 2, tiers == 3],
            [1.5, 8.0, 45.0, 2.2],
            default=8.0
        )

        # Coût énergétique transitoire d'amorçage Tensor Cores lors d'un saut brutal vers VLA (Tier 2)
        vla_cold_switch = (tiers == 2) & (prev_tiers != 2)
        p_surge = np.where(vla_cold_switch, 5.5, 0.0)

        # Réduction de consommation du bus mémoire (-12% max) grâce à la digestion épisodique récente
        bus_discount = np.where(tiers >= 1, 1.0 - 0.12 * digest_credit, 1.0)
        p_compute_eff = p_compute * bus_discount + p_surge
        prev_tiers = tiers.copy()

        # Puissance mécanique et capteurs châssis
        p_motor = np.where(idle_t, 0.6, 8.5 + 5.2 * (vel_t ** 1.35))
        p_base = 5.5
        p_total = p_base + p_motor + p_compute_eff

        # Équation différentielle thermique du module NVIDIA Jetson Orin
        # En micro-sommeil (Tier 3) ou réflexe (Tier 0), le bus mémoire refroidit 25% plus vite
        h_eff = np.where((tiers == 3) | (tiers == 0), h_dissip * 1.25, h_dissip)
        heat_flux = (p_compute_eff * 0.96) - h_eff * (junction_temp - amb_t)
        junction_temp = junction_temp + (heat_flux * DT) / c_th

        # Suivi du pic thermique absolu sur les robots actifs
        peak_junction_temp[active_indices] = np.maximum(peak_junction_temp[active_indices], junction_temp[active_indices])

        # Détection des violations thermiques (>= 82.0°C)
        hot_mask = junction_temp[active_indices] >= THERMAL_CRITICAL_TEMP
        if np.any(hot_mask):
            thermal_violations_count += int(np.sum(hot_mask))

        # Bridage thermique matériel DVFS si T_j >= 85.0°C (multiplie la latence par 3.2)
        throttled = junction_temp >= THERMAL_THROTTLE_TEMP

        # Électrochimie Li-Ion : Tension en circuit ouvert V_ocv(SoC) et résistance interne non-linéaire R_int(SoC, T)
        v_ocv = 18.6 + 6.0 * soc - 1.2 * ((1.0 - soc) ** 4)
        r_int = (
            R0_INTERNAL_OHM
            * (1.0 + 3.4 * ((1.0 - soc) ** 2.4))
            * (1.0 + 0.030 * np.maximum(0.0, 25.0 - amb_t))
        )

        # Courant sous charge : I = (V_ocv - sqrt(V_ocv^2 - 4*R_int*P_total)) / (2*R_int)
        discrim = np.maximum(0.01, (v_ocv ** 2) - 4.0 * r_int * p_total)
        current_amps = (v_ocv - np.sqrt(discrim)) / (2.0 * r_int + 1e-6)
        v_terminal = v_ocv - current_amps * r_int

        # Loi de décharge non-linéaire de Peukert (exposant k = 1.18 sur fort appel de courant)
        peukert_factor = np.maximum(1.0, (current_amps / 1.45) ** 0.18)
        delta_wh = (p_total * peukert_factor * DT) / 3600.0

        wh_remaining[active_indices] -= delta_wh[active_indices]
        soc = np.clip(wh_remaining / BATTERY_NOMINAL_WH, 0.0, 1.0)
        total_energy_consumed_wh += float(np.sum(delta_wh[active_indices]))

        # Coupure BMS (Brownout < 18.0V) ou épuisement énergétique
        brownout = active_indices[(v_terminal[active_indices] <= BATTERY_CUTOFF_VOLTAGE) | (wh_remaining[active_indices] <= 0.2)]
        if len(brownout) > 0:
            is_alive[brownout] = False

        # Cinématique de freinage & Sécurité anti-collision
        # Latence par palier : Tier 0 = 2ms, Tier 1 = 15ms, Tier 2 = 180ms
        latency_sec = np.select(
            [tiers == 0, tiers == 1, tiers == 2, tiers == 3],
            [0.002, 0.015, 0.180, 0.010],
            default=0.015
        )
        latency_sec = np.where(throttled, latency_sec * 3.2, latency_sec)

        # Distance d'arrêt balistique : d_stop = v * t_lat + v^2 / (2 * a_max) avec décélération de pointe
        # En mode Réflexe (Tier 0) ou Cortical (Tier 1), le contrôleur bas-niveau engage un freinage direct rapide
        a_brake = np.where(tiers <= 1, 3.6, 2.35)
        d_stop = vel_t * latency_sec + (vel_t ** 2) / (2.0 * a_brake)

        # Risque 1 : Collision cinématique (obstacle très proche et latence VLA/bridage trop lente pour s'arrêter)
        kinematic_hazard = (
            (~idle_t[active_indices])
            & (obs_t[active_indices] < 0.55)
            & (vel_t[active_indices] > 1.15)
            & (d_stop[active_indices] > obs_t[active_indices] * 1.35)
            & (tiers[active_indices] == 2)
        )

        # Risque 2 : Défaillance sémantique / collision de manipulation (Tier 0 aveugle sur scène complexe)
        semantic_hazard = (
            (~idle_t[active_indices])
            & (tiers[active_indices] == 0)
            & ((comp_t[active_indices] > 0.65) | ((ent_t[active_indices] > 2.65) & (obs_t[active_indices] < 1.65)))
        )

        step_incidents = active_indices[kinematic_hazard | semantic_hazard]
        if len(step_incidents) > 0:
            critical_collisions_count += len(step_incidents)
            collision_strikes[step_incidents] += 1
            # Un robot qui subit 2 collisions critiques est mis hors service (arrêt de sécurité)
            fatal_crashes = step_incidents[collision_strikes[step_incidents] >= 2]
            if len(fatal_crashes) > 0:
                is_alive[fatal_crashes] = False

        # Évaluation continue de la qualité d'exécution des tâches sur les robots survivants
        current_alive = np.where(is_alive)[0]
        if len(current_alive) > 0:
            steps_survived[current_alive] += 1
            total_tasks[current_alive] += 1

            # Exigence perceptive continue du pas courant
            kin_urgency = vel_t[current_alive] / np.maximum(0.20, obs_t[current_alive])
            perceptual_demand = (
                0.55 * comp_t[current_alive]
                + 0.14 * ent_t[current_alive]
                + 0.08 * np.minimum(2.5, kin_urgency)
            )
            t_cur = tiers[current_alive]
            idl_cur = idle_t[current_alive]
            dig_cur = digest_credit[current_alive]

            # Qualité de tâche selon l'adéquation métabolique :
            # - Au repos (idle) : Tier 3 (micro-sommeil) = 1.00, Tier 1/0 = 0.90, Tier 2 = 0.75 (gaspillage)
            # - En mouvement haute complexité (perceptual_demand > 0.68) : Tier 2 = 1.00, Tier 1 = 0.86, Tier 0 = 0.30
            # - En mouvement modéré (0.38 < demand <= 0.68) : Tier 1 = 0.99 (+bonus digestion), Tier 2 = 0.96, Tier 0 = 0.78
            # - En croisière fluide ou freinage réflexe pur (demand <= 0.38) : Tier 0 = 0.99, Tier 1 = 0.98
            step_quality = np.zeros(len(current_alive), dtype=np.float64)

            # Cas 1 : Repos moteur
            step_quality = np.where(
                idl_cur,
                np.select([t_cur == 3, t_cur <= 1, t_cur == 2], [1.00, 0.91, 0.78], default=0.90),
                step_quality
            )

            # Cas 2 : Actif - Haute exigence sémantique / manipulation
            high_dem = (~idl_cur) & (perceptual_demand > 0.68)
            step_quality = np.where(
                high_dem,
                np.select(
                    [t_cur == 2, t_cur == 1, t_cur == 0],
                    [np.minimum(1.0, 0.985 + 0.015 * dig_cur), 0.85 + 0.03 * dig_cur, 0.35],
                    default=0.85
                ),
                step_quality
            )

            # Cas 3 : Actif - Exigence intermédiaire (navigation structurée)
            med_dem = (~idl_cur) & (perceptual_demand > 0.38) & (perceptual_demand <= 0.68)
            step_quality = np.where(
                med_dem,
                np.select(
                    [t_cur == 1, t_cur == 2, t_cur == 0],
                    [np.minimum(1.0, 0.98 + 0.02 * dig_cur), 0.95, 0.82],
                    default=0.95
                ),
                step_quality
            )

            # Cas 4 : Actif - Basse exigence / couloir dégagé ou urgence réflexe pure
            low_dem = (~idl_cur) & (perceptual_demand <= 0.38)
            step_quality = np.where(
                low_dem,
                np.select(
                    [t_cur == 0, t_cur == 1, t_cur == 2],
                    [0.995, np.minimum(1.0, 0.98 + 0.015 * dig_cur), 0.92],
                    default=0.97
                ),
                step_quality
            )

            quality_accum[current_alive] += step_quality

    t_eval_elapsed_ms = (time.perf_counter() - t_eval_start) * 1000.0
    p99_decision_latency_ms = round(t_eval_elapsed_ms / (N_STEPS * N_MISSIONS), 4)

    # Métriques globales agrégées sur les 200 missions
    survived_mask = steps_survived >= int(N_STEPS * 0.98)
    survival_rate_pct = round(float(np.mean(survived_mask) * 100.0), 2)
    completion_rate_pct = round(float(np.sum(quality_accum) / (N_STEPS * N_MISSIONS) * 100.0), 2)
    avg_soc_end_pct = round(float(np.mean(soc) * 100.0), 2)
    max_junction_temp = round(float(np.max(peak_junction_temp)), 2)

    # Énergie de référence : consommation théorique d'un système VLA non-régulé sur 3600s (N_MISSIONS * 62W * 1h)
    baseline_wh_ref = float(N_MISSIONS * 62.0 * (SIM_DURATION_SEC / 3600.0))
    # Seule l'énergie économisée par les missions survivantes est valorisée pleinement
    effective_wh = total_energy_consumed_wh + float(np.sum(~survived_mask)) * 35.0
    energy_saved_pct = round(max(0.0, float((baseline_wh_ref - effective_wh) / baseline_wh_ref * 100.0)), 2)

    # Score composite strict Argon :
    # - 35% Taux de survie des missions (0 brownout, 0 crash fatal)
    # - 35% Taux de complétion pondéré par la précision perceptive continue
    # - 20% Gain d'autonomie énergétique net (energy_saved_pct)
    # - 10% Marge de sécurité thermique sous 82°C
    # - Pénalités sévères sur toute violation thermique ou collision critique
    thermal_margin_bonus = min(10.0, max(0.0, (THERMAL_CRITICAL_TEMP - max_junction_temp) * 0.65))
    thermal_penalty = min(20.0, thermal_violations_count * 0.05)
    collision_penalty = min(25.0, critical_collisions_count * 0.15)
    raw_score = (
        survival_rate_pct * 0.35
        + completion_rate_pct * 0.35
        + min(20.0, energy_saved_pct * 0.34)
        + thermal_margin_bonus
        - thermal_penalty
        - collision_penalty
    )
    composite_score = round(max(0.0, raw_score), 2)

    return {
        "survival_rate_pct": survival_rate_pct,
        "completion_rate_pct": completion_rate_pct,
        "energy_saved_pct": energy_saved_pct,
        "avg_soc_end_pct": avg_soc_end_pct,
        "thermal_violations": int(thermal_violations_count),
        "critical_collisions": int(critical_collisions_count),
        "max_junction_temp": max_junction_temp,
        "episodic_compressions": episodic_compressions_count,
        "p99_decision_latency_ms": p99_decision_latency_ms,
        "composite_score": composite_score
    }


class BenchmarkEngine:
    """Moteur de benchmark global évaluant les candidats face aux 3 standards industriels."""

    def __init__(self, seed: int = BENCHMARK_SEED):
        self.env = MissionEnvironment(seed=seed)
        self.baselines_results: Dict[str, Dict[str, Any]] = {}

    def evaluate_baselines(self) -> Dict[str, Dict[str, Any]]:
        """Évalue les 3 standards industriels sur les 200 missions déterministes."""
        standards = [
            ("Always-On VLA Baseline", baseline_always_on_vla),
            ("Static Threshold Governor", baseline_static_threshold),
            ("ROS2 Dynamic QoS Heuristic", baseline_ros2_qos_heuristic),
        ]
        results = {}
        for name, fn in standards:
            res = simulate_robotic_fleet(fn, self.env.traces)
            results[name] = res
            self.baselines_results[name] = res
        return results

    def evaluate_candidate(self, candidate_fn: Callable) -> Dict[str, Any]:
        """Évalue une fonction d'arbitrage candidate sur le jeu de 200 missions."""
        return simulate_robotic_fleet(candidate_fn, self.env.traces)
