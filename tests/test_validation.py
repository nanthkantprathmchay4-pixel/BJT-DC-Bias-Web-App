import unittest

from dc_bias import validate

VALID = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}


class ValidInputTest(unittest.TestCase):
    def test_returns_bias_input_with_ohms(self):
        bias_input, errors = validate(VALID)
        self.assertEqual(errors, {})
        self.assertIsNotNone(bias_input)
        self.assertEqual(bias_input.r1, 100_000.0)
        self.assertEqual(bias_input.rc, 2_200.0)

    def test_strips_surrounding_whitespace(self):
        bias_input, errors = validate({**VALID, "vcc": " 12 "})
        self.assertEqual(errors, {})
        self.assertEqual(bias_input.vcc, 12.0)

    def test_accepts_fractional_beta(self):
        bias_input, errors = validate({**VALID, "beta": "2.5"})
        self.assertEqual(errors, {})
        self.assertEqual(bias_input.beta, 2.5)


class InvalidInputTest(unittest.TestCase):
    def test_missing_field(self):
        form = dict(VALID)
        del form["re"]
        bias_input, errors = validate(form)
        self.assertIsNone(bias_input)
        self.assertEqual(errors["re"], "กรุณากรอกค่านี้")

    def test_non_numeric(self):
        bias_input, errors = validate({**VALID, "vcc": "abc"})
        self.assertIsNone(bias_input)
        self.assertEqual(errors["vcc"], "ต้องเป็นตัวเลข")

    def test_thousands_separator_is_rejected_as_non_numeric(self):
        bias_input, errors = validate({**VALID, "r1": "1,000"})
        self.assertIsNone(bias_input)
        self.assertEqual(errors["r1"], "ต้องเป็นตัวเลข")

    def test_zero_or_negative_resistance(self):
        _, errors = validate({**VALID, "r1": "-1"})
        self.assertEqual(errors["r1"], "ความต้านทานต้องมากกว่า 0")
        _, errors = validate({**VALID, "r2": "0"})
        self.assertEqual(errors["r2"], "ความต้านทานต้องมากกว่า 0")

    def test_zero_beta(self):
        _, errors = validate({**VALID, "beta": "0"})
        self.assertEqual(errors["beta"], "β ต้องมากกว่า 0")

    def test_non_positive_vcc(self):
        _, errors = validate({**VALID, "vcc": "0"})
        self.assertEqual(errors["vcc"], "VCC ต้องมากกว่า 0")

    def test_vbe_out_of_range(self):
        _, errors = validate({**VALID, "vbe": "12"})
        self.assertEqual(errors["vbe"], "VBE ต้องอยู่ระหว่าง 0 ถึง VCC")

    def test_beta_below_minus_one_is_blocked(self):
        _, errors = validate({**VALID, "beta": "-5"})
        self.assertIn("beta", errors)

    def test_all_missing_reports_every_field(self):
        _, errors = validate({})
        self.assertEqual(len(errors), 7)


class NonFiniteInputTest(unittest.TestCase):
    def test_nan_is_rejected(self):
        bias_input, errors = validate({**VALID, "vcc": "nan"})
        self.assertIsNone(bias_input)
        self.assertIn("vcc", errors)

    def test_infinity_is_rejected(self):
        bias_input, errors = validate({**VALID, "vcc": "inf"})
        self.assertIsNone(bias_input)
        self.assertIn("vcc", errors)

    def test_overflow_literal_is_rejected(self):
        bias_input, errors = validate({**VALID, "beta": "1e400"})
        self.assertIsNone(bias_input)
        self.assertIn("beta", errors)

    def test_kilo_ohm_overflow_is_rejected(self):
        bias_input, errors = validate({**VALID, "rc": "1e308"})
        self.assertIsNone(bias_input)
        self.assertIn("rc", errors)
