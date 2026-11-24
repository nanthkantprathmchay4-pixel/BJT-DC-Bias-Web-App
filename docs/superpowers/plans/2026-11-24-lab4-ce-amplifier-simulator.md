# Lab 04 โ€” CE Amplifier Simulator v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Lab 3 BJT DC Bias Flask app with a real ngspice-powered CE Voltage Divider amplifier simulator supporting `.op`, `.ac`, and `.tran`, with server-rendered SVG plots and clear SPICE vs analytical provenance.

**Architecture:** Keep `dc_bias.py` pure and unchanged. Add `spice_engine.py` as the only subprocess/netlist/parsing boundary and `plot_svg.py` as pure SVG rendering. `app.py` validates form input, dispatches to the engine, and renders a new `/simulator` template; existing `/` DC bias modes remain intact.

**Tech Stack:** Python 3/Flask 3.1.3, stdlib `unittest`, stdlib `subprocess/tempfile/pathlib/shutil/math`, ngspice 47 (external CLI), Jinja templates, server-generated SVG.

**Spec:** `docs/superpowers/specs/2026-11-24-lab4-ce-amplifier-simulator-design.md`

## Global Constraints

- `dc_bias.py` must not import Flask/HTML/subprocess; engineering equations stay there only.
- Templates display only; **no client-side JavaScript**.
- Use `unittest` from stdlib only; no pytest, no new plotting deps.
- `subprocess.run` uses argument list, `shell=False`, timeout, and per-run isolated `cwd`.
- Validate all numeric inputs before building netlist; never interpolate raw form text into shell commands.
- ngspice errors/missing executable/timeout/empty output must be reported as error status; never show stale success plot.
- SPICE results and analytical results must be labeled separately.
- Resistors in forms remain kฮฉ in UI, converted to ฮฉ in validation.
- Display 3 decimal places; current >=1 mA in mA else ยตA; resistance >=1000 ฮฉ in kฮฉ else ฮฉ.
- Do not commit `.venv/`, `__pycache__/`, `.env`, credentials, or large temp run artifacts.
- Commit via **GitHub Desktop** only (AGENTS.md).

## Review Focus

- **ngspice missing/unrunnable**: UI shows clear error with install/`NGSPICE_EXE` hint; no traceback, no fake graph.
- **Invalid simulation input (`RE=0`, non-numeric freq/amp, negative/zero sweep bounds)**: rejected before subprocess; old success plot not shown.
- **ngspice returns empty/partial/NaN output**: parser treats as failure with status=error, not a blank/zeroed chart.
- **AC gain reference ambiguity**: plot/labels state gain is `V(out)/V(in_source)` (dB) and phase is degrees; Vin measurement point documented.
- **Lab 3 regression**: `/` and `?mode=fixed|emitter|divider`, A1โ€“A5 behavior, and existing 65 tests remain green.

---

## File Structure

| File | Responsibility |
|---|---|
| `spice_engine.py` | Resolve ngspice executable; define CE circuit dataclasses/constants; generate netlists; run ngspice; parse wrdata/log; return typed result/error objects. No Flask. |
| `plot_svg.py` | Pure SVG generators for AC Bode and transient waveforms from numeric series. No physics, no Flask. |
| `app.py` | Add simulator form validation/dispatch/render for `/simulator`; keep existing DC bias routes unchanged. |
| `templates/index.html` | Add nav link to simulator; keep existing DC bias UI behavior. |
| `templates/simulator.html` | New simulator form, analysis selector, status/provenance, result tables, embedded SVG plots. |
| `static/style.css` | Extend styles for simulator layout, status badges, plot container, responsive behavior. |
| `tests/test_spice_engine.py` | Unit tests for resolver, netlist, parsing, command shape, error handling. Integration smoke tests skipped unless ngspice available. |
| `tests/test_plot_svg.py` | Unit tests for SVG structure/labels/paths/empty-data handling. |
| `tests/test_web_simulator.py` | Flask client tests for simulator GET/POST validation, mocked success, mocked failure, no-stale-success. |
| `README.md` | Add Lab 4 setup/run/ngspice install/model/provenance notes. |
| `docs/validation.md` | Append Lab 4 B1โ€“B8 real-browser results. |

