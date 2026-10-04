# AI Interface (FloodConnect API v1) — คู่มือสำหรับ AI ภายนอก

**จุดเข้าเดียวของระบบคือ `AI.md` (repo root)** — เอกสารนี้คือสเปกเทคนิคฉบับเต็มของสองทาง
ที่ `AI.md` ชี้มา (MCP server / static JSON API v1) สำหรับ AI assistant ภายนอกที่ต้องการอ่าน
สถานะน้ำ/คลอง/ปั๊ม/แนวโน้มของพื้นที่ที่ FloodConnect ครอบคลุม (ปัจจุบัน: สัมมากร,
ซอยรามคำแหง 53) — สร้างขึ้นหลังเหตุการณ์ที่ AI ภายนอกตัวหนึ่งตอบผิดว่า "receiving canal =
UNKNOWN" ทั้งที่ระบบนี้มีค่า `WL.BMA.02`/`WL.SSB.*` ที่สดอยู่ขณะนั้น — สาเหตุคือ AI ตัวนั้นไม่มี
ช่องทางเข้าถึงข้อมูล ไม่ใช่เพราะข้อมูลไม่มีจริง

## กฎ epistemic (single source: `AI.md`)

กฎการให้เหตุผลแบบละเอียด (dual-state, UNKNOWN != SAFE, tag vocabulary,
contradictions ต้องแสดงทั้งสองฝั่ง, งดออกคำสั่งอพยพ, รายการคำที่งดใช้ในข้อความถึงผู้อยู่อาศัย,
งดใส่เครดิตชื่อ AI/vendor) — **อ่านที่ `AI.md`'s "Mandatory reasoning rules" section
เป็นแหล่งเดียว** ไม่คัดลอกซ้ำที่นี่ทั้งชุด เพื่อไม่ให้เกิดปัญหาสองสำเนาที่ไม่ตรงกัน
(two-copies-drift). `skills/floodconnect/references/epistemic_rules.md` เก็บ provenance
เต็ม (อ้างอิง project decision ของแต่ละกฎ)

## ทางเลือก 1 — Local JSON export (ไม่ใช่ API ที่ไหน ไม่มี host ให้ GET)

**ไม่มีโฮสต์กลาง (project decision 2026-10-04):** repo นี้ไม่รัน/ไม่ publish `/api/v1/`
ที่ไหนให้ใครอ่านได้ทันที — ไม่มี URL ใดๆ ที่ตอบคำขอนี้ได้จริง `site/dist/api/v1/` เป็น
build artifact ที่ gitignore ไว้ **ไม่ถูก track ในคลังนี้เลย** ต้องรัน `site/build_data.py`
แล้ว `tools/api/export_api.py` บนเครื่องตัวเองก่อนเสมอ (ดู `tools/api/export_api.py`
สำหรับ argument ที่ต้องส่ง) จึงจะมีไฟล์ **local** ให้ MCP server หรือ client ที่อ่าน JSON Schema
อ่านได้ — ไม่มี path สำเร็จรูปในคลังนี้ และไม่มี `GET` ข้าม network ที่ไหนทำงานได้จริง คอลัมน์
"เส้นทางเดิม" ด้านล่างแค่บอกชื่อไฟล์ relative path ที่คุณจะได้ **หลังสร้างเอง** เท่านั้น — อ่านเป็น
local file path ไม่ใช่ HTTP call:

