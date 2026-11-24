import unittest

import plot_svg


class PlotSvgTest(unittest.TestCase):
    def test_bode_svg_has_labels_and_path(self):
        svg = plot_svg.bode_svg([10, 100, 1000], [-20, 0, -3], [180, 170, 120])
        self.assertIn("<svg", svg)
        self.assertIn("Frequency (Hz)", svg)
        self.assertIn("Gain (dB)", svg)
        self.assertIn("Phase", svg)
        self.assertIn("<path", svg)

    def test_transient_svg_has_labels(self):
        svg = plot_svg.transient_svg([0.0, 0.001], [0.0, 0.01], [0.0, -0.1])
        self.assertIn("Time (ms)", svg)
        self.assertIn("Vin", svg)
        self.assertIn("Vout", svg)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            plot_svg.transient_svg([], [], [])
