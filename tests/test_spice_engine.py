import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import spice_engine
from spice_engine import CEParams, DEFAULT_MODEL_NAME, build_netlist


def base_params():
    return CEParams(12.0, 100e3, 22e3, 2.2e3, 1e3, 10e3, 10.0, 10.0, 100.0, 0.7, 10.0, 1000.0)


class ResolveNgspiceTest(unittest.TestCase):
    def test_explicit_path_wins(self):
        with TemporaryDirectory() as td:
            exe = Path(td) / "ngspice.exe"
            exe.write_text("", encoding="utf-8")
            got = spice_engine.resolve_ngspice(str(exe), env={})
            self.assertEqual(got, str(exe))

    def test_env_var_used(self):
        with TemporaryDirectory() as td:
            exe = Path(td) / "ngspice.exe"
            exe.write_text("", encoding="utf-8")
            got = spice_engine.resolve_ngspice(None, env={"NGSPICE_EXE": str(exe)})
            self.assertEqual(got, str(exe))

    def test_missing_raises_actionable_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            spice_engine.resolve_ngspice(
                None, env={}, which=lambda _: None, exists=lambda _: False
            )
        self.assertIn("NGSPICE_EXE", str(ctx.exception))


class NetlistTest(unittest.TestCase):
    def test_contains_model_and_parts(self):
        nl = build_netlist(base_params(), "op")
        self.assertIn(".model Q2N3904 NPN", nl)
        self.assertIn("Q1", nl)
        self.assertIn("R1", nl)
        self.assertIn("Cin", nl)
        self.assertIn("Cout", nl)
        self.assertIn("RL", nl)

    def test_ac_has_ac_and_wrdata(self):
        nl = build_netlist(base_params(), "ac")
        self.assertIn("ac dec", nl)
        self.assertIn("wrdata ac.txt", nl)

    def test_tran_has_tran_and_wrdata(self):
        nl = build_netlist(base_params(), "tran")
        self.assertIn("tran ", nl)
        self.assertIn("wrdata tran.txt", nl)


class ParseWrdataTest(unittest.TestCase):
    def test_parses_two_columns(self):
        rows = spice_engine.parse_wrdata("0.0  1.5\n1.0  2.5\n", 2)
        self.assertEqual(rows, [[0.0, 1.5], [1.0, 2.5]])

    def test_rejects_empty(self):
        with self.assertRaises(spice_engine.NgspiceError):
            spice_engine.parse_wrdata("", 2)

    def test_rejects_non_finite(self):
        with self.assertRaises(spice_engine.NgspiceError):
            spice_engine.parse_wrdata("1 nan\n", 2)


class RunSimulationTest(unittest.TestCase):
    def test_missing_exe_returns_error(self):
        r = spice_engine.run_simulation(base_params(), "op", ngspice_exe="Z:/missing/ngspice.exe")
        self.assertEqual(r["status"], "error")
        self.assertIn("ngspice", r["error"].lower())

    def test_timeout_returns_error(self):
        with mock.patch("spice_engine.subprocess.run", side_effect=spice_engine.subprocess.TimeoutExpired(cmd="ngspice", timeout=1)):
            with mock.patch("spice_engine.resolve_ngspice", return_value="ngspice"):
                r = spice_engine.run_simulation(base_params(), "op", timeout_s=1)
        self.assertEqual(r["status"], "error")
        self.assertIn("timeout", r["error"].lower())


def _has_ngspice():
    try:
        spice_engine.resolve_ngspice()
        return True
    except FileNotFoundError:
        return False


@unittest.skipUnless(_has_ngspice(), "ngspice not installed")
class NgspiceSmokeTest(unittest.TestCase):
    def test_op_returns_dc_values(self):
        r = spice_engine.run_simulation(base_params(), "op")
        self.assertEqual(r["status"], "ok", r.get("error"))
        for k in ["vb", "ve", "vc", "vce", "ic"]:
            self.assertIn(k, r["data"])

    def test_ac_returns_frequency_data(self):
        r = spice_engine.run_simulation(base_params(), "ac")
        self.assertEqual(r["status"], "ok", r.get("error"))
        self.assertGreater(len(r["data"]["freq_hz"]), 10)

    def test_tran_returns_waveforms(self):
        r = spice_engine.run_simulation(base_params(), "tran")
        self.assertEqual(r["status"], "ok", r.get("error"))
        self.assertGreater(len(r["data"]["time_s"]), 10)
