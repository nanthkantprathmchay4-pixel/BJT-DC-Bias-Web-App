"""Flask entry point for the BJT DC bias calculator."""

from flask import Flask, render_template, request

from dc_bias import calculate, validate
from formatting import fmt_current, fmt_resistance, fmt_voltage

app = Flask(__name__)

DEFAULT_FORM = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}

REGION_LABELS = {
    "active": "Active Region",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
}

FORMULAS = {
    "VTH": "VCC · R2 / (R1 + R2)",
    "RTH": "R1 · R2 / (R1 + R2)",
    "IB": "(VTH − VBE) / (RTH + (β + 1) · RE)",
    "IE": "(β + 1) · IB",
}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        bias_input, errors = validate(request.form)
        if errors:
            return render_template(
                "index.html",
                form=request.form,
                errors=errors,
                results=None,
            )

        result = calculate(bias_input)
        results = {
            "vb": fmt_voltage(result.vb),
            "ve": fmt_voltage(result.ve),
            "vc": fmt_voltage(result.vc),
            "vce": fmt_voltage(result.vce),
            "ic": fmt_current(result.ic),
        }
        steps = [
            ("VTH", FORMULAS["VTH"], fmt_voltage(result.vth)),
            ("RTH", FORMULAS["RTH"], fmt_resistance(result.rth)),
            ("IB", FORMULAS["IB"], fmt_current(result.ib)),
            ("IE", FORMULAS["IE"], fmt_current(result.ie)),
        ]
        return render_template(
            "index.html",
            form=request.form,
            errors={},
            results=results,
            steps=steps,
            region=REGION_LABELS[result.region],
            region_key=result.region,
            warnings=result.warnings,
        )

    return render_template(
        "index.html",
        form=DEFAULT_FORM,
        errors={},
        results=None,
    )
