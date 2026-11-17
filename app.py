"""Flask entry point for the BJT DC bias calculator."""

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
