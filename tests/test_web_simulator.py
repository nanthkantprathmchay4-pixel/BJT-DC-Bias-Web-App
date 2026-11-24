import unittest
from unittest import mock

from app import app


class SimulatorWebTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_simulator_has_form(self):
        resp = self.client.get("/simulator")
        body = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        for name in ["vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "vin_mvp", "freq_hz"]:
            self.assertIn(f'name="{name}"', body)

    def test_invalid_re_shows_error(self):
        data = {
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "0", "rl": "10",
            "cin": "10", "cout": "10", "beta": "100", "vbe": "0.7",
            "vin_mvp": "10", "freq_hz": "1000", "analysis": "op",
        }
        body = self.client.post("/simulator", data=data).get_data(as_text=True)
        self.assertIn("ความต้านทานต้องมากกว่า 0", body)
        self.assertNotIn("status-ok", body)

    def test_engine_error_has_no_stale_success(self):
        data = {
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "rl": "10",
            "cin": "10", "cout": "10", "beta": "100", "vbe": "0.7",
            "vin_mvp": "10", "freq_hz": "1000", "analysis": "op",
        }
        with mock.patch(
            "app.run_simulation",
            return_value={
                "status": "error", "error": "ngspice missing", "log_tail": "",
                "engine": "ngspice", "model": "2N3904", "analysis": "op", "data": {},
            },
        ):
            body = self.client.post("/simulator", data=data).get_data(as_text=True)
        self.assertIn("ngspice missing", body)
        self.assertNotIn("status-ok", body)