### Task 1: Install ngspice and add executable resolver

**Files:**
- Create: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `resolve_ngspice(explicit: str | None = None, env: Mapping[str, str] | None = None, which=shutil.which, exists=os.path.exists) -> str` returning absolute executable path or raising `FileNotFoundError` with actionable message including `NGSPICE_EXE`.
- Produces: `NgspiceError(RuntimeError)` for run/parse failures.
- Produces: `DEFAULT_MODEL_NAME = "2N3904"` and `NPN_2N3904_MODEL` constant containing exact `.model` line.

- [ ] **Step 1: Write the failing resolver tests**

```python
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import spice_engine


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
            spice_engine.resolve_ngspice(None, env={}, which=lambda _: None, exists=lambda _: False)
        self.assertIn("NGSPICE_EXE", str(ctx.exception))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.ResolveNgspiceTest -v`  
Expected: FAIL because `spice_engine`/`resolve_ngspice` does not exist.

- [ ] **Step 3: Implement minimal resolver and constants in `spice_engine.py`**

Implement `resolve_ngspice` checking explicit, `NGSPICE_EXE`, `which("ngspice")`/`which("ngspice.exe")`, then common Windows locations under `LOCALAPPDATA/Programs/ngspice*` and `C:\Spice64\bin\ngspice.exe`; raise `FileNotFoundError` with checked locations and `NGSPICE_EXE` hint. Add:

```python
DEFAULT_MODEL_NAME = "2N3904"
NPN_2N3904_MODEL = (
    ".model Q2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259 "
    "Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1 "
    "Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75 "
    "Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)"
)
class NgspiceError(RuntimeError):
    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.ResolveNgspiceTest -v`  
Expected: PASS.

- [ ] **Step 5: Install portable ngspice 47 and smoke-test**

Run:
```powershell
$dst="$env:LOCALAPPDATA\Programs\ngspice-47"
New-Item -ItemType Directory -Force $dst | Out-Null
Invoke-WebRequest -Uri "https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/ngspice-47_64.7z/download" -OutFile "$dst\ngspice-47_64.7z"
& "C:\Program Files\7-Zip\7z.exe" x "$dst\ngspice-47_64.7z" -o"$dst" -y
Get-ChildItem $dst -Recurse -Filter ngspice.exe | Select-Object -First 1 -Expand FullName
```
Then set for current shell: `$env:NGSPICE_EXE=<found path>` and run `<found> -v`.  
Expected: ngspice version output contains `47`.

- [ ] **Step 6: Commit**

```bash
Stage `spice_engine.py tests/test_spice_engine.py` and commit via **GitHub Desktop** with message `feat: add ngspice resolver and model constants`
```

### Task 2: Netlist builder for CE reference circuit

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class CEParams` with fields `vcc, r1, r2, rc, re, rl, cin_u, cout_u, beta, vbe, vin_mvp, freq_hz` (resistors stored in ohms in dataclass; validation converts kฮฉ->ฮฉ before construction).
- Produces: `build_netlist(params: CEParams, analysis: str) -> str` where `analysis in {"op","ac","tran"}`.
- Produces: `ANALYSES = ("op", "ac", "tran")`.

- [ ] **Step 1: Write failing netlist tests**

```python
from spice_engine import CEParams, build_netlist, DEFAULT_MODEL_NAME


