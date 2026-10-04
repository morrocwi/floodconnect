# Mae Klong chain — NEXT VERSION (not MVP)

**Tag**: mixed, tagged per row · **บันทึกเข้า**: 2569-09-27 · **Scope**: ไฟล์ใหม่ 1 ไฟล์ (สำหรับ
Mae Klong ecosystem, 27 ก.ย. 2569) — ไม่แก้ไฟล์ที่ track อยู่ ไม่ commit ไม่ build ไม่ collect

**MVP rule (per `docs/MVP_SCOPE_2026-09-27.md`)**: forecasts this repo runs and publishes are
measured/scoped to **Sammakorn + Bangkok only**. Mae Klong (Kanchanaburi/Ratchaburi/Samut Songkhram)
is **NEXT VERSION** — this document encodes the chain structure, what already exists in this
repo's own KG/DB, and what is missing. **No run, no forecast number, no page claim** comes out of
this document.

---

## 1. The chain (declared, RELAYED — general river-network knowledge, not this check's own survey)

```
ศรีนครินทร์ (EGAT, แควใหญ่ / Khwae Yai)  ─┐
                                          ├─> บรรจบที่กาญจนบุรี (confluence) ─> เขื่อนแม่กลอง (ท่าม่วง)
วชิราลงกรณ (EGAT, แควน้อย / Khwae Noi)  ─┘         │  operated by: RID (irrigation diversion) /
                                                    │  EGAT (12 MW mini-hydro on the same structure)
                                                    ▼
                                              ท่าม่วง (อ.ท่าม่วง, กาญจนบุรี)
                                                    ▼
                                              บ้านโป่ง (อ.บ้านโป่ง, ราชบุรี)
                                                    ▼
                                              โพธาราม (อ.โพธาราม, ราชบุรี)
                                                    ▼
                                              ราชบุรี (อ.เมือง, ราชบุรี)
                                                    ▼
                                   ดำเนินสะดวก / บางคนที (ราชบุรี / สมุทรสงคราม)
                                                    ▼
                                              อัมพวา (สมุทรสงคราม)
                                                    ▼
                                    ปากแม่น้ำแม่กลอง (อ่าวไทย, สมุทรสงคราม) ── tide boundary
```

