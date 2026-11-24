"""Flask entry point for the BJT DC bias calculator and CE simulator."""

from __future__ import annotations

import math

from flask import Flask, render_template, request

from dc_bias import (
    MODE_FIELDS,
    MODES,
    UNKNOWN_MODE_MESSAGE,
    calculate,
    calculate_emitter,
    calculate_fixed,
    parse_mode,
    validate,
)
from formatting import fmt_current, fmt_resistance, fmt_voltage
from plot_svg import bode_svg, transient_svg
from spice_engine import CEParams, DEFAULT_MODEL_NAME, run_simulation

app = Flask(__name__)

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

FIELD_LABELS = {
    "vcc": "VCC (V)",
    "beta": "β",
    "rb": "RB (kΩ)",
    "r1": "R1 (kΩ)",
    "r2": "R2 (kΩ)",
    "rc": "RC (kΩ)",
    "re": "RE (kΩ)",
    "vbe": "VBE (V)",
}

DEFAULT_FORMS = {
    "divider": {
        "vcc": "12",
        "r1": "100",
        "r2": "22",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.7",
    },
    "fixed": {
        "vcc": "12",
        "rb": "1000",
        "rc": "2.2",
        "beta": "100",
        "vbe": "0.7",
    },
    "emitter": {
        "vcc": "12",
        "rb": "1000",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.7",
    },
}

REGION_LABELS = {
    "active": "Active Region",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
}

FORMULAS = {
    "VTH": "VCC · R2 / (R1 + R2)",
    "RTH": "R1 · R2 / (R1 + R2)",
    "IB": {
        "divider": "(VTH − VBE) / (RTH + (β + 1) · RE)",
        "fixed": "(VCC − VBE) / RB",
        "emitter": "(VCC − VBE) / (RB + (β + 1) · RE)",
    },
    "IE": "(β + 1) · IB",
}


def _mode_options() -> list[tuple[str, str]]:
    return [(mode, MODE_LABELS[mode]) for mode in MODES]


def _fields(mode: str, values: dict[str, str], errors: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "label": FIELD_LABELS[name],
            "value": values.get(name, ""),
            "error": errors.get(name, ""),
        }
        for name in MODE_FIELDS[mode]
    ]


def _result_for(mode: str, bias_input):
    if mode == "divider":
        return calculate(bias_input)
    if mode == "fixed":
        return calculate_fixed(bias_input)
    if mode == "emitter":
        return calculate_emitter(bias_input)
    raise ValueError(f"unknown mode: {mode}")


def _steps(mode: str, result) -> list[tuple[str, str, str]]:
    steps = []
    if mode == "divider":
        steps.append(("VTH", FORMULAS["VTH"], fmt_voltage(result.vth)))
        steps.append(("RTH", FORMULAS["RTH"], fmt_resistance(result.rth)))
    steps.append(("IB", FORMULAS["IB"][mode], fmt_current(result.ib)))
    steps.append(("IE", FORMULAS["IE"], fmt_current(result.ie)))
    return steps


def _render(mode, fields, results=None, steps=(), region=None, warnings=(), mode_error=None):
    return render_template(
        "index.html",
        mode=mode,
        mode_label=MODE_LABELS.get(mode),
        mode_options=_mode_options(),
        fields=fields,
        results=results,
        steps=steps,
        region=REGION_LABELS.get(region),
        region_key=region,
        warnings=warnings,
        mode_error=mode_error,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        mode = parse_mode(request.form.get("mode"))
    else:
        mode = parse_mode(request.args.get("mode"))

    if mode is None:
        return _render(None, [], mode_error=UNKNOWN_MODE_MESSAGE)

    if request.method == "GET":
        return _render(mode, _fields(mode, DEFAULT_FORMS[mode], {}))

    values = {name: request.form.get(name, "") for name in MODE_FIELDS[mode]}
    bias_input, errors = validate(request.form, mode)
    if errors:
        return _render(mode, _fields(mode, values, errors))

    result = _result_for(mode, bias_input)
    results = {
        "vb": fmt_voltage(result.vb),
        "ve": fmt_voltage(result.ve),
        "vc": fmt_voltage(result.vc),
        "vce": fmt_voltage(result.vce),
        "ic": fmt_current(result.ic),
    }
    return _render(
        mode,
        _fields(mode, values, {}),
        results=results,
        steps=_steps(mode, result),
        region=result.region,
        warnings=result.warnings,
    )


# --- Lab 04: CE amplifier simulator ---


SIM_FIELDS = ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "beta", "vbe", "vin_mvp", "freq_hz")
SIM_LABELS = {
    "vcc": "VCC (V)",
    "r1": "R1 (kΩ)",
    "r2": "R2 (kΩ)",
    "rc": "RC (kΩ)",
    "re": "RE (kΩ)",
    "rl": "RL (kΩ)",
    "cin": "Cin (µF)",
    "cout": "Cout (µF)",
    "beta": "β",
    "vbe": "VBE (V)",
    "vin_mvp": "Vin amplitude (mV peak)",
    "freq_hz": "Frequency (Hz)",
}
SIM_DEFAULTS = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rl": "10",
    "cin": "10",
    "cout": "10",
    "beta": "100",
    "vbe": "0.7",
    "vin_mvp": "10",
    "freq_hz": "1000",
}
ANALYSIS_LABELS = {"op": "DC (.op)", "ac": "AC (.ac)", "tran": "Transient (.tran)"}


