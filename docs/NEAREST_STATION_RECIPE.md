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
lat,lon, continue to Step 1 (if you have the FloodConnect CLI/MCP available) or Step 2
(if you are a browsing-only chat AI with no tool access, per `docs/AI_TIERS.md` T0/T1).

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
| **All of Thailand** (any river/canal telemetry gauge) | `https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel` (public JSON, no key) — Hydro-Informatics Institute (HII)/สสน., via thaiwater.net | Every station's `station.tele_station_lat`/`tele_station_long` (coordinate), `station.tele_station_name.th` (name), `waterlevel_msl` (current reading), `storage_percent`, `station.min_bank`/`ground_level` where the agency publishes them, `geocode.province_name.th` |
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
3. Default radius: **3 km** (FloodConnect's own default, `_answer_state`'s
   `radius_km`) — widen only if you have no station at all within that radius, and say
   so plainly ("nearest station is Xkm away, outside the normal radius").
4. If two sources disagree about the same station, **report both**, tagged, never pick
   one silently (`feedback-floodconnect-conflicting-data-rule`, applies to any AI
   relaying this data, not only this repo's own code).

## Step 4 — read the agency's own status, never invent a threshold

- If the station/bulletin carries its own status word (`ระดับน้ำวิกฤติ`/critical,
  `เฝ้าระวัง`/watch, `ระดับน้ำปกติ`/normal) — **use that word**, mapped per
  `docs/INDICATORS.md` §1's colour rule (critical→RED, watch→YELLOW, normal→GREEN).
- If only a raw number is published (`waterlevel_msl`) with the agency's own
  `min_bank`/`ground_level` fields, you may compute `distance_to_bank_m` /
  `bank_fill_percent` exactly as `docs/INDICATORS.md` §7/§8 define them — **both from
  the agency's own fields, never a number you choose**.
- No status word AND no bank/ground-level fields for that station → the honest answer
  is **`UNKNOWN`**, not GREEN. `docs/INDICATORS.md`'s rule applies to every AI doing
  this by hand too: **UNKNOWN is never SAFE.**
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