Order is RELAYED (general geography — Mae Klong River flows Kanchanaburi → Ratchaburi →
Samut Songkhram to the Gulf of Thailand at Amphawa/Mae Klong mouth); NOT independently re-verified
against a survey map this check. Matches the exact town order named in the founder's own hashtags
(#กาญจนบุรี #ราชบุรี #ท่าม่วง #บ้านโป่ง #โพธาราม), which are already in dam-to-mouth order.

---

## 2. What already exists in this repo's KG / DB (VERIFIED — grepped this check, counts below)

Checked against `output/thailand_water_kg.jsonld` (25,883 nodes, 56,603 edges, built 2026-09-27
18:19, read-only this check — not rebuilt) and `data/observations.sqlite`. Method: exact-string
grep for each place/dam name across all node payloads.

| Chain element | Node(s) held | Node kind | tag |
|---|---|---|---|
| ศรีนครินทร์ (dam) | `node:dam:hii_dam:14`, `node:dam:hii_dam:54`, `node:dam:rid_res_table:ศรีนครินทร์` (3 records, same dam, different source feeds — no dedup performed) | dam | VERIFIED (held) |
| ศรีนครินทร์ (live EGAT reading) | `dam:egat_water_crisis:ศรีนครินทร์` in observations.sqlite: storage 89.71%, inflow 144.84 MCM/day, release 3.19 MCM/day (36.92 m³/s) | observation row, not a KG node per se | MEASURED |
| วชิราลงกรณ (dam) | `node:dam:hii_dam:15`, `node:dam:hii_dam:56`, `node:dam:rid_res_table:วชิราลงกรณ์` (3 records) | dam | VERIFIED (held) |
| วชิราลงกรณ (live EGAT reading) | `dam:egat_water_crisis:วชิราลงกรณ`: storage 91.86%, inflow 101.31 MCM/day, release 8.02 MCM/day (92.82 m³/s) | observation row | MEASURED |
| ลุ่มน้ำแม่กลอง (basin, ONWR) | `node:basin:onwr:14` | basin | VERIFIED (held) |
| Mae Klong sub-basins (DWR) | 19 `sub_basin:14xx` records with `basin_name_en: Mae Klong` (sources/dwr_subbasins.yaml) | sub_basin | VERIFIED (held) |
| กาญจนบุรี (confluence area, gauge) | `node:gauge:thaiwater_waterlevel:K.3A` "สะพานข้ามแม่น้ำแม่กลองหน้าศาลากลาง จ.กาญจนบุรี" (13.99597, 99.538818); `node:gauge:thaiwater_waterlevel:KRN001` "เมืองกาญจนบุรี" | gauge (water level) | VERIFIED (held) — but this sits ABOVE/near the confluence, not confirmed as AT the dam |
| **เขื่อนแม่กลอง (dam node itself)** | **NOT FOUND as a `dam`-kind KG node.** Only found as: (a) a RAIN gauge, `node:rain_gauge:thaiwater_rain_24h:700554` "เขื่อนแม่กลอง" (13.95678, 99.61505); (b) an `asset_id: dam:rid_res_table:เขื่อนแม่กลอง`-style entry in `data/assets_registry.dump.yaml` (name_th: เขื่อนแม่กลอง) with `lat: null, lon: null, tag: OPEN` — no coordinate, not wired into the KG as a `dam`-kind node | **MISSING (as a dam node with coordinates/edges)** | OPEN |
| ท่าม่วง (อำเภอ) | 1 HII telemetry hit only: `node:gate:hii_watergate:709158` "สถานีโทรมาตร บ้านวังขนาย ต.วังขนาย อ.ท่าม่วง จ.กาญจนบุรี" — a sub-district (ตำบล) station, not confirmed as a river gauge on the Mae Klong mainstem itself | gate/telemetry | VERIFIED (held) — relevance to mainstem tailwater OPEN |
| บ้านโป่ง (อำเภอ, ราชบุรี) | `node:gauge:thaiwater_waterlevel:RAJ002` "บ้านโป่ง" (13.81866, 99.86508) — a real water-level gauge, distinct from several unrelated "บ้านโป่ง" place-name hits elsewhere in Thailand (Chiang Mai/Phitsanulok/Trat — NOT this Mae Klong one, filtered out by province/coordinate) | gauge (water level) | VERIFIED (held) |
| โพธาราม (อำเภอ, ราชบุรี) | `node:gauge:thaiwater_waterlevel:RAJ001` "โพธาราม" (13.63308, 99.8164) | gauge (water level) | VERIFIED (held) |
| ราชบุรี (อำเภอเมือง) | rain gauge only: `node:rain_gauge:thaiwater_rain_24h:3720` "ราชบุรี"; no water-level gauge found under this exact name | rain gauge | VERIFIED (held, partial — no water-level station found) |
| ดำเนินสะดวก | `node:canal:wp:202395` "คลองดำเนินสะดวก" (a canal, Wikipedia-derived) — **no river-mainstem gauge/node for the town itself found** | canal (named, not a gauge) | VERIFIED (canal only) — town node MISSING |
| บางคนที | `node:gate:hii_watergate:709168` "สถานีโทรมาตร อ.บางคนที ต.กระดังงา อ.บางคนที จ.สมุทรสงคราม"; `node:gate:hii_watergate:709173` "ปตร.บางนกแขวก" | gate/telemetry | VERIFIED (held) |
| อัมพวา | `node:canal:wp:1358266` "คลองอัมพวา" (canal only) — **no mainstem gauge node for the town itself found** | canal | VERIFIED (canal only) — town node MISSING |
| ปากแม่น้ำแม่กลอง (mouth, tide boundary) | **NOT FOUND** as any node (no tide/sea-boundary node for this specific river mouth located this check) | — | **MISSING** |
| สมุทรสงคราม (province, general) | `node:rain_gauge:thaiwater_rain_24h:455219` "สมุทรสงคราม"; several บางคนที/กระดังงา telemetry stations | rain gauge / telemetry | VERIFIED (held, partial) |

**Count summary**: of 11 named chain elements (2 upstream dams, confluence/Kanchanaburi, Mae Klong
Dam itself, 6 named downstream towns, the river mouth), **7 have at least one held node** (both
upstream dams w/ live readings, confluence/Kanchanaburi, บ้านโป่ง, โพธาราม, บางคนที, สมุทรสงคราม
partial), **2 have a canal-only hit but no town/mainstem gauge node** (ดำเนินสะดวก, อัมพวา), and
**2 are genuinely missing** (a proper `dam`-kind node for เขื่อนแม่กลอง itself with coordinates/
edges; any node at all for the river mouth/tide boundary). ท่าม่วง and ราชบุรี each have a partial/
uncertain hit (a sub-district telemetry station and a rain-only gauge respectively) rather than a
confirmed mainstem water-level station.

---

## 3. Direct answer to "where is น้ำท้ายเขื่อน (tailwater) for Mae Klong Dam" — OPEN

No single node in this repo's KG is confirmed as "the tailwater gauge immediately below Mae Klong
Dam." Three candidates held, none verified as the nearest:

1. `node:gauge:thaiwater_waterlevel:RAJ002` (บ้านโป่ง) — downstream of the dam by chain order, but
   river-distance not measured this check.
2. `node:gauge:thaiwater_waterlevel:RAJ001` (โพธาราม) — further downstream than RAJ002 by chain
   order, same caveat.
3. `node:gate:hii_watergate:709158` (บ้านวังขนาย, ต.วังขนาย, อ.ท่าม่วง) — closest by ADMINISTRATIVE
   district name (ท่าม่วง is where the dam sits) but not confirmed as a mainstem river station
   (name suggests a sub-district telemetry point, could be a canal/tributary station instead).

**NEXT VERSION task**: resolve actual river-km distance from the dam for each candidate (RID/HII
station metadata, if it carries a chainage/km field) and pick the nearest as the canonical
`tailwater_stage` node for Mae Klong Dam. See TODO #171.

---

## 4. Tide boundary at the mouth

**OPEN.** No node for ปากแม่น้ำแม่กลอง / the Gulf of Thailand boundary at Samut Songkhram was
found in this repo's KG this check. A tide boundary condition would be needed for any hydraulic
model of the lower reach (ดำเนินสะดวก → อัมพวา → mouth), consistent with how this repo already
treats the Chao Phraya/Bangkok side (tide interacts with drainage capacity there — see
`docs/CAPACITY.md`, BMA plan 2569 "น้ำทะเลหนุนสูง" language). No BMA-style tide table for the Mae
Klong mouth is held. NEXT VERSION task: locate an HII/RID tide station for the Mae Klong estuary
(candidate: search `thaiwater.net` tide/tidal stations for Samut Songkhram — not attempted this
task, outside its 3-fetch budget already spent on the notice itself).

---

## 5. What forecasting "when will +2.5 m reach each town" would need (NEXT VERSION — not attempted)

Per Toledo-first discipline (AGENTS.md ss2): no travel-time number is computed here. What would be
needed, in order:

1. **A declared travel time from RID/HII** (an agency-published lag table dam→town), which this
   repo does not hold for Mae Klong. This is the ONLY form of travel-time this repo would use
   without deriving a routing equation of its own (Toledo-first: no new formula derived inline).
2. **Failing that, HII `waterlevel_load`/discharge time series at consecutive Mae Klong stations**
   (K.3A above the dam, then RAJ002/RAJ001/others below it) — cross-correlating the arrival of a
   discharge pulse at each station empirically, WITHOUT assuming a wave-celerity formula (that
   would itself need Toledo registration first — a kinematic-wave or Muskingum-routing equation
   is not currently a registered PROP-FLOOD proposal).
3. **A registered coping/bankfull capacity (`coped_max`) for the Mae Klong reaches at each town**,
   analogous to `sources/capacity_ledger.yaml`'s Bangkok/Chao-Phraya entries — this repo holds NONE
   for Mae Klong (confirmed by grep, `capacity_ledger.yaml` is Bangkok-only). Without this, even a
   correct discharge number cannot be placed on the unified ladder (see the incident card §6 —
   the ladder mapping there is a PROPOSAL, explicitly blocked on this missing capacity value).

None of the above is executed this check. This section exists so a future NEXT VERSION worker does
not have to re-derive the requirements list.

---

## 6. TODOLIST — new rows #169 onward (5 columns)

Existing highest TODO number found in this repo (`docs/MVP_SCOPE_2026-09-27.md`, referencing
`docs/knowledge/URBAN_FLOOD_EVENT_LEDGER_2026-09-27.md`'s own table) is **#168** — this table
starts at **#169**, not #160, to avoid colliding with already-assigned numbers (verified by grep
across `docs/` and `sources/` for `#1[5-9][0-9]` this check, see method below the table).

| # | ปัญหา/ช่องว่าง | สิ่งที่ต้องทำ | owner | priority |
|---|---|---|---|---|
| 169 | ไม่มี `dam`-kind KG node ที่มีพิกัด/edge สำหรับเขื่อนแม่กลองเอง (มีแค่ rain gauge ชื่อเดียวกัน + assets_registry entry ที่ lat/lon เป็น null) | หาพิกัดจริงของเขื่อนแม่กลอง (egat.co.th หน้าโรงไฟฟ้า หรือ RID GIS) แล้วเพิ่มเป็น `dam`-kind node จริงใน build_river_kg.py's asset loader (ไม่ใช่แก้ assets_registry.dump.yaml มือ — ต้องผ่าน harvester ที่มีอยู่) | committer | high |
| 170 | ไม่ทราบว่า node ใดใน 3 ตัวเลือก (RAJ002/RAJ001/hii_watergate:709158) คือ tailwater gauge ที่ใกล้เขื่อนแม่กลองที่สุดจริง | ดึง metadata สถานี (river-km/chainage ถ้ามี) จาก HII/RID แล้วยืนยัน หรือวัดระยะทางจากพิกัดจริงเทียบกับพิกัดเขื่อน (ต้องรอ TODO #169 ก่อน) | committer | high |
| 171 | ไม่มี tide/sea-boundary node สำหรับปากแม่น้ำแม่กลอง (สมุทรสงคราม) | ค้นหาสถานีน้ำขึ้นน้ำลงของ thaiwater.net/HII บริเวณปากแม่น้ำแม่กลอง แล้วเพิ่มเป็น node ใหม่ผ่าน harvester ที่มีอยู่ (ไม่ใช่แก้ KG มือ) | committer | medium |
| 172 | ไม่มี `coped_max` (ความจุตลิ่งปลอดภัย) ของแม่น้ำแม่กลองที่จุดใดเลย — บล็อก unified-ladder mapping ในการ์ด incident นี้ทั้งหมด | สืบค้น RID/กรมชลประทาน สำหรับเกณฑ์ระดับเตือนภัย/ความจุตลิ่งที่ท่าม่วง/บ้านโป่ง/โพธาราม/ราชบุรี (คล้าย `sources/capacity_ledger.yaml` แต่คนละลุ่มน้ำ) | founder + committer | high |
| 173 | ท่าม่วงและราชบุรี (อำเภอเมือง) ไม่มีสถานีวัดระดับน้ำ (water-level) ที่ยืนยันแล้วบนลำน้ำหลัก — มีแค่ telemetry ต.วังขนาย (ท่าม่วง) และ rain gauge (ราชบุรี) | ยืนยันว่า hii_watergate:709158 เป็นสถานีบนแม่น้ำแม่กลองสายหลักหรือไม่ (อาจเป็นลำน้ำสาขา) และหาสถานี water-level จริงของอำเภอเมืองราชบุรี ถ้ามี | committer | medium |
| 174 | ดำเนินสะดวกและอัมพวา มีแค่ node คลอง (canal) ไม่มี node เมือง/gauge ของตัวอำเภอเอง | เพิ่ม node ตัวอำเภอ/ชุมชนริมน้ำ (riverside_zone, ดู `sources/dam_tailwater_vocabulary.yaml`) ผ่าน harvester ที่มีอยู่ ถ้าจะให้ chain สมบูรณ์ถึงปากแม่น้ำ | committer | low |
| 175 | ไม่มีค่า travel time (declared หรือ measured) จากเขื่อนแม่กลองถึงเมืองใดเลย — บล็อกคำถาม "น้ำจะถึงเมื่อไร" ทั้งหมด | สืบประกาศ RID ที่มักแนบเวลาถึง (lag hours) ต่อพื้นที่ หรือดึง HII waterlevel_load ของสถานีต่อเนื่องกันมาคำนวณ empirical lag (ห้าม derive สมการ routing เองก่อนขึ้นทะเบียน Toledo) | committer | medium |

**Grep method used for TODO-number collision check**: `grep -rhoE "#1[5-9][0-9]\b" . --include="*.md" --include="*.yaml"` across the repo root — highest hit was `#168`. Full-repo grep, not
scoped to `docs/knowledge/` alone, to avoid missing a number assigned in `sources/` or elsewhere.

---

## 7. Leak scan

No personal names, no local filesystem paths, no AI/vendor names in this file — checked by hand
before handoff.