def _validate_sim(form) -> tuple[CEParams | None, dict[str, str], str, dict[str, str]]:
    values = {k: str(form.get(k, "")).strip() for k in SIM_FIELDS}
    analysis = str(form.get("analysis", "op")).strip()
    errors: dict[str, str] = {}
    if analysis not in ANALYSIS_LABELS:
        analysis = "op"

    numbers: dict[str, float] = {}
    for k in SIM_FIELDS:
        raw = values[k]
        if not raw:
            errors[k] = "กรุณากรอกค่านี้"
            continue
        try:
            n = float(raw)
        except ValueError:
            errors[k] = "ต้องเป็นตัวเลข"
            continue
        if not math.isfinite(n):
            errors[k] = "ต้องเป็นตัวเลข"
            continue
        numbers[k] = n

    for k in ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "beta", "freq_hz"):
        if k in numbers and numbers[k] <= 0:
            errors[k] = "ต้องมากกว่า 0" if k in ("freq_hz", "cin", "cout") else "ความต้านทานต้องมากกว่า 0" if k in ("r1", "r2", "rc", "re", "rl") else "ต้องมากกว่า 0"
    if "vcc" in numbers and numbers["vcc"] <= 0:
        errors["vcc"] = "VCC ต้องมากกว่า 0"
    if "beta" in numbers and numbers["beta"] <= 0:
        errors["beta"] = "β ต้องมากกว่า 0"
    if "vin_mvp" in numbers and numbers["vin_mvp"] <= 0:
        errors["vin_mvp"] = "ต้องมากกว่า 0"
    if "vbe" in numbers:
        vbe = numbers["vbe"]
        if vbe < 0 or ("vcc" in numbers and vbe >= numbers["vcc"]):
            errors["vbe"] = "VBE ต้องอยู่ระหว่าง 0 ถึง VCC"
    if analysis == "tran" and "freq_hz" in numbers and numbers["freq_hz"] > 1e6:
        errors["freq_hz"] = "ความถี่สูงเกินไปสำหรับ transient baseline"

    if errors:
        return None, errors, analysis, values

    params = CEParams(
        vcc=numbers["vcc"],
        r1=numbers["r1"] * 1000.0,
        r2=numbers["r2"] * 1000.0,
        rc=numbers["rc"] * 1000.0,
        re=numbers["re"] * 1000.0,
        rl=numbers["rl"] * 1000.0,
        cin_u=numbers["cin"],
        cout_u=numbers["cout"],
        beta=numbers["beta"],
        vbe=numbers["vbe"],
        vin_mvp=numbers["vin_mvp"],
        freq_hz=numbers["freq_hz"],
    )
    return params, {}, analysis, values


def _sim_fields(values: dict[str, str], errors: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "name": k,
            "label": SIM_LABELS[k],
            "value": values.get(k, ""),
            "error": errors.get(k, ""),
        }
        for k in SIM_FIELDS
    ]


def _dc_reference(params: CEParams) -> dict[str, str]:
    # Comparable analytical divider reference using same VCC/R1/R2/RC/RE/beta/VBE.
    from dc_bias import BiasInput, calculate

    ref = calculate(
        BiasInput(
            vcc=params.vcc,
            r1=params.r1,
            r2=params.r2,
            rc=params.rc,
            re=params.re,
            beta=params.beta,
            vbe=params.vbe,
        )
    )
    return {
        "vb": fmt_voltage(ref.vb),
        "ve": fmt_voltage(ref.ve),
        "vc": fmt_voltage(ref.vc),
        "vce": fmt_voltage(ref.vce),
        "ic": fmt_current(ref.ic),
        "region": REGION_LABELS.get(ref.region, ref.region),
    }


@app.route("/simulator", methods=["GET", "POST"])
def simulator():
    if request.method == "GET":
        return render_template(
            "simulator.html",
            analysis="op",
            analysis_options=ANALYSIS_LABELS,
            fields=_sim_fields(SIM_DEFAULTS, {}),
            run_status=None,
            engine="ngspice",
            model=DEFAULT_MODEL_NAME,
            error=None,
            log_tail=None,
            spice=None,
            reference=None,
            plot_svg=None,
        )

    params, errors, analysis, values = _validate_sim(request.form)
    if errors:
        return render_template(
            "simulator.html",
            analysis=analysis,
            analysis_options=ANALYSIS_LABELS,
            fields=_sim_fields(values, errors),
            run_status="error",
            engine="ngspice",
            model=DEFAULT_MODEL_NAME,
            error="ข้อมูลเข้าไม่ถูกต้อง",
            log_tail=None,
            spice=None,
            reference=None,
            plot_svg=None,
        )

    assert params is not None
    sim = run_simulation(params, analysis)
    plot = None
    spice_view = None
    reference = None

    if sim["status"] == "ok":
        if analysis == "op":
            d = sim["data"]
            spice_view = {
                "vb": fmt_voltage(d["vb"]),
                "ve": fmt_voltage(d["ve"]),
                "vc": fmt_voltage(d["vc"]),
                "vce": fmt_voltage(d["vce"]),
                "ic": fmt_current(d["ic"]),
            }
            reference = _dc_reference(params)
        elif analysis == "ac":
            d = sim["data"]
            plot = bode_svg(d["freq_hz"], d["gain_db"], d["phase_deg"])
        else:
            d = sim["data"]
            plot = transient_svg(d["time_s"], d["vin_v"], d["vout_v"])

    return render_template(
        "simulator.html",
        analysis=analysis,
        analysis_options=ANALYSIS_LABELS,
        fields=_sim_fields(values, {}),
        run_status=sim["status"],
        engine=sim.get("engine", "ngspice"),
        engine_version=sim.get("engine_version"),
        model=sim.get("model", DEFAULT_MODEL_NAME),
        error=sim.get("error"),
        log_tail=sim.get("log_tail"),
        spice=spice_view,
        reference=reference,
        plot_svg=plot,
    )