def base_params():
    return CEParams(12.0, 100e3, 22e3, 2.2e3, 1e3, 10e3, 10.0, 10.0, 100.0, 0.7, 10.0, 1000.0)


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
        self.assertIn(".ac dec", nl)
        self.assertIn("wrdata", nl)

    def test_tran_has_tran_and_wrdata(self):
        nl = build_netlist(base_params(), "tran")
        self.assertIn(".tran", nl)
        self.assertIn("wrdata", nl)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.NetlistTest -v`  
Expected: FAIL missing `CEParams/build_netlist`.

- [ ] **Step 3: Implement netlist builder**

Add `CEParams` dataclass and `build_netlist`. Netlist topology (node names fixed for parser):
```text
VCC vcc 0 DC {vcc}
Vin in 0 DC 0 AC 1 SIN(0 {vin_v} {freq})
Cin in b {cin}
R1 vcc b {r1}
R2 b 0 {r2}
RC vcc c {rc}
Q1 c b e Q2N3904
RE e 0 {re}
Cout c out {cout}
RL out 0 {rl}
```
Use `.control ... run; wrdata <file> <vectors>; quit .endc`. For `op`: `op`; `wrdata op.txt v(b) v(e) v(c) v(c,e) i(vc)`. For `ac`: `ac dec 100 10 1Meg`; `wrdata ac.txt vdb(out) vp(out) vdb(in)`. For `tran`: compute `tstop=5/freq`, `tstep=tstop/2000`; `tran {tstep} {tstop}`; `wrdata tran.txt v(in) v(out)`. Include model constant.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.NetlistTest -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
Stage `spice_engine.py tests/test_spice_engine.py` and commit via **GitHub Desktop** with message `feat: build CE amplifier ngspice netlists`
```

### Task 3: wrdata parser and run adapter

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `parse_wrdata(text: str, columns: int) -> list[list[float]]` returning rows with `columns` floats; raises `NgspiceError` on empty/malformed/non-finite.
- Produces: `run_simulation(params: CEParams, analysis: str, ngspice_exe: str | None = None, timeout_s: float = 20.0) -> dict` with keys `status`, `analysis`, `engine`, `model`, `data`, `log_tail`, `error`.
- Produces: `SpiceRunResult` dataclass or typed dict (choose one; keep consistent) used by app.

- [ ] **Step 1: Write failing parser tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.ParseWrdataTest -v`  
Expected: FAIL.

- [ ] **Step 3: Implement parser**

`parse_wrdata` splits lines, ignores blank lines, parses floats, requires exact column count, rejects `not math.isfinite`, raises `NgspiceError("empty wrdata")` if no rows.

- [ ] **Step 4: Run parser tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.ParseWrdataTest -v`  
Expected: PASS.

- [ ] **Step 5: Write failing run adapter tests with mocked subprocess**

```python
from unittest import mock

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
```

- [ ] **Step 6: Run to verify fail, then implement run adapter**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.RunSimulationTest -v` (expect FAIL before impl).  
Implement `run_simulation`: resolve exe; make `TemporaryDirectory()` as cwd; write `circuit.cir`; run `[exe, "-b", "-o", "run.log", "circuit.cir"]` with `shell=False`, `capture_output=True`, `text=True`, `timeout=timeout_s`, `cwd=tmp`; on non-zero exit/timeout/missing file/parse error return error dict with `log_tail`; on success parse expected wrdata file and map into `data` by analysis. **Verify wrdata column layout with real ngspice 47 first** (it may repeat scale columns per vector); lock parser to observed format with tests.

- [ ] **Step 7: Run tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine -v`  
Expected: PASS.

- [ ] **Step 8: Add real ngspice smoke test (skip if unavailable)**

```python
@unittest.skipUnless(os.environ.get("NGSPICE_EXE") or shutil.which("ngspice"), "ngspice not installed")
class NgspiceSmokeTest(unittest.TestCase):
    def test_op_returns_dc_values(self):
        r = spice_engine.run_simulation(base_params(), "op")
        self.assertEqual(r["status"], "ok")
        self.assertIn("vce", r["data"])
```

