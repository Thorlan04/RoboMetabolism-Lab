"""
RoboMetabolism-Lab - Public Evaluator Contract & Anti-Cheat Unit Tests
Vérifie le déterminisme du juge physique, le verrouillage en lecture seule des traces NumPy,
l'audit AST anti-triche et l'étanchéité de la propriété intellectuelle (verify_zero_leak).
"""

import unittest
import numpy as np

from src.benchmark_engine import (
    MissionEnvironment,
    simulate_robotic_fleet,
    verify_candidate_ast_safety,
    probe_candidate_responsiveness,
    baseline_always_on_vla,
    baseline_static_threshold,
    baseline_ros2_qos_heuristic,
)
from src.ip_protector import compute_code_hash, generate_obfuscated_public_stub, audit_public_store_safety


class TestRoboMetabolismContract(unittest.TestCase):

    def setUp(self):
        self.env = MissionEnvironment(seed=2026)

    def test_deterministic_readonly_traces(self):
        """Vérifie que les traces de mission sont déterministes et verrouillées en lecture seule."""
        env2 = MissionEnvironment(seed=2026)
        np.testing.assert_array_equal(self.env.traces["obstacle_dist"], env2.traces["obstacle_dist"])
        self.assertFalse(self.env.traces["obstacle_dist"].flags.writeable)
        self.assertFalse(self.env.traces["ambient_temp"].flags.writeable)

    def test_ast_anti_cheat_guard(self):
        """Vérifie que l'auditeur AST bloque les variables globales et imports illégaux."""
        bad_code_global = "def arbitrate_metabolic_tier(*args):\n    global x\n    return 1"
        ok, _ = verify_candidate_ast_safety(bad_code_global)
        self.assertFalse(ok)

        bad_code_import = "import os\ndef arbitrate_metabolic_tier(*args):\n    return 1"
        ok2, _ = verify_candidate_ast_safety(bad_code_import)
        self.assertFalse(ok2)

    def test_degenerate_constant_rejected(self):
        """Vérifie qu'une fonction constante dégénérée est rejetée par la sonde multi-états."""
        self.assertFalse(probe_candidate_responsiveness(lambda *args: 1))

    def test_baselines_hierarchy(self):
        """Vérifie la hiérarchie physique des 3 baselines industrielles."""
        r_vla = simulate_robotic_fleet(baseline_always_on_vla, self.env.traces)
        r_stat = simulate_robotic_fleet(baseline_static_threshold, self.env.traces)
        r_qos = simulate_robotic_fleet(baseline_ros2_qos_heuristic, self.env.traces)

        self.assertGreater(r_vla["thermal_violations"], 1000)
        self.assertGreater(r_qos["composite_score"], r_stat["composite_score"])
        self.assertGreater(r_stat["composite_score"], r_vla["composite_score"])

    def test_ip_protector_stub(self):
        """Vérifie que le stub obfusqué ne fuite aucune équation interne."""
        secret = "def arbitrate_metabolic_tier(a,b,c,d,e,f,g,h):\n    secret_term = math.log(82.0 - f) * 0.42\n    return 1"
        h = compute_code_hash(secret)
        stub = generate_obfuscated_public_stub(secret, "TestAlg", h)
        self.assertNotIn("secret_term", stub)
        is_safe, _ = audit_public_store_safety(secret)
        self.assertTrue(is_safe)


if __name__ == "__main__":
    unittest.main()
