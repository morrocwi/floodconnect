# Card — Community self-organisation pattern (แฟลตคลองจั่น + ร่มเกล้า, 2569)

**Tag**: RELAYED (โพสต์ Facebook ของนักวิชาการมหาวิทยาลัย, 28 ก.ย. 2569 -- ไม่ใส่ชื่อบุคคลใน
กราฟ) · **บันทึกเข้า**: 2569-09-28

## 1. ข้อเท็จจริง (RELAYED)

ผู้อยู่อาศัยแฟลตคลองจั่นและเคหะร่มเกล้ารวมตัวช่วยเหลือกันเองเพราะความช่วยเหลือยังไปไม่ถึงครบทุกจุด:
รวมเงินกองกลาง; แบ่งคนลุยน้ำออกไปซื้ออาหาร; อีกกลุ่มทำครัวกลางทำอาหารให้ทุกคน; ใครมียา/น้ำดื่ม
แบ่งปันกัน (บันทึกเป็นบทบาท ไม่ใช่เพศ ตามคำสั่งฟาวน์เดอร์)

## 2. Pattern (reusable template, area-agnostic)

บทบาทเดิมที่เอกสารนี้มีอยู่แล้ว (`docs/COMMUNITY_SELF_HELP_DAG.md` §3.3): coordinator,
welfare, route_checker, resource_keeper, comms — เพิ่มบทบาทเดียวที่ขาด:
**`procurement_runner`** (คนออกไปหาซื้อของเมื่อเส้นทาง ASSISTED/OPEN เท่านั้น — ไม่ใช้เส้นทาง
UNKNOWN, เงื่อนไขความปลอดภัยเป็นข้อความ ไม่ใช่ตัวเลข)

Node kinds (reuse-first, ไม่มี kind ใหม่): `support` (kitchen service, แบบเดียวกับ
`romklao_ops_kitchen_ram192`), `resource` (`shared_pool` — เงิน/ยา/น้ำดื่ม, ไม่มีจำนวน)

## 3. Typology (ดู `typology/nodes/community_selforg_pattern_2026-09-28.yaml`)

- `RES.TOOL.SHARED_POOL` -- generic (`pool_subtypes: [money, medicine, drinking_water]`)
- `CIV.ZONE.KHLONGCHAN_FLATS`, `CIV.ZONE.ROMKLAO` (kind `soi_surface`, layer `civil` --
  reuse ของเดิมที่ SOI.SAMMAKORN.17/18 ใช้อยู่แล้ว) -- `CIV.ZONE.ROMKLAO` มี
  `self_help_dag_ref: romklao_zone` (cross-reference attribute, ไม่สร้าง node ซ้ำกับที่มีอยู่
  แล้วจาก drone commit)

## 4. Self-help DAG (`site/inputs/community/self_help_dag.yaml`)

- area ใหม่ `khlongchan_flats`: zone + community-kitchen support node, ตาม pattern เดียวกับ
  ร่มเกล้า
- `resources: [{type: shared_pool, ...}]` เพิ่มเข้าทั้ง `khlongchan_flats_zone` และ
  `romklao_zone` (ของเดิม) -- ลิงก์ pattern เข้ากับ Romklao ตามคำสั่ง
- `roles_active` (optional, vocabulary ปิดใน `community_dag.py::COMMUNITY_ROLES`)

## 5. เทียบกับ card_yucharoen_model_2554 (อยู่เจริญโมเดล 2554)

| มิติ | อยู่เจริญ 2554 | Pattern นี้ (คลองจั่น/ร่มเกล้า 2569) |
|---|---|---|
| โครงสร้าง | คณะกรรมการทางการ, ประธานมาจากเลือกตั้ง, ประชุมรายเดือน (สถาบัน ไม่ใช่ตัวบุคคล) | บทบาทเฉพาะกิจช่วงวิกฤต (coordinator/welfare/route_checker/resource_keeper/comms/procurement_runner) -- ไม่มีโครงสร้างทางการล่วงหน้าที่ระบุในโพสต์ |
| การเงิน/ทรัพยากร | กองทุนขยะรีไซเคิลสะสมล่วงหน้า + งบสนับสนุนจากเขต/หน่วยงานภายนอก | เงินกองกลางที่รวมกันเฉพาะกิจตอนเกิดเหตุ (shared_pool) -- ไม่มีกองทุนสะสมล่วงหน้าที่ระบุ |
| สิ่งที่ตรงกัน | การพึ่งพาตนเองของชุมชน, การแบ่งงานตามทักษะ/บทบาท, เครือข่ายภายในช่วยกันเอง | เหมือนกัน -- ทั้งสองกรณีให้ชุมชนขับเคลื่อนเองก่อนรอความช่วยเหลือจากรัฐ |
| สิ่งที่ใหม่ในกรณีนี้ | -- | ครัวกลางเป็นจุดศูนย์กลางชัดเจน + บทบาท procurement_runner ผูกกับเงื่อนไขเส้นทาง (ASSISTED/OPEN เท่านั้น) ซึ่งอยู่เจริญไม่ได้ระบุกลไกนี้ |

## 6. ตั้งชุมชนเมื่อฉุกเฉิน (checklist)

ดู `docs/COMMUNITY_SELF_HELP_DAG.md` §4.2 (เพิ่มโดยงานนี้) -- สรุปจาก pattern ข้างบน เป็นภาษาไทย
ธรรมดา ไม่มีคำห้าม/ไม่ต้อง/ไม่ควร/ผ่อนคลาย
