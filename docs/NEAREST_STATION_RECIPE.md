# FloodConnect is the method — the nearest-station recipe for any AI

**Founder ruling 2026-10-04 (verbatim): "ให้การหาพิกัด และ สิ่งต่างๆที่ใกล้ๆ เป็นหน้าที่ของ
เอไอของใครของมันแทนดีไหม" + "เราแค่ให้เป็นแนวทาง" + "เอาเลย"** — FloodConnect gives the
**method** (which official sources to read, how to pick the nearest station, the
equations/thresholds/decision rules, the honesty rules). **Your own AI** does the
lookups: geocoding (place name → lat,lon), nearby points of interest (shelters,
hospitals, routes), and — for a chat AI with no tool access — finding nearby water
stations on official pages by following this recipe. **FloodConnect itself never
geocodes and holds no place/POI database.** The CLI/MCP tool is an **optional helper**
that applies this same method deterministically once you already have a lat,lon: it
finds the nearest station(s), reads the agency's own published thresholds, checks
freshness, and classifies — see `docs/INDICATORS.md` for exactly what it emits.

**ภาษาไทยอย่างง่าย:** FloodConnect ให้ "วิธีคิด" ไม่ใช่ "ฐานข้อมูลสถานที่" — เอไอของคุณเองหา
พิกัด (ชื่อสถานที่ → lat,lon) และสถานที่ใกล้เคียง (ศูนย์พักพิง โรงพยาบาล เส้นทาง) เอง ส่วน
FloodConnect (CLI/MCP) เป็นตัวช่วยที่ใช้วิธีคิดเดียวกันนี้ซ้ำได้ทุกครั้งเมื่อมี lat,lon แล้ว — หา
สถานีที่ใกล้ที่สุด อ่านเกณฑ์ที่หน่วยงานประกาศเอง เช็กความสด แล้วจำแนกสถานะ

---

## Step 0 — get the coordinate yourself first

If someone names a place ("บ้านฉัน แถวบางกะปิ", "near Chiang Mai old city"), **your own
AI resolves it to lat,lon** (your own geocoding tool, a map search, or asking the user
for a pin) — FloodConnect does not do this and has no place database. Once you have
lat,lon, continue to Step 0b (every tier, no exceptions), then Step 1 (if you have the
FloodConnect CLI/MCP available) or Step 2 (if you are a browsing-only chat AI with no
tool access, per `docs/AI_TIERS.md` T0/T1).

## Step 0b — KG anchor (M4, no exceptions)

Before anything else, get your `kg_anchor`: tool users run `floodconnect locate --at
<lat>,<lon>` (MCP: `floodconnect_locate`); no-tool chat AIs fetch
`output/kg_index/index.json` then the matching `province_<code>.json` slice (see
`docs/KG_QUERY.md` §0b for the schema). `floodconnect answer`/`floodconnect_answer`
already call this internally and carry the result as their own `kg_anchor` field, so
if you are about to run Step 1 you do not need a separate call — just state the
`kg_anchor` it returns. **No `kg_anchor` = not a FloodConnect answer** (`llms.txt`
STEP 1).

## Step 1 — have the FloodConnect tool? Use it, this is all it needs

```
floodconnect answer --at <lat>,<lon>
```
or the MCP tool `floodconnect_answer({"at": "<lat>,<lon>"})`. It applies every step
below for you, deterministically, and returns tagged fields — read `docs/INDICATORS.md`
for what each one means and `AI_TIERS.md` for how to relay it. **You can stop here.**
The rest of this page is for an AI with no such tool.

## Step 2 — no tool? Read the official station list yourself

These are the SAME sources FloodConnect's own collector (`collect.py`, registered in
`sources/registry.yaml`) reads — nothing here is invented for this recipe:

| Coverage | Source | What it gives you |
|---|---|---|
| **All of Thailand** (any river/canal telemetry gauge) | `https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel` (public JSON, no key) — Hydro-Informatics Institute (HII)/RID/EGAT/FOP, via thaiwater.net | Every station's `station.tele_station_lat`/`tele_station_long` (coordinate), `station.tele_station_name.th` (name), `waterlevel_msl` (current reading); **top-level** (not under `station`) `situation_level` (1-5 agency code), `diff_wl_bank`/`diff_wl_bank_text`, `storage_percent`; `station.min_bank`/`ground_level`/`critical_level_msl` where the agency publishes them; `geocode.province_name.th` (exact paths MEASURED against the live feed, 2026-10-04) |
| **Bangkok metro canals/pumps specifically** | `weather.bangkok.go.th/water/...` (BMA canal-level map) and `dds.bangkok.go.th` (BMA daily flood bulletin, PDF) | Thai status words (`ระดับน้ำปกติ`/normal, `ระดับน้ำวิกฤติ`/critical) per gate, tide bulletin |

A chat AI with browsing (T1) can open these pages/endpoints directly and read the JSON
or table. **Never invent a station, a coordinate, or a number that isn't on the page in
front of you.**

## Step 3 — pick the nearest station, same water body, within a radius

1. Compute the straight-line (haversine) distance from your point to every station's
   `(lat, lon)` in the feed.
