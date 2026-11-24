# Lab 04 — CE Amplifier Simulator v1 Design

**Date:** 2026-11-24  
**Status:** Draft for approval  
**Scope:** Extend Lab 3 BJT DC Bias Web App into a minimal working Common-Emitter Amplifier Simulator v1.

## Intent / Why

Lab 3 already calculates analytical DC bias for Fixed, Emitter, and Voltage Divider modes. Lab 4 adds a real SPICE simulation path for one reference Common-Emitter Voltage Divider amplifier so students can compare analytical reasoning with ngspice `.op`, `.ac`, and `.tran` results in a browser, with visible provenance and engineering units.

## Goals

- Preserve all three Lab 3 analytical DC bias modes, routes, and existing tests.
- Add a CE Voltage Divider amplifier simulator that runs real ngspice:
  - DC operating point (`.op`) — VB, VE, VC, VCE, IC.
  - AC frequency response (`.ac`) — magnitude `|Vout/Vin|` and phase vs frequency.
  - Transient response (`.tran`) — Vin and Vout vs time.
- Show run status, engine version/name, BJT model name, units, and data provenance.
- Distinguish SPICE simulation results from analytical/reference results; never merge them as one value.
- Provide B1–B8 browser acceptance evidence in `docs/validation.md`.
- Keep the app reproducible from README.

## Non-goals

- No drag-and-drop circuit editor, free-form netlist editor, or arbitrary circuit builder.
- No AC/Transient simulation for Fixed or Emitter bias modes in v1.
- No emitter bypass capacitor (`CE`) in baseline.
- No JavaScript chart library / client-side physics calculation (AGENTS forbids JS).
- No SPICE solver implementation in Python.
- No deployment/public hosting work.

## Anti-goals

- Fabricating plots, hard-coding success values, or showing stale graphs with a success status.
- Hiding ngspice errors/timeouts/missing executable conditions.
- Replacing Lab 3 analytical paths or deleting existing tests.

## Constraints

- `dc_bias.py` remains pure engineering logic: no Flask, no HTML, no subprocess.
- `app.py` validates input, dispatches by mode/analysis, and renders template data.
- `formatting.py` formats/presents only; no physics.
- Templates display only; **no client-side JavaScript** (AGENTS rule). Plots are server-generated SVG.
- Use `unittest` stdlib only; TDD for new behavior.
- `subprocess.run` with argument list, `shell=False`, timeout, isolated working directory per run.
- Inputs validated before netlist generation; form text never interpolated unsafely into shell commands.
- ngspice is an external program; code must handle missing executable, non-zero exit, empty/invalid output, and timeout.

## Decisions Already Made (User)

- **B:** No instructor starter kit available. Install portable ngspice via SourceForge download; use standard **2N3904** BJT model with documented parameters.
- **1:** Charts are **Python-generated SVG** embedded in HTML. ngspice output captured via control-block `wrdata` plain-text files for easy parsing. No matplotlib/numpy/Chart.js dependency.

## Approaches Considered

| Approach | Summary | Trade-off | Verdict |
|---|---|---|---|
| **1. Server SVG + `wrdata` text (picked)** | For each analysis run ngspice `-b` on a generated netlist with `.control`/`wrdata`; parse plain numeric columns; render SVG in Jinja. | More code to draw SVG axes/paths, but no new deps, no JS, fully testable, provenance is clear. | **Picked** — fits AGENTS (no JS), reproducible, easy to unit-test parser/SVG. |
| 2. matplotlib PNG + raw-file parse | Generate PNG plots, parse ngspice binary/raw output. | Adds numpy/matplotlib and binary parsing complexity; harder to test exact plot data; binary artifacts. | Rejected — unnecessary deps and harder parsing. |
| 3. Chart.js client-side | Return JSON and render charts in browser. | Interactive, but violates AGENTS no-JS rule and moves display logic to client. | Rejected — conflicts with project rule. |

## Architecture / How

### File layout (reuse before rebuild)

```text
app.py                     # add simulator route/dispatch; keep Lab 3 routes intact
dc_bias.py                 # unchanged analytical modes
formatting.py              # add small helpers only if needed (no physics)
spice_engine.py            # NEW: resolve ngspice, build netlist, run, parse, errors
plot_svg.py                # NEW: pure SVG rendering from numeric series (no physics)
templates/
  index.html               # keep Lab 3 DC bias page
  simulator.html           # NEW: CE simulator UI
static/style.css           # extend existing styles
docs/validation.md         # append Lab 4 B1–B8
docs/evidence/lab4/        # screenshots/log snippets
tests/
  test_spice_engine.py     # NEW: netlist/parse/command/error paths
  test_plot_svg.py         # NEW: SVG contains axes/labels/data paths
  test_web_simulator.py    # NEW: route validation/rendering with mocked engine
  ...existing tests...
README.md                  # setup, ngspice install, model, run, verify
```

