import unittest

from dc_bias import EmitterBiasInput, calculate_emitter

A3 = EmitterBiasInput(vcc=12, rb=1_000_000, rc=2_200, re=1_000, beta=100, vbe=0.7)
A4 = EmitterBiasInput(vcc=12, rb=1_000_000, rc=2_200, re=2_000, beta=100, vbe=0.7)


class EmitterBiasReferenceTest(unittest.TestCase):
    def setUp(self):
        self.a3 = calculate_emitter(A3)
        self.a4 = calculate_emitter(A4)

    def test_a3_currents(self):
        self.assertAlmostEqual(self.a3.ib, 1.0263396911898274e-05, delta=1e-9)
        self.assertAlmostEqual(self.a3.ic, 0.0010263396911898274, delta=1e-9)
        self.assertAlmostEqual(self.a3.ie, 0.0010366030881017257, delta=1e-9)

    def test_a3_voltages(self):
        self.assertAlmostEqual(self.a3.ve, 1.0366030881017256, delta=1e-6)
        self.assertAlmostEqual(self.a3.vb, 1.7366030881017256, delta=1e-6)
        self.assertAlmostEqual(self.a3.vc, 9.742052679382379, delta=1e-6)
        self.assertAlmostEqual(self.a3.vce, 8.705449591280653, delta=1e-6)

    def test_a4_reference_values(self):
        self.assertAlmostEqual(self.a4.ic, 0.0009400998336106491, delta=1e-9)
        self.assertAlmostEqual(self.a4.vce, 8.03277870216306, delta=1e-6)

    def test_raising_re_lowers_ic_and_vce(self):
        # RE ↑ → IB, IC ↓ และ VE ↑ มากกว่าที่ IC·RC ลดลง ดังนั้น VCE ลดในย่านนี้
        self.assertLess(self.a4.ic, self.a3.ic)
        self.assertLess(self.a4.vce, self.a3.vce)

    def test_region_is_active_for_both_cases(self):
        self.assertEqual(self.a3.region, "active")
        self.assertEqual(self.a4.region, "active")
        self.assertEqual(self.a3.warnings, [])
        self.assertEqual(self.a4.warnings, [])