Run: `.venv\Scripts\python.exe -m unittest tests.test_spice_engine.NgspiceSmokeTest -v`  
Expected: PASS when `NGSPICE_EXE` set.

- [ ] **Step 9: Commit**

```bash
Stage `spice_engine.py tests/test_spice_engine.py` and commit via **GitHub Desktop** with message `feat: run ngspice and parse wrdata results`
```

### Task 4: Server-rendered SVG plots

**Files:**
- Create: `plot_svg.py`
- Test: `tests/test_plot_svg.py`

**Interfaces:**
- Produces: `bode_svg(freq_hz: list[float], gain_db: list[float], phase_deg: list[float]) -> str`
- Produces: `transient_svg(time_s: list[float], vin_v: list[float], vout_v: list[float]) -> str`
- Produces: `PlotError(ValueError)` for empty/non-finite/mismatched series.

- [ ] **Step 1: Write failing SVG tests**

```python
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
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_plot_svg -v`  
Expected: FAIL.

- [ ] **Step 3: Implement minimal pure SVG renderer**

Implement helpers for scale, ticks, polyline path, and two chart functions. No external deps. Escape text. Use viewBox, axes, gridlines, legend. Bode: log-frequency x axis; show gain and phase traces with two y-axis labels (left dB, right deg) or two stacked panels - pick one and keep readable.

- [ ] **Step 4: Run tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_plot_svg -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
Stage `plot_svg.py tests/test_plot_svg.py` and commit via **GitHub Desktop** with message `feat: render simulation plots as server SVG`
```

### Task 5: Simulator route, template, and validation

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Create: `templates/simulator.html`
- Modify: `static/style.css`
- Test: `tests/test_web_simulator.py`

**Interfaces:**
- Produces: `GET/POST /simulator` route.
- Produces: form fields `vcc,r1,r2,rc,re,rl,cin,cout,beta,vbe,vin_mvp,freq_hz,analysis`.
- Produces: template context keys `analysis`, `fields`, `errors`, `run_status`, `engine`, `model`, `spice`, `reference`, `plot_svg`, `log_tail`.
- Consumes: `spice_engine.run_simulation`, `spice_engine.CEParams`, `plot_svg.bode_svg/transient_svg`.

- [ ] **Step 1: Write failing web tests**

```python
import unittest
from unittest import mock
from app import app


class SimulatorWebTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_simulator_has_form(self):
        body = self.client.get("/simulator").get_data(as_text=True)
        self.assertEqual(self.client.get("/simulator").status_code, 200)
        for name in ["vcc","r1","r2","rc","re","rl","cin","cout","vin_mvp","freq_hz"]:
            self.assertIn(f'name="{name}"', body)

    def test_invalid_re_shows_error(self):
        data = {"vcc":"12","r1":"100","r2":"22","rc":"2.2","re":"0","rl":"10","cin":"10","cout":"10","beta":"100","vbe":"0.7","vin_mvp":"10","freq_hz":"1000","analysis":"op"}
        body = self.client.post("/simulator", data=data).get_data(as_text=True)
        self.assertIn("เธเธงเธฒเธกเธ•เนเธฒเธเธ—เธฒเธเธ•เนเธญเธเธกเธฒเธเธเธงเนเธฒ 0", body)
        self.assertNotIn("Run Status: ok", body)

    def test_engine_error_has_no_stale_success(self):
        data = {"vcc":"12","r1":"100","r2":"22","rc":"2.2","re":"1","rl":"10","cin":"10","cout":"10","beta":"100","vbe":"0.7","vin_mvp":"10","freq_hz":"1000","analysis":"op"}
        with mock.patch("app.run_simulation", return_value={"status":"error","error":"ngspice missing","log_tail":"","engine":"ngspice","model":"2N3904","analysis":"op","data":{}}):
            body = self.client.post("/simulator", data=data).get_data(as_text=True)
        self.assertIn("ngspice missing", body)
        self.assertNotIn("status-ok", body)
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web_simulator -v`  
Expected: FAIL (no route).

- [ ] **Step 3: Implement validation and route**

Add simulator defaults/field metadata in `app.py`. Validate with same style/messages as `dc_bias.validate` where possible. Build `CEParams` only on valid input. Call `run_simulation`; on ok generate SVG via `plot_svg`; on error render error. Never include old plot on error. Add nav link in `index.html` to `/simulator`.

- [ ] **Step 4: Create template and styles**

`simulator.html`: extends visual style, shows form, analysis selector, Run button, status badge, provenance box (`Engine: ngspice`, model, version if available), DC result table, SVG plot area, log tail on error. `style.css`: responsive two-column/stack layout, `.status-ok/.status-error`, `.plot-wrap svg {max-width:100%;height:auto;}`.

- [ ] **Step 5: Run tests**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web_simulator tests.test_web -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
Stage `app.py templates/index.html templates/simulator.html static/style.css tests/test_web_simulator.py` and commit via **GitHub Desktop** with message `feat: add CE amplifier simulator web UI`
```

