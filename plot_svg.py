"""Pure SVG rendering for simulation plots.

No Flask, no physics. Input is numeric series; output is SVG markup.
"""

from __future__ import annotations

import math


class PlotError(ValueError):
    """Raised when plot data is invalid."""


def _check_series(*series: list[float]) -> None:
    if not series or any(len(s) == 0 for s in series):
        raise PlotError("empty series")
    n = len(series[0])
    if any(len(s) != n for s in series):
        raise PlotError("series length mismatch")
    for s in series:
        for v in s:
            if not math.isfinite(v):
                raise PlotError("non-finite value")


def _scale_linear(value: float, vmin: float, vmax: float, out_min: float, out_max: float) -> float:
    if vmax == vmin:
        return (out_min + out_max) / 2
    t = (value - vmin) / (vmax - vmin)
    return out_min + t * (out_max - out_min)


def _scale_log(value: float, vmin: float, vmax: float, out_min: float, out_max: float) -> float:
    value = max(value, 1e-12)
    vmin = max(vmin, 1e-12)
    vmax = max(vmax, 1e-12)
    if vmax == vmin:
        return (out_min + out_max) / 2
    lv = math.log10(value)
    lmin = math.log10(vmin)
    lmax = math.log10(vmax)
    t = (lv - lmin) / (lmax - lmin)
    return out_min + t * (out_max - out_min)


def _nice_ticks(vmin: float, vmax: float, count: int = 5) -> list[float]:
    if vmax == vmin:
        return [vmin]
    span = vmax - vmin
    step = span / max(count - 1, 1)
    mag = 10 ** math.floor(math.log10(step)) if step > 0 else 1
    norm = step / mag
    if norm < 1.5:
        nice = 1
    elif norm < 3.5:
        nice = 2
    elif norm < 7.5:
        nice = 5
    else:
        nice = 10
    step = nice * mag
    start = math.floor(vmin / step) * step
    ticks = []
    t = start
    for _ in range(20):
        if t > vmax + step * 0.01:
            break
        if t >= vmin - step * 0.01:
            ticks.append(t)
        t += step
    return ticks or [vmin, vmax]


def _polyline(xs: list[float], ys: list[float], color: str) -> str:
    if not xs:
        return ""
    d = " ".join(
        ("M" if i == 0 else "L") + f"{x:.2f},{y:.2f}" for i, (x, y) in enumerate(zip(xs, ys))
    )
    return f'<path fill="none" stroke="{color}" stroke-width="2" d="{d}"/>'


def _text(x: float, y: float, txt: str, size: int = 12, anchor: str = "middle", fill: str = "#17344b", rotate: float | None = None) -> str:
    esc = (
        str(txt)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    rot = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"{rot}>{esc}</text>'


def bode_svg(freq_hz: list[float], gain_db: list[float], phase_deg: list[float]) -> str:
    _check_series(freq_hz, gain_db, phase_deg)
    if any(f <= 0 for f in freq_hz):
        raise PlotError("frequency must be > 0")

    W, H = 760, 520
    ml, mr = 72, 30
    top_h = 180
    gap = 70
    bot_h = 180
    top_y = 40
    bot_y = top_y + top_h + gap
    plot_w = W - ml - mr

    fmin, fmax = min(freq_hz), max(freq_hz)
    gmin, gmax = min(gain_db), max(gain_db)
    pmin, pmax = min(phase_deg), max(phase_deg)
    if gmax == gmin:
        gmax, gmin = gmax + 1, gmin - 1
    if pmax == pmin:
        pmax, pmin = pmax + 10, pmin - 10
    gpad = (gmax - gmin) * 0.1
    ppad = (pmax - pmin) * 0.1
    gmin -= gpad
    gmax += gpad
    pmin -= ppad
    pmax += ppad

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Bode plot">',
        f'<rect width="{W}" height="{H}" fill="#fbfdff"/>',
        _text(W / 2, 22, "AC Frequency Response (Bode)", 15, fill="#103658"),
    ]

    def panel(y0, h, ymin, ymax, y_label, series, color, label):
        parts.append(f'<rect x="{ml}" y="{y0}" width="{plot_w}" height="{h}" fill="#fff" stroke="#d3e0ec"/>')
        for t in _nice_ticks(ymin, ymax):
            yy = _scale_linear(t, ymax, ymin, y0, y0 + h)
            parts.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml+plot_w}" y2="{yy:.1f}" stroke="#e6eef5"/>')
            parts.append(_text(ml - 8, yy + 4, f"{t:.3g}", 10, anchor="end", fill="#546d83"))
        for f in [10, 100, 1000, 10000, 100000, 1000000]:
            if fmin <= f <= fmax:
                xx = _scale_log(f, fmin, fmax, ml, ml + plot_w)
                parts.append(f'<line x1="{xx:.1f}" y1="{y0}" x2="{xx:.1f}" y2="{y0+h}" stroke="#eef3f8"/>')
                parts.append(_text(xx, y0 + h + 18, f"{f:g}", 10, fill="#546d83"))
        xs = [_scale_log(f, fmin, fmax, ml, ml + plot_w) for f in freq_hz]
        ys = [_scale_linear(v, ymax, ymin, y0, y0 + h) for v in series]
        parts.append(_polyline(xs, ys, color))
        parts.append(_text(18, y0 + h / 2, y_label, 12, fill="#103658", rotate=-90))
        parts.append(_text(ml + 8, y0 + 16, label, 11, anchor="start", fill=color))

    panel(top_y, top_h, gmin, gmax, "Gain (dB)", gain_db, "#0c8078", "Magnitude |Vout/Vin| (dB)")
    panel(bot_y, bot_h, pmin, pmax, "Phase (deg)", phase_deg, "#b85c2c", "Phase (deg)")
    parts.append(_text(ml + plot_w / 2, H - 12, "Frequency (Hz)", 12, fill="#103658"))
    parts.append("</svg>")
    return "\n".join(parts)


