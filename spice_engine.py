"""ngspice adapter for the CE amplifier simulator.

This module owns netlist generation, subprocess execution, and output parsing.
It knows nothing about Flask or HTML.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

DEFAULT_MODEL_NAME = "2N3904"
NPN_2N3904_MODEL = (
    ".model Q2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259 "
    "Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1 "
    "Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75 "
    "Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)"
)

ANALYSES = ("op", "ac", "tran")


class NgspiceError(RuntimeError):
    """Raised when ngspice cannot be run or its output cannot be parsed."""


@dataclass(frozen=True)
class CEParams:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin_u: float
    cout_u: float
    beta: float
    vbe: float
    vin_mvp: float
    freq_hz: float


def _fmt_eng(value: float) -> str:
    """Format a float for ngspice without locale issues."""
    return f"{value:.12g}"


def build_netlist(params: CEParams, analysis: str) -> str:
    """Build a CE Voltage Divider amplifier netlist for the requested analysis."""
    if analysis not in ANALYSES:
        raise ValueError(f"unknown analysis: {analysis}")

    vin_v = params.vin_mvp / 1000.0
    cin = params.cin_u * 1e-6
    cout = params.cout_u * 1e-6
    tstop = 5.0 / params.freq_hz
    tstep = tstop / 2000.0

    lines = [
        "* BJT CE Amplifier - Lab 04",
        f"VCC vcc 0 DC {_fmt_eng(params.vcc)}",
        f"Vin in 0 DC 0 AC 1 SIN(0 {_fmt_eng(vin_v)} {_fmt_eng(params.freq_hz)})",
        f"Cin in b {_fmt_eng(cin)}",
        f"R1 vcc b {_fmt_eng(params.r1)}",
        f"R2 b 0 {_fmt_eng(params.r2)}",
        f"RC vcc c {_fmt_eng(params.rc)}",
        "Q1 c b e Q2N3904",
        f"RE e 0 {_fmt_eng(params.re)}",
        f"Cout c out {_fmt_eng(cout)}",
        f"RL out 0 {_fmt_eng(params.rl)}",
        NPN_2N3904_MODEL,
        ".control",
        "set noaskquit",
        "set wr_singlescale",
    ]

    if analysis == "op":
        lines += [
            "op",
            "wrdata op.txt v(b) v(e) v(c) v(c,e)",
        ]
    elif analysis == "ac":
        lines += [
            "ac dec 100 10 1Meg",
            "wrdata ac.txt vdb(out) vp(out)",
        ]
    else:  # tran
        lines += [
            f"tran {_fmt_eng(tstep)} {_fmt_eng(tstop)}",
            "wrdata tran.txt v(in) v(out)",
        ]

    lines += ["quit", ".endc", ".end", ""]
    return "\n".join(lines)


def parse_wrdata(text: str, columns: int) -> list[list[float]]:
    """Parse ngspice wrdata output into rows of numeric columns.

    With `set wr_singlescale`, wrdata writes: scale val1 val2 ... per row.
    """
    if columns < 2:
        raise NgspiceError("wrdata columns must be >= 2")
    rows: list[list[float]] = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) != columns:
            raise NgspiceError(
                f"malformed wrdata row: expected {columns} columns, got {len(parts)}"
            )
        try:
            vals = [float(x) for x in parts]
        except ValueError as exc:
            raise NgspiceError(f"non-numeric wrdata value: {exc}") from exc
        if not all(math.isfinite(v) for v in vals):
            raise NgspiceError("non-finite wrdata value")
        rows.append(vals)
    if not rows:
        raise NgspiceError("empty wrdata")
    return rows


def resolve_ngspice(
    explicit: str | None = None,
    env: Mapping[str, str] | None = None,
    which=shutil.which,
    exists=os.path.exists,
) -> str:
    """Return a usable ngspice executable path or raise FileNotFoundError."""
    env = os.environ if env is None else env
    checked: list[str] = []

    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    else:
        env_exe = env.get("NGSPICE_EXE")
        if env_exe:
            candidates.append(env_exe)
        for name in ("ngspice_con", "ngspice_con.exe", "ngspice", "ngspice.exe"):
            found = which(name)
            if found:
                candidates.append(found)

        localapp = env.get("LOCALAPPDATA", "")
        common = [
            os.path.join(localapp, "Programs", "ngspice-47", "Spice64", "bin", "ngspice_con.exe"),
            os.path.join(localapp, "Programs", "ngspice-47", "Spice64", "bin", "ngspice.exe"),
            os.path.join(localapp, "Programs", "ngspice", "bin", "ngspice_con.exe"),
            os.path.join(localapp, "Programs", "ngspice", "bin", "ngspice.exe"),
            r"C:\Spice64\bin\ngspice_con.exe",
            r"C:\Spice64\bin\ngspice.exe",
            r"C:\Program Files\Spice64\bin\ngspice_con.exe",
            r"C:\Program Files\Spice64\bin\ngspice.exe",
        ]
        candidates.extend(common)

    seen: set[str] = set()
    for raw in candidates:
        if not raw:
            continue
        path = str(Path(raw))
        if path in seen:
            continue
        seen.add(path)
        checked.append(path)
        if exists(path):
            return path

    checked_msg = "\n".join(f" - {p}" for p in checked) if checked else " - (none)"
    raise FileNotFoundError(
        "ngspice executable not found. Set NGSPICE_EXE to the full path to ngspice.exe "
        "or install ngspice and add it to PATH.\nChecked:\n" + checked_msg
    )


def _read_log_tail(path: Path, limit: int = 40) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[-limit:])


def _extract_version(text: str) -> str | None:
    m = re.search(r"ngspice-(\d+)", text)
    return m.group(1) if m else None


def _error_result(analysis: str, error: str, log_tail: str = "", version: str | None = None) -> dict:
    return {
        "status": "error",
        "analysis": analysis,
        "engine": "ngspice",
        "engine_version": version,
        "model": DEFAULT_MODEL_NAME,
        "data": {},
        "error": error,
        "log_tail": log_tail,
    }


def run_simulation(
    params: CEParams,
    analysis: str,
    ngspice_exe: str | None = None,
    timeout_s: float = 20.0,
) -> dict:
    """Run ngspice for one CE analysis and return a normalized result dict."""
    if analysis not in ANALYSES:
        return _error_result(analysis, f"unknown analysis: {analysis}")

    try:
        exe = resolve_ngspice(ngspice_exe)
    except FileNotFoundError as exc:
        return _error_result(analysis, str(exc))

    with TemporaryDirectory(prefix="ngspice-run-") as td:
        run_dir = Path(td)
        netlist_path = run_dir / "circuit.cir"
        log_path = run_dir / "run.log"
        netlist_path.write_text(build_netlist(params, analysis), encoding="utf-8")

        cmd = [exe, "-b", "-o", str(log_path), str(netlist_path)]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(run_dir),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return _error_result(analysis, f"ngspice timeout after {timeout_s:g}s", _read_log_tail(log_path))
        except OSError as exc:
            return _error_result(analysis, f"failed to run ngspice: {exc}", _read_log_tail(log_path))

        log_tail = _read_log_tail(log_path)
        version = _extract_version(log_tail + "\n" + (proc.stdout or "") + "\n" + (proc.stderr or ""))

        if proc.returncode != 0:
            msg = f"ngspice exited with code {proc.returncode}"
            if log_tail:
                msg += "; see log tail"
            return _error_result(analysis, msg, log_tail, version)

        try:
            data = _parse_analysis_output(run_dir, analysis, params)
        except (NgspiceError, OSError, ValueError) as exc:
            return _error_result(analysis, f"failed to parse ngspice output: {exc}", log_tail, version)

    return {
        "status": "ok",
        "analysis": analysis,
        "engine": "ngspice",
        "engine_version": version,
        "model": DEFAULT_MODEL_NAME,
        "data": data,
        "error": None,
        "log_tail": log_tail,
    }


def _parse_analysis_output(run_dir: Path, analysis: str, params: CEParams) -> dict:
    if analysis == "op":
        rows = parse_wrdata((run_dir / "op.txt").read_text(encoding="utf-8", errors="replace"), 5)
        # wr_singlescale: scale, v(b), v(e), v(c), v(c,e)
        _, vb, ve, vc, vce = rows[0]
        ic = (params.vcc - vc) / params.rc
        return {"vb": vb, "ve": ve, "vc": vc, "vce": vce, "ic": ic}

    if analysis == "ac":
        rows = parse_wrdata((run_dir / "ac.txt").read_text(encoding="utf-8", errors="replace"), 3)
        # wr_singlescale: freq, vdb(out), vp(out)
        freq = [r[0] for r in rows]
        gain_db = [r[1] for r in rows]
        phase_deg = [r[2] for r in rows]
        return {"freq_hz": freq, "gain_db": gain_db, "phase_deg": phase_deg}

    # tran
    rows = parse_wrdata((run_dir / "tran.txt").read_text(encoding="utf-8", errors="replace"), 3)
    # wr_singlescale: time, v(in), v(out)
    time_s = [r[0] for r in rows]
    vin_v = [r[1] for r in rows]
    vout_v = [r[2] for r in rows]
    return {"time_s": time_s, "vin_v": vin_v, "vout_v": vout_v}
