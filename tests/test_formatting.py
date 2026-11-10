import unittest

from formatting import fmt_current, fmt_resistance, fmt_voltage


class FormatTest(unittest.TestCase):
    def test_voltage(self):
        self.assertEqual(fmt_voltage(1.942156), "1.942 V")
        self.assertEqual(fmt_voltage(12.0), "12.000 V")

    def test_current_uses_milliamp_above_one_milliamp(self):
        self.assertEqual(fmt_current(1.22986e-3), "1.230 mA")

    def test_current_uses_microamp_below_one_milliamp(self):
        self.assertEqual(fmt_current(12.2986e-6), "12.299 µA")

    def test_current_boundary_is_one_millamp(self):
        self.assertEqual(fmt_current(1e-3), "1.000 mA")

    def test_resistance_uses_kilo_ohm_above_one_thousand(self):
        self.assertEqual(fmt_resistance(18032.787), "18.033 kΩ")

    def test_resistance_uses_ohm_below_one_thousand(self):
        self.assertEqual(fmt_resistance(820.0), "820.000 Ω")
