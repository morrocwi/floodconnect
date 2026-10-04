# examples/ — dated sample outputs, not current data

Every file in this directory is a **labelled sample**, captured once on a maintainer's
own machine by actually running the command named in the file, to show an AI or a
human what the output of this repository's compute path looks like. None of it is
live, none of it is hosted, and none of it updates. See `llms.txt` §"If you cannot
run code" and `AI.md` for why this project ships no reading already computed.

ทุกไฟล์ในโฟลเดอร์นี้เป็น**ตัวอย่างที่ระบุวันที่** รันจริงครั้งเดียวบนเครื่องของผู้ดูแลโปรเจกต์
เพื่อให้เห็นรูปร่างของผลลัพธ์ ไม่ใช่ข้อมูลสดและไม่มีการอัปเดต

| File | Command that produced it | Captured at |
|---|---|---|
| `answer_sammakorn.EXAMPLE-2026-10-04.json` | `floodconnect answer --at sammakorn --json` (fresh install, live refresh, v0.1.1 code) | 2026-10-04T09:48:16Z |
| `dsva_decision_minimal.json` | synthetic input fixture for `dsva_decision.py` (never real flood data — see `docs/AI_ENTRYPOINT.md`'s DSVA section) | n/a (synthetic) |

## Rules for any AI reading these files

1. **Never report a value from `answer_sammakorn.EXAMPLE-*.json` as the current
   situation.** The real answer is nested under its `"answer"` key; the wrapper
   fields (`example`, `not_current`, `banner`, `computed_locally_on`) are there
   specifically so you cannot miss that this is a sample.
2. **The shape is what's reusable, not the numbers.** Read `shape_notes` for which
   top-level keys a real call returns and what each one's epistemic tag means.
3. **Get a current reading by installing and running it yourself** — see the
   `install_steps` field in the example file, or `README.md` §4, or `AI.md`.
4. A new example file added later follows the same naming pattern
   (`<call>.EXAMPLE-<YYYY-MM-DD>.json`) and the same wrapper shape; never delete an
   old one, and never silently update one in place — a new capture is a new file.