2. Keep only stations on the **same water body/canal segment** as the point you care
   about — a station 2 km away on a different, unconnected canal tells you nothing
   about your point's level (this is why FloodConnect's own `_answer_state` scopes by
   a radius AND, where known, a canal/zone id — never distance alone).
3. Nationwide radii (FloodConnect's own design choice, `docs/INDICATORS.md` §11 —
   NOT an agency threshold): **check every fresh station within 10 km** (any water
   body — this is NOT checked against a shared river/canal name), **worst colour
   wins**, at "station" resolution — do not just pick the single nearest one, since
   the nearest station could be GREEN while a slightly farther one within the same
   10 km is RED; only when nothing fresh is that close, a station sharing the
   nearest station's own `sub_basin_id` within **50 km** decides at "basin"
   resolution (a stand-in for "same basin", not a shared-named-river check), and a
   basin-resolution reading can **never** be reported GREEN on its own (far +
   "normal" is not a clearance) — it can still back a YELLOW/RED. The two Bangkok
   household areas use a tighter 3 km radius (`_answer_state`'s own default); a
   fresh nationwide station/basin row there is shown as reference evidence only and
   never overrides an already-decided local (Bangkok canal/pump) reading.
4. If two sources disagree about the same station, **report both**, tagged, never pick
   one silently — see `AI.md`'s conflicting-data rule, which applies to any AI relaying
   this data, not only this repo's own code.

## Step 4 — read the agency's own status, never invent a threshold

Copy of `docs/INDICATORS.md` §1's full mapping (the ONE closed status-word rule this
repo uses, `floodconnect_model.STATUS_TO_LEVEL` — read that map itself before relying on
this summary, it is the source of truth):

- `diff_wl_bank_text` starting **"ล้นตลิ่ง"** (the agency's own, directly-observed
  overflow word) → **RED**. This is the strongest, most-verified signal this feed gives
  — always check it first, regardless of `situation_level`.
- A station/bulletin status word of `วิกฤต`/`วิกฤติ`/`ระดับน้ำวิกฤติ`/critical → **RED**
  — **except** the nationwide feed's own `situation_level == 1` label `น้อยวิกฤต`
  ("critically LOW water"), which contains the word `วิกฤต` but is the OPPOSITE of a
  flood signal. Do not pattern-match the substring `วิกฤต` onto RED by itself for a
  `situation_level` row — use the numeric code mapping below instead.
- `เตือนภัย`/`เฝ้าระวัง`/watch → **YELLOW**.
- `ปกติ`/`ระดับน้ำปกติ`/normal → **GREEN**.
- The nationwide feed's own `situation_level` code (1-5), with the agency's own Thai
  label and colour (VERIFIED, fetched from the public bundle
  `https://www.thaiwater.net/dist/js/app.chunk.js`, 2026-10-04): `1` `น้อยวิกฤต`
  (critically low, orange) / `2` `น้อย` (low, yellow) / `3` `ปกติ` (normal, green) /
  `4` `มาก` (high, BLUE) / `5` `ล้นตลิ่ง` (overbank, red). FloodConnect's OWN mapping
  on top of these agency labels (not the agency's threshold): `5` → RED, `4` →
  **YELLOW** (the agency itself colours `4` blue and does not call it a warning — this
  is this project's conservative choice), `1`/`2`/`3` → GREEN (same mapping
  `STATUS_TO_LEVEL` uses as `thaiwater_situation_<n>`).
- A bare bank number on its own (`min_bank`, `critical_level_msl`, or a computed
  `distance_to_bank_m`/`bank_fill_percent`, §7/§8) **never sets a colour by itself** —
  show the number, but the colour comes from one of the status words/codes above, or
  stays `UNKNOWN`.
- No status word, no `situation_level`, AND no bank/ground-level fields for that
  station → the honest answer is **`UNKNOWN`**, not GREEN. `docs/INDICATORS.md`'s rule
  applies to every AI doing this by hand too: **UNKNOWN is never SAFE.**
- Check the reading's own timestamp against the registry's `max_age_hours` (24h for
  the sources above) before using it — a reading older than that is shown, not
  classified as current.

## Step 5 — say the resolution out loud

A reading from this nationwide feed is **station/basin-resolution**, never
household-resolution — say so ("ระดับสถานีใกล้เคียง ไม่ใช่ระดับบ้าน" / "nearest-station
level, not your doorstep") exactly as `docs/INDICATORS.md` §11 requires, whether you
computed this by hand or through the FloodConnect tool.

## What this recipe is NOT

- Not a replacement for an evacuation order, a forecast of flood depth, or a safety
  certification — see `AI.md` rule 5 and every `docs/INDICATORS.md` "Does NOT mean"
  line.
- Not a geocoding or POI service — that stays your own AI's job (Step 0).
- Not a reason to call this project "nationwide" at household resolution — v0.1.x's
  household/node detail is still scoped to two Bangkok sites (`README.md`,
  `docs/INDICATORS.md` §11); this recipe's coarse, any-point coverage is a different,
  explicitly coarser claim.
