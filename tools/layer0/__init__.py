"""LAYER 0 -- the three-number readout (IN / OUT / CAPACITY) per unit.

Founder instruction (verbatim, 2026-09-27): "จริงๆ การพยากรณ์เบื้องต้นไม่ซับซ้อน ... กทม. มี
ความสามารถรับฝนที่ xxx แต่วันนี้ฝนจะตกในพื้นที่ xxx+1 หรือกำลังมีน้ำที่มาจากต้นทางที่ xxx+1 ในกี่ชั่วโมง
... แล้วค่อยไปลงรายละเอียด" -> "เอาแบบง่ายๆ ก่อน น้ำเข้า น้ำออก ความสามารถในการรับมือ".

This package is a PROPOSAL-derived simplification of PROP-FLOOD-06's own F_H / C_H / R_H
(see toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md), not a new Toledo equation: it is a
3-number restatement (IN=F_H, OUT=D_H+R_H, CAPACITY=threshold proxy) for a first-glance
readout, before PROP-FLOOD-06's own fuller tier machinery. See docs/LAYER0_IN_OUT_CAPACITY.md.
"""

from .in_out_capacity import (  # noqa: F401
    Reading,
    BackflowState,
    Layer0Readout,
    refused,
    compute_backflow_state,
    time_to_exceed_hours,
    load_coping_thresholds,
    capacity_band,
    render_unit,
    build_bangkok_east,
    build_sammakorn,
    build_ram53,
    build_chao_phraya_bkk_reach,
    build_historical_unit,
)
