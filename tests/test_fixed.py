import unittest

from dc_bias import FixedBiasInput, calculate_fixed

A2 = FixedBiasInput(vcc=12, rb=1_000_000, rc=2_200, beta=100, vbe=0.7)


class FixedBiasReferenceTest(unittest.TestCase):
    def setUp(self):
        self.r = calculate_fixed(A2)

    def test_currents(self):
        self.assertAlmostEqual(self.r.ib, 1.13e-05, delta=1e-9)
        self.assertAlmostEqual(self.r.ic, 0.00113, delta=1e-9)
        self.assertAlmostEqual(self.r.ie, 0.0011413, delta=1e-9)

    def test_voltages(self):
        self.assertAlmostEqual(self.r.ve, 0.0, delta=1e-12)
        self.assertAlmostEqual(self.r.vb, 0.7, delta=1e-9)
        self.assertAlmostEqual(self.r.vc, 9.514, delta=1e-6)
        self.assertAlmostEqual(self.r.vce, 9.514, delta=1e-6)

    def test_region_is_active_without_warnings(self):
        self.assertEqual(self.r.region, "active")
        self.assertEqual(self.r.warnings, [])
