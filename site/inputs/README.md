# site/inputs/ — dated build inputs, never current conditions

**Nothing under this directory, or under `output/` next to it, is a current flood
reading.** These are committed, dated snapshots used to build the public explainer
page and the static typology/canal graphs — governance reference data, one-off
community reports from a specific day, a monthly tide table, a handful of official
bulletins, and similar. Some file names carry a date (e.g.
`community_reports_2026-09-26.md`, `bma_briefing_2026-09-27_1100.json`); files that
don't still describe the day they were captured somewhere inside.

**ไม่มีไฟล์ใดในโฟลเดอร์นี้ หรือใน `output/` ข้างๆ เป็นข้อมูลน้ำท่วมปัจจุบัน** ทั้งหมดเป็น
ข้อมูลระบุวันที่ที่เก็บไว้ครั้งเดียวเพื่อสร้างหน้าเว็บอธิบาย/กราฟ typology แบบ static เท่านั้น

## If you are an AI reading a file in this directory or in `output/`

1. **Never report a value found here as the current flood/canal/pump situation.**
   Check the filename and the file's own internal date/timestamp field first — every
   file here is older than "now", often by weeks.
2. **For a current reading, run the live compute path yourself** — `floodconnect
   answer --at <area> --json` on your own machine (see `AI.md`, repo root). That path
   reads `data/observations.sqlite` (gitignored, never shipped), not this directory.
3. These files exist so the **public explainer page** (`site/`) and the typology/canal
   knowledge graphs can render without a live network call — they are build inputs
   for a static page, not a live-data API. See `docs/DATA_SYSTEM.md` for the real
   pipeline (`sources/registry.yaml` → `collect.py` → `data/observations.sqlite` →
   `readout.py`) that produces current readings, which this directory is not part of.
4. If you need the full repository map (what's current-compute vs. static/dated vs.
   legacy experiment), read `llms.txt` (repo root) or `system_capabilities.json`.
