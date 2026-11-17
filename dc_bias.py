"""DC bias calculations for a BJT common-emitter voltage-divider circuit.

This module is pure engineering logic: it knows nothing about Flask, HTTP or
HTML. All resistances are in ohms, all voltages in volts and all currents in
amperes.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass

SATURATION_VCE_LIMIT = 0.2

MODES = ("divider", "fixed", "emitter")

MODE_FIELDS = {
    "divider": ("vcc", "beta", "r1", "r2", "rc", "re", "vbe"),
    "fixed": ("vcc", "beta", "rb", "rc", "vbe"),
    "emitter": ("vcc", "beta", "rb", "rc", "re", "vbe"),
}

RESISTOR_FIELDS = ("r1", "r2", "rc", "re", "rb")

KILO = 1_000.0

MISSING_MESSAGE = "กรุณากรอกค่านี้"
NUMBER_MESSAGE = "ต้องเป็นตัวเลข"
TOO_LARGE_MESSAGE = "ค่ามากเกินไป"
VCC_MESSAGE = "VCC ต้องมากกว่า 0"
RESISTANCE_MESSAGE = "ความต้านทานต้องมากกว่า 0"
BETA_MESSAGE = "β ต้องมากกว่า 0"
VBE_MESSAGE = "VBE ต้องอยู่ระหว่าง 0 ถึง VCC"

UNKNOWN_MODE_MESSAGE = "ไม่รู้จักโหมดวงจรที่เลือก"

CUTOFF_WARNING = "วงจรอยู่ในช่วง Cutoff — แบบจำลอง Forward-Active ใช้ไม่ได้"
SATURATION_WARNING = (
    "VCE ต่ำกว่า 0.2 V — ใกล้หรือเข้าสู่ Saturation ค่าที่ได้ไม่น่าเชื่อถือ"
)


@dataclass(frozen=True)
class BiasInput:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class FixedBiasInput:
    vcc: float
    rb: float
    rc: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class EmitterBiasInput:
    vcc: float
    rb: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class BiasResult:
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: list[str]
    vth: float | None = None
    rth: float | None = None


def calculate(p: BiasInput) -> BiasResult:
    vth = p.vcc * p.r2 / (p.r1 + p.r2)
    rth = p.r1 * p.r2 / (p.r1 + p.r2)

    if vth <= p.vbe:
        return BiasResult(
            vth=vth,
            rth=rth,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=vth,
            ve=0.0,
            vc=p.vcc,
            vce=p.vcc,
            region="cutoff",
            warnings=[CUTOFF_WARNING],
        )

    ib = (vth - p.vbe) / (rth + (p.beta + 1) * p.re)
    ic = p.beta * ib
    ie = (p.beta + 1) * ib
    ve = ie * p.re
    vb = ve + p.vbe
    vc = p.vcc - ic * p.rc
    vce = vc - ve

    if vce <= SATURATION_VCE_LIMIT:
        return BiasResult(
            vth=vth,
            rth=rth,
            ib=ib,
            ic=ic,
            ie=ie,
            vb=vb,
            ve=ve,
            vc=vc,
            vce=vce,
            region="saturation",
            warnings=[SATURATION_WARNING],
        )

    return BiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region="active",
        warnings=[],
    )


def _classify(ib: float, vce: float) -> tuple[str, list[str]]:
    if ib <= 0:
        return "cutoff", [CUTOFF_WARNING]
    if vce <= SATURATION_VCE_LIMIT:
        return "saturation", [SATURATION_WARNING]
    return "active", []


def calculate_fixed(p: FixedBiasInput) -> BiasResult:
    """Fixed bias: base resistor from VCC to base, emitter grounded."""
    ib = (p.vcc - p.vbe) / p.rb
    ic = p.beta * ib
    ie = (p.beta + 1) * ib
    ve = 0.0
    vb = ve + p.vbe
    vc = p.vcc - ic * p.rc
    vce = vc - ve
    region, warnings = _classify(ib, vce)

    return BiasResult(
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )


def calculate_emitter(p: EmitterBiasInput) -> BiasResult:
    """Emitter bias: base resistor from VCC to base plus an emitter resistor."""
    ib = (p.vcc - p.vbe) / (p.rb + (p.beta + 1) * p.re)
    ic = p.beta * ib
    ie = (p.beta + 1) * ib
    ve = ie * p.re
    vb = ve + p.vbe
    vc = p.vcc - ic * p.rc
    vce = vc - ve
    region, warnings = _classify(ib, vce)

    return BiasResult(
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )


def parse_mode(raw: str | None) -> str | None:
    """Map a raw form/query value to a bias mode.

    A missing or empty value means the original voltage-divider mode, so
    callers from Lab 02 keep working. Anything outside MODES is unknown:
    None, never a guess.
    """
    if raw is None or str(raw).strip() == "":
        return "divider"
    return raw if raw in MODES else None


def validate(
    form: Mapping[str, str], mode: str = "divider"
) -> tuple[BiasInput | FixedBiasInput | EmitterBiasInput | None, dict[str, str]]:
    """Parse and check raw form values for one mode, converting kΩ to ohms.

    Only the fields that mode uses are read, so stray values from another
    mode's inputs are ignored. Returns the parsed input dataclass and an empty
    error dict when everything is valid, or None and a per-field error dict
    otherwise.
    """
    if mode not in MODES:
        return None, {"mode": UNKNOWN_MODE_MESSAGE}

    fields = MODE_FIELDS[mode]
    resistor_fields = [field for field in RESISTOR_FIELDS if field in fields]
    errors: dict[str, str] = {}
    values: dict[str, float] = {}

    for field in fields:
        raw = str(form.get(field, "")).strip()
        if not raw:
            errors[field] = MISSING_MESSAGE
            continue
        try:
            number = float(raw)
        except ValueError:
            errors[field] = NUMBER_MESSAGE
            continue
        if not math.isfinite(number):
            errors[field] = NUMBER_MESSAGE
            continue
        values[field] = number

    if "vcc" in values and values["vcc"] <= 0:
        errors["vcc"] = VCC_MESSAGE

    for field in resistor_fields:
        if field in values and values[field] <= 0:
            errors[field] = RESISTANCE_MESSAGE

    if "beta" in values and values["beta"] <= 0:
        errors["beta"] = BETA_MESSAGE

    if "vbe" in values:
        vbe = values["vbe"]
        out_of_range = vbe < 0 or (
            "vcc" in values and vbe >= values["vcc"]
        )
        if out_of_range:
            errors["vbe"] = VBE_MESSAGE

    ohms: dict[str, float] = {}
    for field in resistor_fields:
        if field in values:
            scaled = values[field] * KILO
            if not math.isfinite(scaled):
                errors[field] = TOO_LARGE_MESSAGE
            else:
                ohms[field] = scaled

    if errors:
        return None, errors

    if mode == "fixed":
        return (
            FixedBiasInput(
                vcc=values["vcc"],
                rb=ohms["rb"],
                rc=ohms["rc"],
                beta=values["beta"],
                vbe=values["vbe"],
            ),
            {},
        )

    if mode == "emitter":
        return (
            EmitterBiasInput(
                vcc=values["vcc"],
                rb=ohms["rb"],
                rc=ohms["rc"],
                re=ohms["re"],
                beta=values["beta"],
                vbe=values["vbe"],
            ),
            {},
        )

    return (
        BiasInput(
            vcc=values["vcc"],
            r1=ohms["r1"],
            r2=ohms["r2"],
            rc=ohms["rc"],
            re=ohms["re"],
            beta=values["beta"],
            vbe=values["vbe"],
        ),
        {},
    )