| ไฟล์ local (หลังรันเองแล้วเท่านั้น) | คำอธิบาย |
|---|---|
| `site/dist/api/v1/index.json` | รายชื่อพื้นที่ + ตารางลิงก์ endpoint อื่นทั้งหมด |
| `site/dist/api/v1/areas/{area_id}.json` | สถานะเต็มของพื้นที่หนึ่ง — มี `current_local_state` และ `forward_hazard` แยกกันเสมอ |
| `site/dist/api/v1/typology/graph.json` | กราฟ typology ทั้งหมด (node-link JSON) |
| `site/dist/api/v1/typology/subgraph/{area_id}.json` | กราฟ typology เฉพาะพื้นที่ |
| `site/dist/api/v1/community/self_help_dag.json` | DAG ช่วยเหลือตัวเองของชุมชน (`schema_status: proposal_operational_schema`) |
| `site/dist/api/v1/sources.json` | ทะเบียนแหล่งข้อมูลต้นทาง (`auth` อยู่ใน enum `none`/`key` เท่านั้น ไม่มี secret จริง) |
| `site/dist/api/v1/schema/{name}.schema.json` | JSON Schema (draft 2020-12) ของแต่ละไฟล์ |
| `site/dist/api/v1/openapi.yaml` | สเปก OpenAPI เดิม (อธิบายรูปร่างไฟล์ ไม่ใช่ endpoint ที่มีจริง) |

กติกาการสร้างไฟล์: **หนึ่ง network request ต่อหนึ่ง URL ต่อนแหล่งข้อมูลต้นทาง ไม่มี retry**
(เกิดขึ้นตอนรัน `collect.py`/`floodconnect answer` (refresh เป็น default อยู่แล้ว) บนเครื่องคุณเอง ไม่ใช่ตอนอ่านไฟล์
เหล่านี้) — ถ้าแหล่งข้อมูลเรียกไม่สำเร็จ ให้ถือว่าฟิลด์นั้น `tag: OPEN` ไม่เดาไม่ลองซ้ำ

## ทางเลือก 2 — MCP server

`tools/mcp/floodconnect_mcp.py` (stdio) — ดูตัวอย่างการตั้งค่าที่
`tools/mcp/README_config_example.json`:

```json
{
  "mcpServers": {
    "floodconnect": {
      "command": "python",
      "args": ["tools/mcp/floodconnect_mcp.py"],
      "env": { "FLOODCONNECT_API_BASE": "/absolute/path/to/floodconnect/site/dist/api/v1" }
    }
  }
}
```

Tools: `floodconnect_list_areas`, `floodconnect_get_area_state`,
`floodconnect_get_station`, `floodconnect_get_typology_subgraph`,
`floodconnect_find_safe_route`, `floodconnect_list_upstream_sources`,
`floodconnect_explain_rules`. ทุก tool ตอบกลับพร้อม `source`/`staleness`/`tag`
เสมอ (shared envelope helper — ไม่มี tool ไหนลืมใส่)

## Agent Skill — wrapper รอบสองทางเลือกข้างบน ไม่ใช่ทางที่สาม

`AI.md` (repo root) ชี้ไปยัง **สามทาง** ที่อ่านข้อมูลเดียวกัน: MCP tool | `kb.py answer`
(เรียกตรงในเครื่อง ไม่ต้องรันเซิร์ฟเวอร์) | static `api/v1` json (สองทางหลังนี้คือสองทางเลือก
ข้างบนในเอกสารนี้). `skills/floodconnect/SKILL.md` ไม่ใช่ทางที่สี่ — มันเป็น agent-skill
wrapper รอบทางเลือก 1–2 ข้างบนสำหรับ AI assistant ที่รองรับระบบ skill/tool-definition
ทั่วไป ให้โหลด skill นี้ก่อนตอบคำถามเกี่ยวกับสถานะน้ำ/คลอง/ความปลอดภัยของพื้นที่ที่
FloodConnect ครอบคลุม มีตัวอย่างจริงจากเหตุการณ์ Sammakorn ที่
`skills/floodconnect/references/sammakorn_worked_example.md`

## หมายเหตุความปลอดภัย

- อ่านอย่างเดียว (read-only), ข้อมูลสาธารณะเท่านั้น
- ไม่มี credential/token/พาธเครื่องท้องถิ่น/username/internal IP/Forgejo URL
  ปรากฏใน endpoint ใดๆ
- ไม่มีชื่อ AI vendor/model ใน output ที่ถึงผู้อยู่อาศัย — ใช้ "ผู้ช่วย AI" แทนถ้าถูกถามเรื่อง
  แหล่งที่มา
