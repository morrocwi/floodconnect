#!/usr/bin/env python3
"""
tools/flowmap/render_profile.py -- longitudinal SVG profile renderer for a
`flow_stall.compute_chain()` result: x = position along a declared chain order,
y = elevation (m MSL). Terrain (ground/bed/bank/control) drawn as steps -- solid where
the source is known, dashed where a node's terrain attribute is `OPEN`. Water surfaces
drawn as blue segments at their latest reading + timestamp. Edges drawn as arrows
coloured by direction; REFUSED edges drawn as a grey "?" with the reason; INFERRED
edges/nodes drawn hatched/dotted (never the same look as a directly measured value),
labelled with the rule id and anchors used. Pumps/gates drawn as small icons with their
measured state text. Page blocks (A)-(D) folded in from the external typology proposal
(landscape-type sentence, main-chain edge labels, head ledger, flow-state readout) are
rendered as text blocks above/below the profile.

Colour tokens are literal hex values matching `site/index.template.html`'s light-theme
CSS custom properties (`--ok`, `--warning-text`, `--alert`, `--accent`, `--accent-2`,
`--border`, `--bg`, `--surface`, `--text`) -- this is a standalone prototype SVG (not yet
wired into the built page's own CSS cascade), so each colour is annotated with the site
variable it must be swapped for once this renderer is wired into `site/build_page.py`
(see docs/FLOW_STALL_TYPOLOGY.md "wiring steps").

Text is always >=12px (`font-size` in the SVG's user units, which this renderer keeps at
1 unit = 1 px). All labels are Thai per this repo's public-page convention.
"""
from __future__ import annotations

import html
from fractions import Fraction
from typing import Optional

from .flow_stall import (
    TREND_MOVING_UP, TREND_MOVING_DOWN, TREND_STALLED, TREND_UNKNOWN,
    EDGE_STATUS_OK, EDGE_STATUS_CONTROLLED, EDGE_STATUS_REFUSED, EDGE_STATUS_INFERRED,
    STATUS_OK,
)

# Site tokens (light theme), literal hex -- see docstring above for the swap-in mapping.
C_BG = "#F5F7F8"           # var(--bg)
C_SURFACE = "#FFFFFF"      # var(--surface)
C_TEXT = "#12232B"         # var(--text) (approx, see index.template.html)
C_BORDER = "#CBD8DC"       # var(--border)
C_ACCENT = "#0B3C5D"       # var(--accent)
C_ACCENT2 = "#1F7A8C"      # var(--accent-2) -- used for water surfaces
C_OK = "#2E7D32"           # var(--ok) -- FORWARD / MOVING_UP direction
C_WARNING = "#945F0B"      # var(--warning-text) -- REVERSE / MOVING_DOWN direction
C_ALERT = "#C0392B"        # var(--alert) -- CONTROLLED / locked
C_GREY = "#7C8C93"         # not a site token -- REFUSED "?" grey, deliberately muted
C_GROUND = "#8A6D3B"       # not a site token -- terrain ground/bed brown

FONT = "font-family:'Noto Sans Thai','Noto Sans',sans-serif;"


def _esc(s: Optional[str]) -> str:
    return html.escape(str(s)) if s is not None else ""


def _elev(attr) -> Optional[float]:
    if attr is None or attr.value is None:
        return None
    try:
        return float(Fraction(str(attr.value)))
    except (ValueError, ZeroDivisionError):
        return None


def _direction_color(direction: Optional[str]) -> str:
    if direction in (TREND_MOVING_UP, "FORWARD"):
        return C_OK
    if direction in (TREND_MOVING_DOWN, "REVERSE"):
        return C_WARNING
    if direction == TREND_STALLED:
        return C_GREY
    return C_ACCENT2  # UNRESOLVED / unknown-but-moving-adjacent


