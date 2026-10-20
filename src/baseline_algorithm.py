"""
RoboMetabolism-Lab - Standards Industriels & Algorithmes de Référence (Baselines)
Définit les 3 standards de l'industrie robotique évalués par le juge physique déterministe :
1. Always-On VLA Baseline (Modèle multimodal 45W permanent avec sécurité réflexe minimale)
2. Static Threshold Governor (Gouverneur statique sur seuils fixes de batterie et distance)
3. ROS2 Dynamic QoS Heuristic (Heuristique standard de modulation de qualité de service ROS2 / Nav2)
"""

from typing import Dict, Any


def baseline_always_on_vla(
    obstacle_dist: float,
    velocity: float,
    sensor_entropy: float,
    manipulation_comp: float,
    battery_soc: float,
    junction_temp: float,
    ambient_temp: float,
    is_motor_idle: bool
) -> int:
    """
    Standard Industriel 1 : Always-On VLA Baseline.
    Maintient le modèle Vision-Language-Action (45W) actif en permanence pour maximiser
    la précision sémantique, avec uniquement un arrêt réflexe d'extrême urgence (< 0.42m).
    Conséquence : Épuisement rapide de la batterie par effet Peukert, chutes de tension
    internes (Brownout BMS < 18.0V) et surchauffe thermique (> 82°C / throttling > 85°C).
    """
    if is_motor_idle:
        return 1
    if obstacle_dist < 0.42 and manipulation_comp < 0.50:
        return 0
    return 2


def baseline_static_threshold(
    obstacle_dist: float,
    velocity: float,
    sensor_entropy: float,
    manipulation_comp: float,
    battery_soc: float,
    junction_temp: float,
    ambient_temp: float,
    is_motor_idle: bool
) -> int:
    """
    Standard Industriel 2 : Static Threshold Governor.
    Politique industrielle classique à seuils fixes sur l'état de charge (SoC) et l'incertitude.
    Conséquence : Chattering coûteux entre paliers de puissance, mauvaise anticipation des pics
    thermiques et arbitrages sous-optimaux à haute vitesse.
    """
    if is_motor_idle:
        return 1
    if battery_soc < 0.25:
        return 0
    if obstacle_dist < 0.58:
        return 0 if manipulation_comp < 0.62 else 1
    if manipulation_comp > 0.52 or sensor_entropy > 2.25:
        return 2
    return 1


def baseline_ros2_qos_heuristic(
    obstacle_dist: float,
    velocity: float,
    sensor_entropy: float,
    manipulation_comp: float,
    battery_soc: float,
    junction_temp: float,
    ambient_temp: float,
    is_motor_idle: bool
) -> int:
    """
    Standard Industriel 3 : ROS2 Dynamic QoS Heuristic.
    Heuristique industrielle standard (Nav2 / ROS2 Lifecycle QoS Manager) modulant le palier
    de calcul selon la température CPU/GPU, la distance d'obstacle et l'entropie.
    Conséquence : Survit à la majorité des missions mais ignore la résistance interne non-linéaire
    R_int(SoC, T), n'exploite pas la digestion épisodique en micro-sommeil (Tier 3) et gaspille
    de l'énergie lors des commutations fréquentes vers le VLA 45W.
    """
    if is_motor_idle:
        return 1
    if junction_temp > 77.5:
        return 0 if (obstacle_dist < 0.65 and manipulation_comp < 0.55) else 1
    if obstacle_dist < 0.62 and manipulation_comp < 0.60 and sensor_entropy < 2.50:
        return 0
    if manipulation_comp > 0.62 or (sensor_entropy > 2.45 and obstacle_dist < 2.20):
        if obstacle_dist > 0.80 and battery_soc > 0.18:
            return 2
    return 1


BASELINES_CATALOG: Dict[str, Dict[str, Any]] = {
    "Always-On VLA Baseline": {
        "function": baseline_always_on_vla,
        "description": "Modèle Vision-Language-Action 45W permanent (NVIDIA Jetson Orin)",
        "flaw": "Surchauffe > 82°C, throttling thermique et coupure prématurée par brownout batterie"
    },
    "Static Threshold Governor": {
        "function": baseline_static_threshold,
        "description": "Gouverneur à seuils statiques (SoC < 22%, entropie > 2.25)",
        "flaw": "Chattering énergétique, collisions résiduelles et absence de barrière thermique"
    },
    "ROS2 Dynamic QoS Heuristic": {
        "function": baseline_ros2_qos_heuristic,
        "description": "Heuristique de QoS dynamique standard ROS2 / Nav2",
        "flaw": "Ignore l'impédance non-linéaire Li-Ion R_int(SoC,T) et le micro-sommeil épisodique"
    }
}
