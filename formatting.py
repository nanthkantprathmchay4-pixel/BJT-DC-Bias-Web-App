"""Presentation helpers that turn raw SI values into display strings."""

MILLI = 1e-3
MICRO = 1e-6
KILO = 1_000.0


def fmt_voltage(volts: float) -> str:
    return f"{volts:.3f} V"


def fmt_current(amps: float) -> str:
    if amps >= MILLI:
        return f"{amps * 1e3:.3f} mA"
    return f"{amps * 1e6:.3f} µA"


def fmt_resistance(ohms: float) -> str:
    if ohms >= KILO:
        return f"{ohms / KILO:.3f} kΩ"
    return f"{ohms:.3f} Ω"