def render_profile_svg(nodes: dict, edges: list, chain_order: list, chain_result,
                        title_th: str, landscape_label: Optional[dict] = None,
                        head_ledger: Optional[list] = None,
                        width: int = 1300, height: int = 640) -> str:
    """`nodes`: dict[node_id, Node]. `edges`: list[Edge]. `chain_order`: list[node_id] in
    left-to-right draw order (a single branch at a time -- call once per branch and
    concatenate the <svg> blocks, or nest as separate <g> if composing multiple branches
    into one figure; this prototype renders one branch per call). `chain_result`: the
    `ChainResult` from `compute_chain()`. `head_ledger`: optional list of dicts
    {"label_th", "edge_id"} for page-block (C) (folded in from the external proposal's
    "two heads" convention -- shown as a ledger of specific edges' delta_m/freshness,
    never a new formula)."""
    margin_l, margin_r, margin_t, margin_b = 70, 40, 150, 170
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    n = max(len(chain_order) - 1, 1)
    x_for = {nid: margin_l + i * (plot_w / n) for i, nid in enumerate(chain_order)}

    edge_by_pair = {}
    for e in edges:
        edge_by_pair[(e.u, e.v)] = e
        edge_by_pair[(e.v, e.u)] = e

    # elevation range across every known terrain attr + reading, so the profile always
    # has a sane y-scale even when almost everything is OPEN.
    elevs = []
    for nid in chain_order:
        node = nodes.get(nid)
        if node is None:
            continue
        for attr in (node.ground_m_msl, node.bed_m_msl, node.bank_m_msl, node.control_m_msl):
            v = _elev(attr)
            if v is not None:
                elevs.append(v)
        for r in node.valid_readings()[:1]:
            try:
                elevs.append(float(Fraction(str(r.value))))
            except (ValueError, ZeroDivisionError):
                pass
    if not elevs:
        elevs = [-1.0, 1.0]
    y_min, y_max = min(elevs) - 0.3, max(elevs) + 0.3
    if y_max - y_min < 0.5:
        y_min -= 0.25
        y_max += 0.25

    def y_for(v: float) -> float:
        return margin_t + plot_h * (1 - (v - y_min) / (y_max - y_min))

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'aria-label="{_esc(title_th)}">'
    )
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{C_BG}"/>')
    parts.append(
        f'<style>text{{{FONT}}} .lbl{{font-size:13px;fill:{C_TEXT};}} '
        f'.lbl-sm{{font-size:12px;fill:{C_TEXT};}} '
        f'.lbl-muted{{font-size:12px;fill:{C_GREY};}} '
        f'.title{{font-size:18px;font-weight:700;fill:{C_ACCENT};}} '
        f'.block-h{{font-size:14px;font-weight:700;fill:{C_ACCENT};}}</style>'
    )
    parts.append(f'<text x="{margin_l}" y="30" class="title">{_esc(title_th)}</text>')

    # ---- Page block (A): landscape-type sentence (always tagged INFERRED + anchors) ----
    if landscape_label:
        t = landscape_label["type"]
        anchors_txt = ", ".join(landscape_label["anchors"]) or "ไม่มี"
        parts.append(f'<text x="{margin_l}" y="52" class="block-h">(A) ภูมิทัศน์ (INFERRED):</text>')
        parts.append(
            f'<text x="{margin_l}" y="72" class="lbl-sm">ประเภท {landscape_label["type_id"]} — '
            f'{_esc(t["name_th"])} · อนุมานจากจุดยึด: {_esc(anchors_txt)}</text>'
        )
        parts.append(f'<text x="{margin_l}" y="90" class="lbl-muted">สัญญาณที่ใช้: {_esc(t["signals"])}</text>')

    # ---- axis ----
    for gv in _grid_values(y_min, y_max):
        y = y_for(gv)
        parts.append(f'<line x1="{margin_l}" y1="{y:.1f}" x2="{width - margin_r}" y2="{y:.1f}" '
                      f'stroke="{C_BORDER}" stroke-width="1" stroke-dasharray="2,3"/>')
        parts.append(f'<text x="{margin_l - 8}" y="{y + 4:.1f}" text-anchor="end" '
                      f'class="lbl-sm">{gv:+.1f}</text>')
    parts.append(f'<text x="20" y="{margin_t - 10}" class="lbl-sm">ม. MSL</text>')

    # ---- terrain steps + water surfaces + node labels ----
    for nid in chain_order:
        node = nodes.get(nid)
        if node is None:
            continue
        x = x_for[nid]
        nt = chain_result.node_trends.get(nid)
        for attr, colour, label in (
            (node.ground_m_msl, C_GROUND, "พื้นดิน"),
            (node.bed_m_msl, C_GROUND, "ท้องคลอง"),
            (node.bank_m_msl, C_ACCENT, "สันคลอง"),
            (node.control_m_msl, "#6A4C93", "ระดับควบคุม"),
        ):
            v = _elev(attr)
            if v is None:
                continue
            y = y_for(v)
            dash = '' if attr.tag not in ("OPEN",) else 'stroke-dasharray="4,3"'
            parts.append(f'<line x1="{x-16:.1f}" y1="{y:.1f}" x2="{x+16:.1f}" y2="{y:.1f}" '
                         f'stroke="{colour}" stroke-width="3" {dash}/>')
        # water surface
        if nt and nt.status == STATUS_OK and nt.cur_reading is not None:
            try:
                v = float(Fraction(str(nt.cur_reading.value)))
            except (ValueError, ZeroDivisionError):
                v = None
            if v is not None:
                y = y_for(v)
                dash = '' if not nt.inferred else 'stroke-dasharray="1,3"'
                parts.append(f'<line x1="{x-20:.1f}" y1="{y:.1f}" x2="{x+20:.1f}" y2="{y:.1f}" '
                             f'stroke="{C_ACCENT2}" stroke-width="5" {dash} '
                             f'stroke-linecap="round" opacity="0.85"/>')
                ts = nt.cur_reading.observed_at or ""
                tlabel = f'{v:+.2f} ม. @ {ts[11:16]}' if ts else f'{v:+.2f} ม.'
                if nt.inferred:
                    tlabel = "อนุมาน: " + tlabel + f" ({nt.rule_id})"
                parts.append(f'<text x="{x:.1f}" y="{y - 10:.1f}" text-anchor="middle" '
                             f'class="lbl-sm">{_esc(tlabel)}</text>')
        elif nt is None or nt.status != STATUS_OK:
            # REFUSED / no readout at all -- grey "?" placeholder, never a fabricated level
            y_q = y_for((y_min + y_max) / 2)
            reason = ", ".join(nt.reason_codes) if nt and nt.reason_codes else "ไม่มีข้อมูล"
            parts.append(f'<circle cx="{x:.1f}" cy="{y_q:.1f}" r="12" fill="none" '
                         f'stroke="{C_GREY}" stroke-width="2" stroke-dasharray="3,2"/>')
            parts.append(f'<text x="{x:.1f}" y="{y_q + 5:.1f}" text-anchor="middle" '
                         f'class="lbl" fill="{C_GREY}">?</text>')
            parts.append(f'<title>{_esc(reason)}</title>')
        # icon for gate/pump
        icon_y = height - margin_b + 20
        if node.kind == "gate":
            parts.append(f'<polygon points="{x-8:.1f},{icon_y-8:.1f} {x+8:.1f},{icon_y-8:.1f} '
                         f'{x:.1f},{icon_y+8:.1f}" fill="{C_ALERT}" opacity="0.85"/>')
            state = "วัดเปิด/ปิดจริง: " + (f'{node.control_m_msl.value} ม.' if node.control_m_msl.value is not None else "OPEN")
        elif node.kind == "pump":
            parts.append(f'<circle cx="{x:.1f}" cy="{icon_y:.1f}" r="9" fill="{C_ACCENT}" opacity="0.85"/>')
            state = ""
        else:
            state = ""
        # node label
        parts.append(f'<text x="{x:.1f}" y="{icon_y + 42:.1f}" text-anchor="middle" '
                     f'class="lbl-sm">{_esc(node.name_th)}</text>')
        if state:
            parts.append(f'<text x="{x:.1f}" y="{icon_y + 58:.1f}" text-anchor="middle" '
                         f'class="lbl-muted">{_esc(state)}</text>')

    # ---- page block (B): edges as arrows with labels ----
    parts.append(f'<text x="{margin_l}" y="{height - margin_b + 90}" class="block-h">'
                 f'(B) เส้นเชื่อมหลัก:</text>')
    ey = height - margin_b + 108
    for i in range(len(chain_order) - 1):
        u, v = chain_order[i], chain_order[i + 1]
        e = edge_by_pair.get((u, v))
        if e is None:
            continue
        ef = chain_result.edge_flows.get(e.edge_id)
        x1, x2 = x_for[u], x_for[v]
        mid = (x1 + x2) / 2
        y_line = y_for((y_min + y_max) / 2)
        if ef is None:
            continue
        if ef.status in (EDGE_STATUS_OK,):
            colour = _direction_color(ef.direction)
            parts.append(f'<line x1="{x1+22:.1f}" y1="{y_line:.1f}" x2="{x2-22:.1f}" y2="{y_line:.1f}" '
                         f'stroke="{colour}" stroke-width="3" marker-end="url(#arrF)"/>')
            label = f"{e.edge_id}: {ef.direction} (ΔH={float(ef.delta_m):+.2f} ม.)" if ef.delta_m is not None else f"{e.edge_id}: {ef.direction}"
        elif ef.status == EDGE_STATUS_CONTROLLED:
            parts.append(f'<line x1="{x1+22:.1f}" y1="{y_line:.1f}" x2="{x2-22:.1f}" y2="{y_line:.1f}" '
                         f'stroke="{C_ALERT}" stroke-width="3" stroke-dasharray="6,3"/>')
            label = f"{e.edge_id}: CONTROLLED (ล็อกที่ {ef.locked_node})"
        elif ef.status == EDGE_STATUS_INFERRED:
            colour = _direction_color(ef.direction)
            parts.append(f'<line x1="{x1+22:.1f}" y1="{y_line:.1f}" x2="{x2-22:.1f}" y2="{y_line:.1f}" '
                         f'stroke="{colour}" stroke-width="3" stroke-dasharray="2,4" '
                         f'marker-end="url(#arrF)" opacity="0.8"/>')
            label = (f"{e.edge_id}: อนุมาน {ef.direction} [{ef.rule_id}] "
                     f"ยึด: {', '.join(ef.anchors)} (ความมั่นใจ={ef.confidence})")
        else:
            parts.append(f'<line x1="{x1+22:.1f}" y1="{y_line:.1f}" x2="{x2-22:.1f}" y2="{y_line:.1f}" '
                         f'stroke="{C_GREY}" stroke-width="2" stroke-dasharray="1,3"/>')
            reason = ", ".join(ef.reason_codes) if ef.reason_codes else "?"
            label = f"{e.edge_id}: REFUSED ({reason})"
        parts.append(f'<text x="{mid:.1f}" y="{ey:.1f}" text-anchor="middle" '
                     f'class="lbl-muted">{_esc(label)}</text>')
        ey += 15
        if ey > height - 20:
            ey = height - margin_b + 108  # wrap column (prototype-simple: overlap accepted)

    parts.append(
        '<defs><marker id="arrF" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" '
        f'markerHeight="6" orient="auto-start-reverse"><path d="M0,0L8,4L0,8Z" fill="{C_OK}"/>'
        '</marker></defs>'
    )

    # ---- page block (C): head ledger ----
    if head_ledger:
        hy = 108
        parts.append(f'<text x="{width - margin_r - 380}" y="{hy - 18}" class="block-h">'
                     f'(C) หัวน้ำ (head ledger):</text>')
        for item in head_ledger:
            ef = chain_result.edge_flows.get(item["edge_id"])
            if ef is None:
                continue
            fresh = "REFUSED" if ef.status == EDGE_STATUS_REFUSED else (
                "อนุมาน" if ef.inferred else "วัดจริง")
            delta_txt = f"{float(ef.delta_m):+.2f} ม." if ef.delta_m is not None else "-"
            parts.append(f'<text x="{width - margin_r - 380}" y="{hy}" class="lbl-sm">'
                         f'{_esc(item["label_th"])}: {delta_txt} [{fresh}]</text>')
            hy += 16

    # ---- page block (D): current flow-state readout (NOT the F1-F6 classifier -- see
    # docs/FLOW_STALL_TYPOLOGY.md appendix; PROP-FLOOD-07 candidate, unregistered) ----
    parts.append(f'<text x="{margin_l}" y="{height - 40}" class="block-h">'
                 f'(D) สถานะการไหลปัจจุบัน (readout, ไม่ใช่ตัวจัดชั้น F1-F6 — '
                 f'ดูภาคผนวก PROP-FLOOD-07 ที่ยังไม่ขึ้นทะเบียน):</text>')
    parts.append(f'<text x="{margin_l}" y="{height - 22}" class="lbl-sm">'
                 f'วัดจริง={chain_result.ok_count} · อนุมาน={chain_result.inferred_count} · '
                 f'REFUSED={chain_result.refused_count}</text>')

    # ---- legend ----
    parts.append(f'<text x="{width - margin_r - 260}" y="{height - 8}" text-anchor="start" '
                 f'class="lbl-sm" font-weight="700">ประตู ≠ ทิศทาง ≠ นิ่ง</text>')

    parts.append('</svg>')
    return "\n".join(parts)


def _grid_values(y_min: float, y_max: float, step: float = 0.5):
    v = round(y_min * 2) / 2
    out = []
    while v <= y_max:
        out.append(v)
        v += step
    return out
