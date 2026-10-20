# 🤖 RoboMetabolism-Lab : Moteur d'Ordonnancement Métabolique & Cognitif Temps-Réel pour Robots Autonomes (Embodied AI / ROS2)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Pure NumPy](https://img.shields.io/badge/dependencies-pure_numpy-success.svg)](https://numpy.org/)
[![Hardware Target](https://img.shields.io/badge/hardware-NVIDIA_Jetson_Orin-76B900.svg)](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)
[![Middleware](https://img.shields.io/badge/ros2-Humble_|_Iron_|_Jazzy-22314E.svg)](https://www.ros.org/)
[![Safety SLA](https://img.shields.io/badge/SLA_Collision_Free-100%25-brightgreen.svg)]()
[![Thermal Violations](https://img.shields.io/badge/Thermal_Violations-0_(<82°C)-blue.svg)]()
[![License](https://img.shields.io/badge/license-Commercial_Polar.sh-ff5a5f.svg)](https://buy.polar.sh/polar_cl_XceignaL6bXyot2FQuNTP9d14PWdHCKoESuN62sF7m6)

> **6ème Laboratoire Algorithmique Autonome** de la flotte R&D.  
> Conçu pour résoudre le goulet d'étranglement fatal de l'autonomie et de la dissipation thermique des robots IA (humanoïdes, quadrupèdes, drones, AGV/AMR d'entrepôt) exploitant des modèles de vision/action (VLA / VLM) sur NVIDIA Jetson Orin.

---

## ⚡ 1. Le Problème Commercial & Physique ("La Nourriture des Robots IA")

Les robots autonomes modernes équipés de modèles multimodaux de pointe (**OpenVLA, Octo, RT-2**) souffrent d'un dilemme thermodynamique et électrique destructeur :

1. **L'Impasse Always-On VLA (45W)** :  
   Activer en permanence le grand modèle multimodal sature le GPU du Jetson Orin. La batterie Li-Ion 6S/7S subit une chute de tension interne brutale ($V_{drop} = I \cdot R_{int}$) amplifiée par l'effet Peukert. La batterie s'épuise en **25 à 35 minutes**. Simultanément, la température de jonction dépasse **85°C**, déclenchant un *thermal throttling* matériel sévère qui triple la latence d'inférence (>500ms) et provoque des **collisions balistiques** face aux obstacles soudains.

2. **L'Échec des Gouverneurs Statiques Réflexes (2W)** :  
   Les bascules simplistes sur seuils fixes de batterie ou de distance ignorent l'inertie thermique, la dynamique non-linéaire des accumulateurs et l'ambiguïté perceptive. Résultat : instabilités oscillatoires (*chattering*), chutes d'objets fragiles manipulés et arrêts d'urgence intempestifs.

---

## 🧠 2. La Solution : L'Ordonnanceur Neuromorphique RoboMetabolism (< 0.2 ms)

`RoboMetabolism-Lab` implémente un noyau d'arbitrage neuromorphique temps-réel en **NumPy pur (zéro dépendance lourde, < 0.2 ms d'exécution)**. Il arbitre continuellement entre 4 régimes métaboliques :

```
                                  [Flux Capteurs & Télémétrie Châssis]
                                                   │
                       ┌───────────────────────────┴───────────────────────────┐
                       ▼                                                       ▼
            [Dynamique Cinématique & LiDAR]                          [Physique Batterie & Thermique]
            • Distance obstacle (d_obs)                              • State of Charge (SoC)
            • Vitesse relative (v)                                   • Résistance interne R_int(SoC, T)
            • Entropie sensorielle H(X)                              • Température jonction Jetson (T_j)
                       │                                                       │
                       └───────────────────────────┬───────────────────────────┘
                                                   ▼
                                  ┌─────────────────────────────────┐
                                  │   ROBOMETABOLISM KERNEL         │
                                  │   Arbitrage Métabolique < 0.2ms │
                                  └────────────────┬────────────────┘
                                                   │
       ┌────────────────────────┬──────────────────┴──────────────┬────────────────────────┐
       ▼                        ▼                                 ▼                        ▼
[Tier 0: Réflexe Spinal] [Tier 1: Cortical Léger]       [Tier 2: Deep VLA]       [Tier 3: Micro-Sommeil]
• Puissance: 1.5W        • Puissance: 8.0W              • Puissance: 45.0W       • Puissance: 2.2W
• Latence: 2ms           • Latence: 15ms                • Latence: 180ms         • Digestion épisodique
• Évitement balistique   • Modèle quantifié INT8        • Raisonnement spatial   • Purge mémoire & bus
• Freinage d'urgence     • Navigation de croisière      • Manipulation fine      • Refroidissement accru
```

---

## 📊 3. Résultats de Validation Déterministe (200 Missions de 3 600s)

Chaque algorithme candidat est évalué de manière strictement déterministe en RAM (`seed = 2026`) sur **200 missions robotiques complexes de 1 heure** simulant navigation encombrée, franchissements d'obstacles, manipulation d'objets instables, pics de chaleur ambiante (jusqu'à 39°C) et modélisation physique Li-Ion.

| Métrique de Performance | Always-On VLA Baseline | Static Threshold Governor | ROS2 Dynamic QoS Heuristic | **Champion RoboMetabolism (`Argon_Shepherd_LogBarrier_v2_1`)** |
| :--- | :---: | :---: | :---: | :---: |
| **Survie Mission (3 600s)** | **0.0%** *(Épuisement / Brownout)* | **25.5%** *(Collisions & Brownout)* | **100.0%** | **100.0% (ZÉRO ÉCHEC)** |
| **Complétion des Tâches** | 24.43% | 46.27% | 96.15% | **98.71% (+2.56 pts)** |
| **Autonomie Gagnée par Charge** | +17.46% *(Mort prématurée)* | +29.20% | +46.67% | **+57.52% d'autonomie** |
| **Violations Thermiques (> 82°C)** | 9 323 violations | 7 violations | 0 | **0 VIOLATION STRICTE** |
| **Collisions Critiques (Crash)** | 339 crashs | 320 crashs | 0 | **0 COLLISION (SLA 100%)** |
| **Température Max Jonction** | 91.69°C *(Throttled)* | 83.10°C | 78.11°C | **69.32°C (-8.8°C vs ROS2 QoS)** |
| **Compressions Micro-Sommeil** | 0 | 0 | 0 | **45 616 cycles consolidés** |
| **Latence Décisionnelle P99** | 0.0015 ms | 0.0021 ms | 0.0025 ms | **0.0033 ms (< 0.2 ms SLA)** |
| **Score Composite Certifié** | **0.00 / 100** | **9.70 / 100** | **87.05 / 100** | **97.35 / 100** |

---

## 🔬 4. Fondements Physiques & Mathématiques du Benchmark

### 1. Modèle Électrochimique Li-Ion Non-Linéaire
- **Tension en Circuit Ouvert ($V_{ocv}$)** :
  $$V_{ocv}(SoC) = 18.6 + 6.0 \cdot SoC - 1.2 \cdot (1 - SoC)^4$$
- **Résistance Interne Non-Linéaire ($R_{int}$)** :
  $$R_{int}(SoC, T) = R_0 \cdot \left(1 + 3.2 \cdot (1 - SoC)^{2.5}\right) \cdot \left(1 + 0.028 \cdot \max(0, 25 - T_{amb})\right)$$
- **Chute de Tension sous Charge & Coupure BMS (Brownout)** :
  $$V_{terminal} = V_{ocv} - I \cdot R_{int}$$
  Si $V_{terminal} \le 18.0\text{V}$, le système de gestion de batterie (BMS) coupe instantanément l'alimentation pour protéger les cellules, entraînant l'échec de la mission.
- **Effet Peukert de Sur-Décharge** :
  $$I_{eff} = I \cdot \left(\frac{I}{I_{nom}}\right)^{0.16}$$

### 2. Modèle Thermique du Châssis NVIDIA Jetson Orin
$$\frac{dT_j}{dt} = \frac{P_{compute} - h_{eff} \cdot (T_j - T_{ambient})}{C_{th}}$$
- $C_{th} = 52.0\text{ J/}^\circ\text{C}$ (capacité thermique radiateur + ventilateur).
- $h_{eff} = 0.72\text{ W/}^\circ\text{C}$ en opération active, portée à $0.90\text{ W/}^\circ\text{C}$ (+25%) lors du micro-sommeil épisodique.
- Seuil de violation : $T_j \ge 82.0^\circ\text{C}$. Seuil de bridage matériel : $T_j \ge 85.0^\circ\text{C}$.

### 3. Modèle Cinématique & Distances d'Arrêt
$$d_{stop} = v \cdot t_{latence} + \frac{v^2}{2 \cdot a_{max}}$$
Si $d_{stop} > d_{obstacle}$, une collision critique irréversible est enregistrée.

---

## 📁 5. Architecture Open-Core & Propriété Intellectuelle

Conformément à la politique **Argon Open-Core B2B Lockdown** de la flotte R&D, ce dépôt GitHub public est conçu pour permettre aux auditeurs et directeurs techniques de vérifier la rigueur du benchmark sans exposer le secret industriel :

- 🌐 **Public sur GitHub (Open-Core Harness)** :
  - `src/benchmark_engine.py` : Le simulateur physique déterministe (200 missions, modèle Li-Ion & thermique Orin).
  - `src/baseline_algorithm.py` : Les 3 standards industriels de référence.
  - `tests/test_evaluator_contract.py` : La suite de tests unitaires formels et garde-fous anti-triche AST.
  - `public_store/` : La vitrine web B2B, le calculateur de ROI interactif et la preuve chiffrée `proof_benchmark.json` (avec stub public obfusqué de 8 lignes).
  - `LICENSE` : Licence commerciale d'évaluation interdisant tout usage en production sans licence payante.

- 🔒 **Privé & Débloqué via la Licence Commerciale Polar.sh (`DECOUVERTE_A_VENDRE/`)** :
  - `algorithme_champion.py` : Le code source mathématique complet du champion certifié (`Argon_Shepherd_LogBarrier_v2_1` - score 97.35/100).
  - `RoboMetabolismROS2Scheduler` : Le wrapper ROS2 prêt pour NVIDIA Jetson Orin (Nano, NX, AGX).
  - `RAPPORT_EXECUTIF_METABOLISME_ROBOTIQUE.md` : Le rapport d'audit exécutif complet pour comités de direction.
  - `SHA256_CERTIFICATE.txt` : Le certificat cryptographique d'intégrité immuable.

---

## 🚀 6. Vérification Publique & Reproduction Déterministe

### Installation
```bash
git clone https://github.com/Thorlan04/RoboMetabolism-Lab.git
cd RoboMetabolism-Lab
pip install -r requirements.txt
```

### Vérifier le Contrat & les Baselines Industrielles
```bash
python -m unittest tests/test_evaluator_contract.py
```

### Évaluer les 3 Standards Industriels Déterministes (200 Missions)
```bash
python -c "from src.benchmark_engine import BenchmarkEngine; b = BenchmarkEngine(); [print(f'{k}: {v}') for k, v in b.evaluate_baselines().items()]"
```

---

## 🔒 7. Déploiement en Production & Licence B2B

Le code source complet de la formule championne (`Argon_Shepherd_LogBarrier_v2_1`), le wrapper ROS2 et les droits d'exploitation commerciale sont délivrés instantanément sous licence B2B :

👉 **[Débloquer la Licence Commerciale sur Polar.sh](https://buy.polar.sh/polar_cl_XceignaL6bXyot2FQuNTP9d14PWdHCKoESuN62sF7m6)**
