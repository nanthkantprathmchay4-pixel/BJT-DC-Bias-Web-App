import unittest

from dc_bias import BiasInput, calculate

REFERENCE = BiasInput(
    vcc=12, r1=100_000, r2=22_000, rc=2_200, re=1_000, beta=100, vbe=0.7
)


class ReferenceCaseTest(unittest.TestCase):
    def setUp(self):
        self.r = calculate(REFERENCE)

    def test_intermediate_values(self):
        self.assertAlmostEqual(self.r.vth, 2.163934, delta=1e-6)
        self.assertAlmostEqual(self.r.rth, 18032.787, delta=1e-3)

    def test_currents(self):
        self.assertAlmostEqual(self.r.ib, 12.298581463e-6, delta=1e-9)
        self.assertAlmostEqual(self.r.ic, 1.2298581463e-3, delta=1e-9)
        self.assertAlmostEqual(self.r.ie, 1.242156727763e-3, delta=1e-9)

    def test_voltages(self):
        self.assertAlmostEqual(self.r.ve, 1.242156727763, delta=1e-6)
        self.assertAlmostEqual(self.r.vb, 1.942156727763, delta=1e-6)
        self.assertAlmostEqual(self.r.vc, 9.29431207814, delta=1e-6)
        self.assertAlmostEqual(self.r.vce, 8.052155350377, delta=1e-6)

    def test_region_is_active_without_warnings(self):
        self.assertEqual(self.r.region, "active")
        self.assertEqual(self.r.warnings, [])


class RegionTest(unittest.TestCase):
    def test_cutoff_when_vth_not_above_vbe(self):
        p = BiasInput(
            vcc=12, r1=100_000, r2=5_000, rc=2_200, re=1_000, beta=100, vbe=0.7
        )
        r = calculate(p)
        self.assertEqual(r.region, "cutoff")
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.ie, 0.0)
        self.assertAlmostEqual(r.vb, 0.571429, delta=1e-6)
        self.assertAlmostEqual(r.vc, 12.0, delta=1e-9)
        self.assertTrue(r.warnings)

    def test_saturation_when_vce_low(self):
        p = BiasInput(
            vcc=12, r1=100_000, r2=22_000, rc=8_700, re=1_000, beta=100, vbe=0.7
        )
        r = calculate(p)
        self.assertEqual(r.region, "saturation")
        self.assertAlmostEqual(r.vce, 0.0581, delta=1e-3)
        self.assertTrue(r.warnings)