def transient_svg(time_s: list[float], vin_v: list[float], vout_v: list[float]) -> str:
    _check_series(time_s, vin_v, vout_v)

    W, H = 760, 360
    ml, mr, mt, mb = 72, 24, 40, 50
    pw, ph = W - ml - mr, H - mt - mb

    tmin, tmax = min(time_s), max(time_s)
    ymin = min(min(vin_v), min(vout_v))
    ymax = max(max(vin_v), max(vout_v))
    if ymax == ymin:
        ymax, ymin = ymax + 0.1, ymin - 0.1
    pad = (ymax - ymin) * 0.1
    ymin -= pad
    ymax += pad

    # display time in ms
    t_ms = [t * 1000.0 for t in time_s]
    tmin_ms, tmax_ms = tmin * 1000.0, tmax * 1000.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Transient plot">',
        f'<rect width="{W}" height="{H}" fill="#fbfdff"/>',
        _text(W / 2, 22, "Transient Response", 15, fill="#103658"),
        f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="#fff" stroke="#d3e0ec"/>',
    ]

    for t in _nice_ticks(ymin, ymax):
        yy = _scale_linear(t, ymax, ymin, mt, mt + ph)
        parts.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{ml+pw}" y2="{yy:.1f}" stroke="#e6eef5"/>')
        parts.append(_text(ml - 8, yy + 4, f"{t:.3g}", 10, anchor="end", fill="#546d83"))

    for t in _nice_ticks(tmin_ms, tmax_ms):
        xx = _scale_linear(t, tmin_ms, tmax_ms, ml, ml + pw)
        parts.append(f'<line x1="{xx:.1f}" y1="{mt}" x2="{xx:.1f}" y2="{mt+ph}" stroke="#eef3f8"/>')
        parts.append(_text(xx, mt + ph + 18, f"{t:.3g}", 10, fill="#546d83"))

    xpts = [_scale_linear(t, tmin_ms, tmax_ms, ml, ml + pw) for t in t_ms]
    vin_y = [_scale_linear(v, ymax, ymin, mt, mt + ph) for v in vin_v]
    vout_y = [_scale_linear(v, ymax, ymin, mt, mt + ph) for v in vout_v]
    parts.append(_polyline(xpts, vin_y, "#0c8078"))
    parts.append(_polyline(xpts, vout_y, "#b85c2c"))

    parts.append(_text(18, mt + ph / 2, "Voltage (V)", 12, fill="#103658", rotate=-90))
    parts.append(_text(ml + pw / 2, H - 10, "Time (ms)", 12, fill="#103658"))
    parts.append(_text(ml + 12, mt + 16, "Vin", 11, anchor="start", fill="#0c8078"))
    parts.append(_text(ml + 50, mt + 16, "Vout", 11, anchor="start", fill="#b85c2c"))
    parts.append("</svg>")
    return "\n".join(parts)
