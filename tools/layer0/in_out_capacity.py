"""LAYER 0 -- three numbers per unit (IN / OUT / CAPACITY), one sentence, epistemic tags.

Founder instruction (verbatim, 2026-09-27): "เอาแบบง่ายๆ ก่อน น้ำเข้า น้ำออก ความสามารถในการรับมือ"
(start simple: water in, water out, coping capacity).

**Toledo status**: no new equation. This module is a declared PROPOSAL-derived 3-number
simplification of `PROP-FLOOD-06`'s own `F_H` (inflow term) / `C_H` (capacity/coping band) /
`R_H`+`D_H` (drainage + retention/outflow terms) -- see
`toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md` and `docs/LAYER0_IN_OUT_CAPACITY.md` §3
for the exact term mapping. `time_to_exceed_hours()` below reuses **PROP-FLOOD-02's stated
idea** (`T_k := (theta - h(t))*k / Delta_k(t)`), NOT a live implementation of that proposal --
`AGENTS.md` §8 records `PROP-FLOOD-02` as "referenced in planning docs but not implemented
anywhere in code"; this module keeps that true by doing the arithmetic inline, tagged
`PROPOSAL-derived`, and never claiming PROP-FLOOD-02 itself is now live.

This module WRITES NEW FILES ONLY. It is not wired into `site/build_data.py` or
`site/build_page.py` -- another worker (the sole committer for this branch) decides if/how to
call `render_unit()` / the `build_*` functions from the live pipeline. Every function here is
pure (no network calls); the few functions that read local repo files
(`load_coping_thresholds`, `_read_capacity_ledger_current`) only read files this check's other
collectors already wrote to disk -- no new HTTP request is spent anywhere in this module.

No personal names, no local filesystem paths, no AI/vendor names appear in this file or in any
string it renders (checked by `tests/test_layer0.py::test_no_forbidden_strings`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

TAGS = {
    "VERIFIED",
    "MEASURED",
    "MEASURED-community",
    "MEASURED-history",
    "RELAYED",
    "INSTINCT",
    "OPEN",
    "PROPOSAL-derived",
}

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COPING_THRESHOLDS_PATH = REPO_ROOT / "sources" / "coping_thresholds.yaml"
CAPACITY_LEDGER_PATH = REPO_ROOT / "sources" / "capacity_ledger.yaml"

NEAR_THRESHOLD_FRACTION = 0.80  # founder's own "ใกล้" band: >=80% of threshold


# --------------------------------------------------------------------------- core value type

@dataclass
class Reading:
    """One tagged number (or an explicit refusal when value is None)."""

    value: Optional[float]
    unit: str
    tag: str
    source: str
    observed_at: Optional[str] = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.tag not in TAGS:
            raise ValueError(f"unknown epistemic tag {self.tag!r} (allowed: {sorted(TAGS)})")
        if self.value is None and self.tag not in ("OPEN",):
            # A missing value must be tagged OPEN -- never silently MEASURED/VERIFIED/etc.
            raise ValueError("Reading with value=None must carry tag='OPEN'")

    @property
    def missing(self) -> bool:
        return self.value is None

    def render(self, decimals: int = 1) -> str:
        if self.missing:
            return f"ขาด: {self.source or self.unit}"
        val = self.value
        shown = f"{val:.{decimals}f}" if isinstance(val, float) else str(val)
        return f"{shown} {self.unit} ({self.tag})"


def refused(unit_label: str, reason: str) -> Reading:
    """A correct, honest REFUSED reading -- never fabricate a number to fill the gap
    (AGENTS.md §2, "no equation" rule + this repo's never-fabricate discipline)."""
    return Reading(value=None, unit=unit_label, tag="OPEN", source=reason,
                    note=f"REFUSED: {reason}")


# --------------------------------------------------------------------------- canal backflow

@dataclass
class BackflowState:
    """Founder correction (verbatim, 2026-09-27): "สัมมากรต้องเชื่อมกับน้ำในคลองด้วย เพราะมันเป็น
    น้ำย้อนจากคลอง ไม่ใช่แค่ปั๊ม" -- for any unit connected to a canal, IN must include canal
    backflow as its own term, not only rain + pumps."""

    state: str  # "active" | "not_active" | "unknown" | "likely"
    tag: str
    head_m: Optional[float] = None  # canal level minus pond level, ONLY when same datum
    evidence: list = field(default_factory=list)  # short source strings, no personal names
    note: str = ""

    def render(self) -> str:
        head = f", head {self.head_m:+.2f} m" if self.head_m is not None else ""
        ev = f" [{'; '.join(self.evidence)}]" if self.evidence else ""
        return f"ย้อนจากคลอง: {self.state}{head} ({self.tag}){ev}"


_ALLOWED_BACKFLOW_STATES = {"active", "not_active", "unknown", "likely"}


def compute_backflow_state(
    *,
    canal_level: Optional[Reading] = None,
    pond_level: Optional[Reading] = None,
    same_datum: bool = False,
    canal_above_own_critical: Optional[bool] = None,
    pond_below_own_bank: Optional[bool] = None,
    gate_open: Optional[bool] = None,
    community_evidence: Optional[list] = None,
) -> BackflowState:
    """Never a fabricated m3/s. Three cases, per founder instruction:

    1. community eyewitness of backflow itself (a person reporting water arriving "from the
       canal pipe") -- direct MEASURED-community evidence, state=active regardless of gate
       flag (a report of water already flowing IS the state).
    2. canal and pond level on the SAME datum -- state from the sign of (canal - pond), only
       "active" when that head is positive AND the connection is not confirmed closed.
    3. different datums, only band comparison available (canal above its own critical level
       while pond is below its own bank line) -- "likely", tagged INSTINCT, never a number.
    Otherwise: "unknown".
    """
    evidence = list(community_evidence or [])
    if evidence:
        return BackflowState(state="active", tag="MEASURED-community", evidence=evidence,
                              note="Direct community eyewitness report of canal water "
                                   "arriving via pipe/drain -- treated as observed state, "
                                   "not inferred.")

    if gate_open is False:
        return BackflowState(state="not_active", tag="MEASURED" if canal_level or pond_level
                              else "OPEN", note="Connection reported closed.")

    if same_datum and canal_level is not None and pond_level is not None:
        if canal_level.missing or pond_level.missing:
            return BackflowState(state="unknown", tag="OPEN",
                                  note="canal/pond level reading missing.")
        head = canal_level.value - pond_level.value
        tag = "MEASURED" if canal_level.tag == pond_level.tag == "MEASURED" else "RELAYED"
        state = "active" if head > 0 else "not_active"
        return BackflowState(state=state, tag=tag, head_m=head,
                              note="Head computed on a shared datum.")

    if canal_above_own_critical is not None and pond_below_own_bank is not None:
        if canal_above_own_critical and pond_below_own_bank:
            return BackflowState(state="likely", tag="INSTINCT",
                                  note="Canal above its own critical level while pond is "
                                       "below its own bank line -- a band comparison, not a "
                                       "shared-datum head; never converted to a fabricated "
                                       "m3/s.")
        return BackflowState(state="not_active", tag="INSTINCT",
                              note="Band comparison does not indicate backflow risk.")

    return BackflowState(state="unknown", tag="OPEN",
                          note="No community evidence, no shared-datum levels, no band "
                               "comparison available.")


# --------------------------------------------------------------------------- time-to-exceed

def time_to_exceed_hours(current_value: Optional[float], threshold: Optional[float],
                          rate_per_hour: Optional[float]) -> Optional[float]:
    """Reuses PROP-FLOOD-02's idea (linear extrapolation to a threshold), not a live
    implementation of that (still-OPEN, per AGENTS.md §8) proposal. Returns None (REFUSED)
    when any input is missing, the rate is non-positive (not rising), or the threshold is
    already exceeded (falling/already-crossed cases both REFUSE, matching PROP-FLOOD-02's
    own stated REFUSED conditions -- see docs/LAYER0_IN_OUT_CAPACITY.md §4)."""
    if current_value is None or threshold is None or rate_per_hour is None:
        return None
    if rate_per_hour <= 0:
        return None
    if current_value >= threshold:
        return 0.0
    hours = (threshold - current_value) / rate_per_hour
    if not math.isfinite(hours) or hours < 0:
        return None
    return hours


# --------------------------------------------------------------------------- coping_thresholds.yaml

def load_coping_thresholds(path: Optional[Path] = None) -> dict:
    """Reads sources/coping_thresholds.yaml's `derived` block (min/max/gap per unit x
    variable, already computed by hand in that file from the historical/research rows).
    Read-only, no network call. Returns {} (never raises) if the file or PyYAML is
    unavailable -- callers must treat an empty dict as OPEN/REFUSED for every band."""
    target = path or COPING_THRESHOLDS_PATH
    try:
        import yaml  # local import: keep this module importable even without PyYAML
    except ImportError:
        return {}
    try:
        with open(target, "r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
    except OSError:
        return {}
    return doc.get("derived", {}) or {}


def _band_reading(band: dict, key: str, unit_of_value: str) -> Reading:
    entry = (band or {}).get(key)
    if not entry or entry.get("value") is None:
        return refused(unit_of_value, f"{key} ไม่มีในประวัติ (coping_thresholds.yaml)")
    return Reading(value=float(entry["value"]), unit=unit_of_value, tag=entry.get("tag", "OPEN"),
                   source="sources/coping_thresholds.yaml", observed_at=entry.get("date"),
                   note=entry.get("basis", "") or entry.get("station", ""))


def capacity_band(unit_id: str, variable: str, unit_of_value: str,
                   thresholds: Optional[dict] = None) -> dict:
    """Returns {"flooded_min": Reading, "coped_max": Reading, "design": Reading|None,
    "gap": float|None, "one_sided": bool}. All missing sides come back REFUSED, never a
    guessed number."""
    thresholds = thresholds if thresholds is not None else load_coping_thresholds()
    band = (thresholds.get(unit_id, {}) or {}).get(variable, {}) or {}
    flooded_min = _band_reading(band, "threshold_flooded_min", unit_of_value)
    coped_max = _band_reading(band, "threshold_coped_max", unit_of_value)
    design = None
    if band.get("design") and band["design"].get("value") is not None:
        d = band["design"]
        design = Reading(value=float(d["value"]), unit=d.get("unit", unit_of_value),
                          tag=d.get("tag", "OPEN"), source="sources/coping_thresholds.yaml",
                          note=d.get("basis", ""))
    gap = band.get("gap")
    return {
        "flooded_min": flooded_min,
        "coped_max": coped_max,
        "design": design,
        "gap": gap,
        "one_sided": bool(band.get("one_sided", flooded_min.missing or coped_max.missing)),
    }


def _read_capacity_ledger_current(ledger_id: str, field_name: str = "current_value_this_week"
                                   ) -> Optional[Reading]:
    """Best-effort read of an already-collected current value from
    sources/capacity_ledger.yaml (no new network request -- this file is written by another
    collector). Returns None (caller must REFUSE) if the row/field is absent."""
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(CAPACITY_LEDGER_PATH, "r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
    except OSError:
        return None
    for row in doc.get("rows", []) or []:
        if row.get("id") == ledger_id:
            val = row.get(field_name)
            if val is None:
                return None
            if isinstance(val, dict):
                # dam rows: {"inflow_m3s": .., "release_m3s": ..} -- caller picks a sub-key
                return None
            return Reading(value=float(val), unit="m3s", tag=row.get("tag", "OPEN"),
                           source="sources/capacity_ledger.yaml", observed_at=row.get("observed_at"))
    return None


# --------------------------------------------------------------------------- readout record

@dataclass
class Layer0Readout:
    unit_id: str
    label: str
    IN: dict  # name -> Reading | BackflowState
    OUT: dict  # name -> Reading
    CAPACITY: dict  # {"design": Reading|None, "flooded_min": Reading, "coped_max": Reading, "gap": float|None}
    in_vs_capacity: str
    out_vs_in: str
    time_to_exceed_h: Optional[float]
    sentence: str


def _in_vs_capacity(primary_in: Optional[Reading], capacity: dict) -> str:
    """Band logic (founder-specified, 2026-10-03; no new thresholds -- uses only the
    shipped flooded_min/coped_max band for the unit):

    - value >= flooded_min            -> "เกิน" (exceeded -- this alone is decidable even
                                          if coped_max is missing, since flooded_min is an
                                          observed upper bound on its own).
    - value <= coped_max              -> "ไม่เกิน" (not exceeded), with an optional "ใกล้"
                                          sub-band for 0.8*coped_max <= value <= coped_max.
    - coped_max < value < flooded_min -> "ไม่รู้ (อยู่ระหว่างเคยรับได้กับเคยท่วม)" -- a real,
                                          named band of ignorance between the two historical
                                          bounds (UNKNOWN != SAFE: never defaulted to
                                          "ไม่เกิน" just because flooded_min isn't reached).
    - either bound missing (and value doesn't already clear flooded_min from above)
                                       -> "ไม่รู้ (ขาด: ความสามารถรับมือ)".
    """
    if primary_in is None or primary_in.missing:
        return "ไม่รู้ (ขาด: น้ำเข้า)"
    value = primary_in.value
    flooded_min = capacity.get("flooded_min")
    coped_max = capacity.get("coped_max")

    if flooded_min is not None and not flooded_min.missing and value >= flooded_min.value:
        return "เกิน"

    if coped_max is None or coped_max.missing:
        return "ไม่รู้ (ขาด: ความสามารถรับมือ)"

    if value <= coped_max.value:
        if coped_max.value and value >= NEAR_THRESHOLD_FRACTION * coped_max.value:
            return "ใกล้ (>=80%)"
        return "ไม่เกิน"

    if flooded_min is None or flooded_min.missing:
        return "ไม่รู้ (ขาด: ความสามารถรับมือ)"

    return "ไม่รู้ (อยู่ระหว่างเคยรับได้กับเคยท่วม)"


def _out_vs_in(primary_out: Optional[Reading], primary_in: Optional[Reading]) -> str:
    if primary_out is None or primary_out.missing or primary_in is None or primary_in.missing:
        return "ไม่รู้"
    if primary_out.value >= primary_in.value:
        return "ระบายทัน"
    return "ไม่ทัน"


def render_unit(
    unit_id: str,
    label: str,
    in_components: dict,
    out_components: dict,
    capacity: dict,
    *,
    primary_in: Optional[Reading] = None,
    primary_out: Optional[Reading] = None,
    rate_per_hour: Optional[float] = None,
) -> Layer0Readout:
    """Assembles the one-sentence LAYER 0 readout. Renders with whatever exists -- a missing
    number shows as "ขาด: <what>" in-line, the sentence itself never fails to render
    (founder: "the sentence must still render with whatever exists")."""
    in_vs_cap = _in_vs_capacity(primary_in, capacity)
    out_vs_in = _out_vs_in(primary_out, primary_in)

    threshold_for_time = capacity.get("flooded_min") or capacity.get("design")
    t_exceed = None
    if (primary_in is not None and not primary_in.missing and threshold_for_time is not None
            and not threshold_for_time.missing):
        t_exceed = time_to_exceed_hours(primary_in.value, threshold_for_time.value, rate_per_hour)

    in_parts = []
    for name, comp in in_components.items():
        if isinstance(comp, BackflowState):
            in_parts.append(comp.render())
        else:
            in_parts.append(f"{name}: {comp.render()}")
    out_parts = [f"{name}: {comp.render()}" for name, comp in out_components.items()]

    cap_parts = []
    if capacity.get("design") is not None:
        cap_parts.append(f"ออกแบบ {capacity['design'].render()}")
    cap_parts.append(f"เคยท่วมที่ {capacity['flooded_min'].render()}"
                      if not capacity["flooded_min"].missing
                      else f"เคยท่วมที่ {capacity['flooded_min'].render()}")
    cap_parts.append(f"เคยรับได้ถึง {capacity['coped_max'].render()}"
                      if not capacity["coped_max"].missing
                      else f"เคยรับได้ถึง {capacity['coped_max'].render()}")
    if capacity.get("gap") is not None:
        cap_parts.append(f"ช่วงไม่รู้ {capacity['gap']:.1f}")
    elif capacity.get("one_sided"):
        cap_parts.append("ช่วงไม่รู้: ด้านเดียว (one_sided)")

    time_txt = (f"อีก ~{t_exceed:.1f} ชม. ถึงเกิน" if t_exceed and t_exceed > 0
                else ("เกินแล้ว" if t_exceed == 0 else "ไม่รู้เวลาที่จะเกิน"))

    sentence = (
        f"[{label}] น้ำเข้า: {'; '.join(in_parts) if in_parts else 'ขาด: น้ำเข้า'} · "
        f"น้ำออก: {'; '.join(out_parts) if out_parts else 'ขาด: น้ำออก'} · "
        f"รับมือได้: {'; '.join(cap_parts)} · "
        f"IN vs CAPACITY: {in_vs_cap} · OUT vs IN: {out_vs_in} · {time_txt}"
    )

    return Layer0Readout(
        unit_id=unit_id, label=label, IN=in_components, OUT=out_components, CAPACITY=capacity,
        in_vs_capacity=in_vs_cap, out_vs_in=out_vs_in, time_to_exceed_h=t_exceed, sentence=sentence,
    )


# --------------------------------------------------------------------------- live-unit builders
# These are NOT wired into site/build_data.py (out of this check's write scope; another worker
# is the sole committer for this branch). Called with no `live` dict, every IN/OUT component
# that needs a live pull REFUSES honestly; CAPACITY is filled from the historical record
# (sources/coping_thresholds.yaml), which does not need a live pull.

def build_bangkok_east(live: Optional[dict] = None) -> Layer0Readout:
    live = live or {}
    thresholds = load_coping_thresholds()
    cap = capacity_band("bangkok_east", "rain_24h_mm", "mm/24h", thresholds)

    rain_fc = live.get("rain_forecast_24h_median") or refused(
        "mm/24h", "rain_forecast_24h_median (ensemble, ยังไม่ได้ wire จาก build_data.py)")
    rain_obs = live.get("rain_observed_24h") or refused(
        "mm/24h", "rain_observed_24h (thaiwater_rain_24h, ยังไม่ได้ wire)")
    upstream = live.get("upstream_inflow") or Reading(
        value=0.0, unit="mm/24h", tag="INSTINCT", source="no gate reported open with dH>0",
        note="BKK east: 0 unless a named gate is confirmed open with head>0.")

    pumping = live.get("pumping_running") or Reading(
        value=1200.0, unit="m3/s", tag="RELAYED",
        source="docs/knowledge/CHAO_PHRAYA_CAPACITY_AND_DISCHARGE.md §3 (mgronline.com, 2026-09-25 20:12)",
        observed_at="2026-09-25T20:12+07:00",
        note="กำลังสูบรวมฝั่งพระนคร เต็มกำลัง -- scope: ฝั่งพระนคร only, not the whole city.")
    gravity = live.get("gravity_headroom") or refused("m3/s", "gravity_headroom (reach capacity - current flow, ยังไม่ได้ wire)")

    in_components = {"ฝนพยากรณ์24ชม.": rain_fc, "ฝนวัดจริง24ชม.": rain_obs, "น้ำต้นทาง": upstream}
    out_components = {"ปั๊มที่วิ่งอยู่": pumping, "ทางออกแรงโน้มถ่วง": gravity}
    primary_in = rain_obs if not rain_obs.missing else rain_fc
    return render_unit("bangkok_east", "กทม. ฝั่งตะวันออก", in_components, out_components, cap,
                        primary_in=primary_in, primary_out=pumping)


def build_sammakorn(live: Optional[dict] = None) -> Layer0Readout:
    live = live or {}
    thresholds = load_coping_thresholds()
    cap = capacity_band("sammakorn", "rain_24h_mm", "mm/24h", thresholds)

    rain_obs = live.get("rain_observed_24h") or Reading(
        value=196.6, unit="mm/24h", tag="RELAYED",
        source="site/inputs/community/community_reports_2026-09-26.md §E.4",
        observed_at="2026-09-26", note="สถานีบางกะปิ ใกล้ที่สุดในข้อมูลชุมชน, ไม่ใช่สถานีในหมู่บ้านเอง.")

    backflow = live.get("backflow_state") or compute_backflow_state(
        community_evidence=[
            "ซอย 59: \"ขึ้นโรงรถ/หลังบ้าน จากท่อน้ำคลอง\" 06:00-10:00 (26 ก.ย. 2569)",
            "ซอย 17: \"เข้าโรงรถ + ย้อนขึ้นท่อ/ห้องน้ำชั้นล่าง\" 11:10 (26 ก.ย. 2569)",
        ])

    # 4 pumps, all reporting "ขัดข้อง" (fault) per this repo's own MEASURED sensor read --
    # see docs/SAMMAKORN_STANDING_WATER_2026-09-27.md. The founder's instructions mentioned
    # "0/11 pumps"; this repo's own knowledge base records 4 private pumps (ST.SPS.01-04),
    # not 11 -- kept as an OPEN discrepancy, never silently overwritten to match that
    # recollection.
    pumping = live.get("pumping_running") or Reading(
        value=0.0, unit="m3/s", tag="MEASURED",
        source="docs/SAMMAKORN_STANDING_WATER_2026-09-27.md (ST.SPS.01-04, ทั้งหมด 'ขัดข้อง')",
        observed_at="2026-09-27",
        note="0/4 ปั๊มส่วนตัวหมู่บ้านทำงาน (ไม่ใช่ 0/11 ตามที่โจทย์อ้างถึง -- ความต่างนี้ยังเปิดอยู่, "
             "OPEN, ไม่ได้แก้ให้ตรงกับโจทย์โดยไม่มีหลักฐาน).")
    gravity = live.get("gravity_headroom") or refused(
        "m3/s", "gravity_headroom -- 'มีเส้นทางแรงโน้มถ่วงสำรองไหม' ยังเป็น OPEN ตาม "
                "docs/SAMMAKORN_STANDING_WATER_2026-09-27.md")

    in_components = {"ฝนวัดจริง24ชม.": rain_obs, "ย้อนจากคลอง": backflow}
    out_components = {"ปั๊ม (0/4)": pumping, "ไหลเองเมื่อบึงสูงกว่าคลอง": gravity}
    return render_unit("sammakorn", "สัมมากร", in_components, out_components, cap,
                        primary_in=rain_obs, primary_out=pumping)


def build_ram53(live: Optional[dict] = None) -> Layer0Readout:
    live = live or {}
    thresholds = load_coping_thresholds()
    # ram53 shares the bangkok_east rain-capacity band -- no unit-specific historical rows
    # exist yet for this exact unit, so the band is explicitly borrowed and flagged.
    cap = capacity_band("bangkok_east", "rain_24h_mm", "mm/24h", thresholds)
    cap = dict(cap)
    cap["design"] = cap.get("design")

    rain_obs = live.get("rain_observed_24h") or refused(
        "mm/24h", "rain_observed_24h ยังไม่ได้ wire สำหรับราม 53 โดยเฉพาะ (ใช้ค่าโซนตะวันออกแทนได้ในอนาคต)")
    pumping = live.get("pumping_running") or refused("m3/s", "pumping_running ยังไม่ได้ wire")
    gravity = live.get("gravity_headroom") or refused("m3/s", "gravity_headroom ยังไม่ได้ wire")
    upstream = live.get("upstream_inflow") or Reading(
        value=0.0, unit="mm/24h", tag="INSTINCT", source="no gate reported open with dH>0")

    in_components = {"ฝนวัดจริง24ชม.": rain_obs, "น้ำต้นทาง": upstream}
    out_components = {"ปั๊มที่วิ่งอยู่": pumping, "ทางออกแรงโน้มถ่วง": gravity}
    readout = render_unit("ram53", "รามคำแหง 53", in_components, out_components, cap,
                           primary_in=rain_obs, primary_out=pumping)
    readout.CAPACITY = dict(readout.CAPACITY)
    readout.sentence += " (หมายเหตุ: ยืมแถบ CAPACITY จาก bangkok_east -- ยังไม่มีประวัติเฉพาะราม 53)"
    return readout


def build_chao_phraya_bkk_reach(live: Optional[dict] = None) -> Layer0Readout:
    live = live or {}
    thresholds = load_coping_thresholds()
    cap = capacity_band("chao_phraya_bkk_reach", "river_flow_m3s", "m3/s", thresholds)

    current = live.get("river_flow_now") or _read_capacity_ledger_current("AS_DAM_C13") or Reading(
        value=1750.0, unit="m3/s", tag="RELAYED",
        source="docs/knowledge/CHAO_PHRAYA_CAPACITY_AND_DISCHARGE.md §3 (igreenstory.co/flood-15)",
        observed_at="2026-09-27")
    upstream = live.get("upstream_inflow_c2") or refused(
        "m3/s", "C.2 flow now vs travel-time tau -- ยังไม่ได้ wire tau_up (OPEN ตาม PROP-FLOOD-06 v5)")
    pumping = refused("m3/s", "river reach: ไม่มีปั๊ม, ใช้เฉพาะ gravity headroom")
    gravity = live.get("gravity_headroom") or Reading(
        value=(cap["flooded_min"].value - current.value) if not cap["flooded_min"].missing else None,
        unit="m3/s", tag="PROPOSAL-derived",
        source="threshold_flooded_min - current (arithmetic, not a registered equation)"
    ) if not cap["flooded_min"].missing else refused("m3/s", "flooded_min missing, ไม่คำนวณ headroom")

    in_components = {"C.13 ปัจจุบัน": current, "น้ำต้นทาง (C.2, tau ชม.)": upstream}
    out_components = {"ปั๊ม": pumping, "ช่องว่างก่อนล้นตลิ่ง": gravity}
    return render_unit("chao_phraya_bkk_reach", "แม่น้ำเจ้าพระยา ช่วงผ่าน กทม. (C.13)",
                        in_components, out_components, cap, primary_in=current, primary_out=None)


def build_historical_unit(unit_id: str, label: str, variable: str, unit_of_value: str,
                           demonstration_note: str = "ข้อมูลย้อนหลัง (backtest archive), "
                                                       "ไม่ใช่ live") -> Layer0Readout:
    """nan_town / chiangmai_town / hatyai -- historical demonstration units built purely from
    raw/backtest archives + docs/knowledge case cards, flagged not-live throughout."""
    thresholds = load_coping_thresholds()
    cap = capacity_band(unit_id, variable, unit_of_value, thresholds)
    flagged_note = f"[{demonstration_note}] "

    in_reading = refused(unit_of_value, f"{demonstration_note}: no current live reading, "
                                         f"historical band only")
    out_reading = refused("m3/s", f"{demonstration_note}: no live pump/gate data for this unit")
    in_components = {"น้ำเข้า (ไม่ live)": in_reading}
    out_components = {"น้ำออก (ไม่ live)": out_reading}
    readout = render_unit(unit_id, label, in_components, out_components, cap,
                           primary_in=None, primary_out=None)
    readout.sentence = flagged_note + readout.sentence
    return readout