`index.html` may gain a nav link to simulator; existing Lab 3 behavior remains default.

### Simulation path

1. Browser submits CE parameters + analysis mode + source settings.
2. `app.py` validates numeric/range/unit fields; rejects invalid input before any subprocess.
3. `spice_engine.py` resolves ngspice executable:
   - `NGSPICE_EXE` env var if file exists
   - `shutil.which("ngspice")` / `ngspice.exe`
   - common local install path under `%LOCALAPPDATA%\Programs\ngspice` (documented)
4. Adapter creates a unique temp working directory per run, writes netlist, runs:
   ```text
   [ngspice_exe, "-b", "-o", "run.log", "circuit.cir"]
   ```
   with `shell=False`, `timeout`, `cwd=run_dir`, captured output.
5. Netlist contains analysis directives and `.control` block using `wrdata` to emit plain text columns for the selected analysis. (We will verify this pattern with the installed ngspice 47 Windows build before finalizing parser; if incompatible, switch to an ASCII raw/print parse with tests.)
6. Parser reads wrdata/log, converts to floats, checks required columns/non-empty/finite values.
7. `app.py` formats values, builds SVG plot, renders template with provenance metadata: engine=`ngspice`, version, model=`2N3904`, analysis, timestamp/run id, status.

### CE reference circuit (baseline)

Voltage Divider CE, no `CE` bypass:

- VCC, R1, R2, RC, RE, RL, Cin, Cout, Q1 (2N3904), Vin AC source.
- Defaults: VCC 12V, R1 100k, R2 22k, RC 2.2k, RE 1k, RL 10k, Cin 10u, Cout 10u, Vin 10mV peak, 1kHz.
- Node convention documented in code/comments: Vin source node, base after Cin, collector, emitter, Vout after Cout to RL.

### Analyses

- **DC `.op`**: report VB, VE, VC, VCE, IC (and IB/IE if available). Capacitors open in DC; results from operating point.
- **AC `.ac`**: decade sweep (default 10 Hz–1 MHz or configurable range within safe bounds), output magnitude `20*log10(|Vout/Vin|)` in dB and phase in degrees. Vin measurement point explicitly documented.
- **Transient `.tran`**: step/stop derived from source frequency (e.g., 5 cycles, reasonable step), plot Vin and Vout vs time.

### Error handling / provenance

- Missing ngspice: clear error status, install hint, no fake plot.
- Non-zero exit / timeout / parse failure: show error summary + log tail (sanitized), status=error, no stale success graph.
- UI always labels result source: `SPICE (ngspice)` or `Analytical (dc_bias.py)`.
- DC analytical reference may be shown alongside SPICE DC for the same CE bias parameters only when assumptions are comparable; label differences as model assumption differences.

## Testing / Verification

TDD with `unittest`:

- `test_spice_engine.py`: netlist contains expected nodes/components/directives; command is list with `-b`; missing executable raises/returns clean error; parser rejects empty/malformed/non-finite data; timeout handled.
- `test_plot_svg.py`: SVG has axes labels, units, polyline/path points, handles empty data as error.
- `test_web_simulator.py`: GET renders form; invalid input shows errors; mocked successful run renders provenance + SVG; mocked engine failure renders error and no success badge.
- Existing `tests/test_*.py` remain green.

Manual/browser acceptance B1–B8 recorded in `docs/validation.md` with real evidence.

## Risks / Open Checks

- **ngspice control+wrdata in batch mode**: verify on installed ngspice 47 Windows build before finalizing parser. Fallback: parse ASCII raw/print format with tests.
- **2N3904 model parameters**: use a documented standard model; record exact `.model` line in README and netlist comment.
- **AC gain reference**: define Vin as source node before Cin or after source resistance consistently; document it.
- **Cutoff frequency claim**: only report -3dB if sweep/range contains crossing; otherwise show "not determined in sweep range".

## Approval

If you approve this design, I’ll proceed to the implementation plan (`writing-plans`) and then execute in small verified steps: install ngspice portable, add failing tests, implement engine/parser/SVG/routes/UI, run B1–B8, update docs, commit.
