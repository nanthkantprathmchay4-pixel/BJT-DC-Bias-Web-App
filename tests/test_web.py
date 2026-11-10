import unittest

from app import app


class GetFormTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_returns_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("<form", body)

    def test_get_has_every_named_input(self):
        body = self.client.get("/").get_data(as_text=True)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', body)

    def test_get_prefills_defaults(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('value="12"', body)
        self.assertIn('value="100"', body)

    def test_get_has_no_results_block(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("ขั้นตอนการคำนวณ", body)


VALID_POST = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}


class CalculatePostTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_valid_post_shows_results(self):
        body = self.client.post("/", data=VALID_POST).get_data(as_text=True)
        self.assertIn("1.942", body)          # VB
        self.assertIn("1.230 mA", body)       # IC
        self.assertIn("Active Region", body)

    def test_valid_post_shows_steps(self):
        body = self.client.post("/", data=VALID_POST).get_data(as_text=True)
        self.assertIn("ขั้นตอนการคำนวณ", body)
        self.assertIn("2.164", body)          # VTH

    def test_invalid_input_shows_error_without_traceback(self):
        body = self.client.post(
            "/", data={**VALID_POST, "beta": "0"}
        ).get_data(as_text=True)
        self.assertIn("β ต้องมากกว่า 0", body)
        self.assertNotIn("Traceback", body)

    def test_empty_post_reports_missing_fields(self):
        body = self.client.post("/", data={}).get_data(as_text=True)
        self.assertIn("กรุณากรอกค่านี้", body)

    def test_saturation_shows_warning(self):
        body = self.client.post(
            "/", data={**VALID_POST, "rc": "8.7"}
        ).get_data(as_text=True)
        self.assertIn("Saturation", body)

    def test_huge_values_do_not_crash(self):
        resp = self.client.post("/", data={**VALID_POST, "vcc": "1000000000"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Traceback", resp.get_data(as_text=True))

    def test_non_finite_input_never_renders_nan_or_inf(self):
        cases = (
            ("vcc", "nan"),
            ("vcc", "inf"),
            ("rc", "1e308"),
            ("beta", "1e400"),
        )
        for field, raw in cases:
            with self.subTest(field=field, raw=raw):
                body = self.client.post(
                    "/", data={**VALID_POST, field: raw}
                ).get_data(as_text=True)
                self.assertIn('class="error"', body)
                self.assertNotIn("nan V", body)
                self.assertNotIn("inf V", body)
                self.assertNotIn("nan µA", body)
                self.assertNotIn("inf mA", body)