### Task 6: Real ngspice verification, docs, and B1โ€“B8 evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/validation.md`
- Create: `docs/evidence/lab4/` (screenshots/logs as needed)

**Interfaces:**
- Produces: README sections for Lab 4 setup, ngspice install, `NGSPICE_EXE`, model name/params, how to run simulator, how to verify.
- Produces: validation table B1โ€“B8 with real observed values/status/evidence.

- [ ] **Step 1: Run full unit tests**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`  
Expected: all existing + new tests PASS.

- [ ] **Step 2: Run real simulator smoke with ngspice**

Run app and exercise `/simulator` for op/ac/tran with default values; capture ngspice version and one log snippet.  
Expected: all three analyses return status ok and plots/data change when source/frequency/RE changes.

- [ ] **Step 3: Execute B1โ€“B8 with Playwright MCP/browser tool and record evidence**

Cover regression A1-equivalent, DC SPICE op, RE change, AC, tran 10mV 1kHz, source change, invalid/fail, desktop+390px UI. Save screenshots under `docs/evidence/lab4/`. Record real observed outputs and PASS/FAIL/NOT RUN honestly.

- [ ] **Step 4: Update README and validation**

Document exact ngspice version, install path/env var, 2N3904 model string, run commands, and limitations (no CE bypass, reference circuit only, SPICE vs analytical assumptions).

- [ ] **Step 5: Final verification**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`  
Expected: PASS. Confirm `git status` has no `.venv`/cache artifacts.

- [ ] **Step 6: Commit**

```bash
Stage changed files and commit via **GitHub Desktop** with message `docs: record Lab 4 validation and simulator setup` (exclude `.venv`, caches, credentials)
```

## Self-Review Notes

- **Spec coverage:** Preserved Lab 3 modes/tests (Tasks 5,6 + regression). Real ngspice `.op/.ac/.tran` (Tasks 1-3,5). SVG plots (Task 4). Provenance/SPICE vs analytical separation (Task 5). B1-B8 validation (Task 6). README install/run (Task 6). No JS (Global Constraints). Error handling (Tasks 3,5).
- **Placeholder scan:** No TBD; wrdata/control compatibility has explicit verification/fallback in Task 3/Spec risk.
- **Type consistency:** `CEParams` defined Task 2, used Tasks 3,5. `run_simulation` dict shape defined Task 3, consumed Task 5. SVG functions defined Task 4, consumed Task 5.
- **Review Focus mapped:** missing ngspice -> Task 1/3/5 tests; invalid input before subprocess -> Task 5; empty/NaN output -> Task 3; AC reference labeled -> Task 4/5; Lab 3 regression -> Task 5/6.
- **Proportion:** Plan is detailed but code blocks are limited to signatures/assertions/key netlist shape; implementers write bodies.

