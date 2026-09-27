# Community Self-Help DAG — จาก “รอดเอง” ถึง “node ปลอดภัยภายนอก”

> **สถานะ:** operational proposal / ยังไม่ใช่คำสั่งอพยพหรือการรับรองความปลอดภัย  
> **โค้ด:** `community_dag.py`  
> **กราฟประกาศ:** `site/inputs/community/self_help_dag.yaml`

FloodConnect เดิมตอบคำถามว่า “น้ำ/คลอง/ปั๊ม/ฝน/ถนนตอนนี้เป็นอย่างไร” เอกสารนี้เพิ่มอีกชั้นหนึ่ง:
**เมื่อคนรู้สถานการณ์แล้ว จะเชื่อมตัวเองเข้ากับเครือข่ายช่วยเหลืออย่างไรจนถึงพื้นที่ปลอดภัยภายนอก**

หลักคือ **ช่วยตัวเองก่อน → ช่วยเพื่อนบ้าน → รวมเป็นพื้นที่ → ไปยังจุดพักภายใน →
ออกจากพื้นที่ → ถึง node ภายนอกที่ตรวจแล้ว** โดยไม่ต้องรอให้หน่วยงานรัฐเป็นผู้สร้างเครือข่ายให้
แต่ยังใช้หน่วยฉุกเฉิน/รัฐเป็น escalation เมื่อเกินกำลังชุมชน

---

## 1. DAG 6 ชั้น

ให้กราฟเป็น

[
G=(V,E), qquad ell:Vightarrow{0,1,2,3,4,5}
]

โดยทุกเส้นเชื่อมต้องผ่านเงื่อนไข

[
(u,v)in E Rightarrow ell(v)>ell(u)
]

ดังนั้น edge ทุกเส้นเดิน “ไปข้างหน้า” เสมอและ **ไม่มีวงวน (cycle)**

| layer | node | หน้าที่ |
|---:|---|---|
| 0 | `household` | คน/ครัวเรือนทำให้ตัวเองรอดก่อน |
| 1 | `buddy_cell` | บ้านใกล้กันช่วยเช็กกัน |
| 2 | `zone` | พื้นที่ย่อยรวม demand/supply/สถานะทาง |
| 3 | `internal_safe` | จุดพักหรือรวมพลภายในที่ตรวจแล้ว |
| 4 | `egress` | ประตู/ทางออกจากพื้นที่ |
| 5 | `external_safe` | node ปลอดภัยภายนอกที่ตรวจภาคสนามแล้ว |

edge สามารถข้ามชั้นได้ เช่น household → egress หากเส้นทางตรงปลอดภัยจริง
แต่ห้ามย้อนกลับหรือเชื่อมระดับเดียวกันในกราฟ routing นี้

---

## 2. เริ่มจาก “ตัวเองรอด”

ก่อนคนหนึ่งจะกลายเป็นผู้ช่วยคนอื่น ให้ household node เช็กขั้นต่ำ 6 เรื่อง:

1. **คน** — ทุกคนอยู่ครบหรือไม่ ใครช่วยเคลื่อนย้ายตัวเองไม่ได้
2. **ไฟฟ้า** — มีน้ำใกล้ระบบไฟ/ปลั๊ก/เครื่องใช้หรือไม่
3. **ยา/ของจำเป็น** — ของที่ต้องใช้ต่อเนื่องอยู่กับตัวแล้วหรือยัง
4. **น้ำดื่ม/อาหารระยะสั้น** — พอให้ไม่ต้องออกไปเสี่ยงโดยไม่จำเป็น
5. **สื่อสาร** — โทรศัพท์/แบตเตอรี่/ช่องทางสำรอง
6. **ทางออก** — รู้ว่าออกได้ทางไหน และทางนั้นเพิ่งถูกตรวจเมื่อใด

จุดสำคัญคือ **household ที่ยังดูแลตัวเองไม่ได้ ไม่ควรถูกนับเป็น “กำลังอาสา”**  
มันควรถูกนับเป็น demand ของ buddy cell ก่อน

---

## 3. Social network: บ้าน → buddy → zone

### 3.1 Buddy cell

หน่วยที่เล็กที่สุดของ mutual aid ไม่ควรเป็น “ทั้งหมู่บ้าน” แต่เป็นบ้านที่รู้จักพื้นที่เดียวกันจริง
เช่นกลุ่มบ้านใกล้กันที่สามารถถามกันสั้น ๆ ได้ว่า:

- ติดต่อได้ / ติดต่อไม่ได้
- ปลอดภัยอยู่ / ต้องย้าย
- ต้องการคนช่วยเคลื่อนย้ายกี่คน
- มีทรัพยากรอะไรแบ่งได้
- ทางหน้าบ้านผ่านได้หรือไม่

ไม่ต้องส่งชื่อเต็ม โรค หรือเลขบ้านละเอียดขึ้น public board

### 3.2 Zone node

zone ทำหน้าที่ **aggregate** ไม่ใช่ “ผู้บัญชาการ”

ตัวอย่างข้อมูลที่ zone ควรรู้:

[
D_Z=(n_{	ext{move}},n_{	ext{medical}},n_{	ext{mobility}},n_{	ext{unreachable}})
]

และทรัพยากร:

[
S_Z=(n_{	ext{helpers}},n_{	ext{vehicles}},n_{	ext{lights}},n_{	ext{powerbanks}},ldots)
]

ระบบไม่ต้องพยายามลดทุกอย่างให้เหลือเลขเดียว เพราะ “คนต้องย้าย 3 คน” กับ “มีรถ 1 คัน”
เป็นคนละชนิดของข้อมูลและควรเห็นแยกกัน

### 3.3 บทบาทขั้นต่ำ

แต่ละ zone มีเพียง:

- **coordinator 1 คน + backup 1 คน** — รวมสถานะ ไม่ใช่ออกคำสั่งแทนทุกคน
- **welfare/buddy** — เช็กบ้านที่ขาดการติดต่อ
- **route checker** — รายงานทางที่ตนเองอยู่หรือมองเห็นได้โดยไม่เข้าไปเสี่ยง
- **resource keeper** — รู้ว่าของ/รถ/จุดชาร์จอยู่ที่ไหน
- **comms** — ส่งสถานะขึ้น FloodConnect/กลุ่มสื่อสาร

คนหนึ่งถือหลายบทบาทได้ในชุมชนเล็ก

---

## 4. Spatial node ต้องมีอะไร

แต่ละ node ไม่ควรเป็นแค่ “ชื่อสถานที่” แต่เป็น object ที่บอกอย่างน้อย:

- `kind`, `layer`
- `status = SAFE / DEGRADED / UNSAFE / UNKNOWN`
- `fresh` — สถานะยังใหม่พอหรือไม่
- `capacity_persons`, `occupied_persons`
- `services` เช่น `water`, `power`, `toilet`, `first_aid`, `charging`, `comms`
- accessibility/mode ที่รองรับ
- พิกัดเมื่อเป็นสถานที่จริง
- เวลาตรวจล่าสุด + แหล่ง/วิธีตรวจ

**โรงพยาบาล โรงเรียน วัด มัสยิด อาคารสูง หรือถนนใหญ่ ห้ามถูกถือว่าเป็น safe node โดยอัตโนมัติ**
ต้องยืนยันสถานะน้ำ ทางเข้า ไฟฟ้า ความจุ และการเปิดใช้งาน ณ เวลานั้นก่อน

---

## 5. Edge คือ “ทางที่ตรวจแล้ว” ไม่ใช่เส้นบนแผนที่

edge ระหว่างสอง node ต้องมีอย่างน้อย:

- `status = OPEN / ASSISTED / BLOCKED / UNKNOWN`
- `safety = CLEAR / CAUTION / BLOCKED / UNKNOWN`
- `field_verified`
- `fresh`
- `modes` เช่น walk / vehicle
- `max_group`
- `distance_m` ถ้าวัดได้

ถ้าค่าเป็น `UNKNOWN`, stale หรือยังไม่ field-verified  
**routing engine จะไม่ใช้เส้นนั้น**

นี่คือหลักสำคัญกว่า algorithm: “ไม่มีข้อมูล” ต้องแปลว่า **ไม่รู้** ไม่ใช่ “น่าจะผ่านได้”

---

## 6. คณิตศาสตร์เลือกเส้นทาง — constraint ก่อน score

สำหรับคนหรือกลุ่มขนาด (g), mode (m), route (P)

### 6.1 ตัดเส้นที่ใช้ไม่ได้ก่อน

ให้ feasible edge predicate เป็น

[
phi(e;g,m,t)=1
]

ก็ต่อเมื่อทั้งหมดจริง:

- edge ถูกตรวจภาคสนามแล้ว
- ข้อมูลยัง fresh
- status ∈ {OPEN, ASSISTED}
- safety ∈ {CLEAR, CAUTION}
- mode (m) ใช้ได้
- capacity ของ edge ถ้ามี (ge g)
- destination node ไม่เป็น UNSAFE/UNKNOWN
- destination capacity ถ้ามี (ge g)

ดังนั้น feasible graph คือ

[
G_t^{*}=(V_t^{*},E_t^{*})
]

ไม่ใช่กราฟถนนทั้งหมด

### 6.2 safe external target

node (v) เป็นปลายทางได้เมื่อ:

[
	ext{ExternalSafe}(v)=
[	ext{kind}=external_safe]
land[	ext{verified}=1]
land[	ext{fresh}=1]
land[	ext{status}=SAFE]
land[	ext{freeCapacity}ge g]
land[	ext{services}supseteq needs]
]

ถ้าไม่มี node ใดผ่านครบ ระบบต้องตอบ **NO FEASIBLE SAFE ROUTE**
ไม่เลือก “ตัวที่ดูดีที่สุด” จาก node ที่ยังไม่ปลอดภัย

### 6.3 ไม่ใช้ weighted risk score

เมื่อเหลือแต่เส้นทาง feasible แล้ว จัดลำดับเส้นทางด้วย tuple

[
J(P)=
(A,D,C,U_c,-B,U_d,L,H)
]

อ่านจากซ้ายไปขวาแบบ lexicographic:

- (A) = จำนวน edge ที่ต้องมี assistance
- (D) = จำนวน degraded transit nodes
- (C) = จำนวน caution edges
- (U_c) = จำนวนจุดที่ capacity ยังไม่ทราบ
- (B) = bottleneck spare capacity ต่ำสุดตลอดทาง (ยิ่งมากยิ่งดี)
- (U_d) = จำนวนช่วงที่ยังไม่รู้ระยะ
- (L) = ระยะทางรวมที่ประกาศ
- (H) = จำนวน hops

เลือก

[
P^{*}=argmin_{	ext{lex}}J(P)
]

ข้อดีคือไม่มีค่าน้ำหนัก 0.37/0.22/0.15 ที่สร้างขึ้นโดยไม่มี calibration  
ความปลอดภัยและ feasibility ถูกตัดสิน **ก่อน** ความสั้นของทาง

---

## 7. ความซ้ำซ้อน: อย่ามี safe node เดียว

ชุมชนควรพยายามประกาศ external safe node อย่างน้อยสอง node ที่ไม่พึ่ง failure เดียวกัน

เช่น ไม่ใช่:

[
E_1,E_2 	ext{ ที่ใช้สะพาน/ถนน/หม้อแปลงเดียวกันทั้งหมด}
]

แต่พยายามให้มีคนละทางออกหรือคนละ failure domain เมื่อสภาพพื้นที่อนุญาต

ตัวชี้วัดเชิงโครงสร้างที่ควรดูคือ:

[
R(v)=|{	ext{independent feasible exits from }v}|
]

แต่ `R(v)` เป็นเพียงจำนวนทางสำรองเชิงโครงสร้าง  
**ไม่ใช่ความน่าจะเป็นรอด**

---

## 8. เครื่องมือสังคม

### Request ticket

ใช้ข้อความสั้นรูปเดียวกันทั้งเครือข่าย:

```text
[เวลา][ZONE][REQUEST]
คนต้องย้าย: 2
ต้องช่วยเดิน/เคลื่อนย้าย: 1
ปลายทางที่ต้องการ: safe node ที่มีไฟฟ้า
ทางหน้าจุด: UNKNOWN
ติดต่อกลับ: ช่องทางภายในกลุ่ม
```

### Offer ticket

```text
[เวลา][ZONE][OFFER]
ผู้ช่วย: 2
รถ: 1
รับได้เพิ่ม: 3
พร้อมถึง: 20 นาที
ข้อจำกัด: ไม่เข้าพื้นที่น้ำลึก/ไฟฟ้าเสี่ยง
```

### Route check

```text
[เวลา][EDGE-ID]
สถานะ: OPEN / ASSISTED / BLOCKED / UNKNOWN
mode: walk / vehicle
safety: CLEAR / CAUTION / BLOCKED / UNKNOWN
ตรวจจาก: อยู่ ณ จุด / มองเห็น / แหล่งทางการ
```

---

## 9. Technology stack

ระบบควรทำงานได้แม้อินเทอร์เน็ตบางส่วนล่ม

### Online

- FloodConnect = shared situation + graph state
- LINE / WhatsApp = human communication
- GitHub = protocol/schema/audit trail
- QR/link = เปิดหน้า zone ของตัวเอง
- optional location sharing = เฉพาะเวลาจำเป็นและโดยความยินยอม

### Offline fallback

- แผนที่กระดาษแบ่ง zone/node/edge
- whiteboard หรือกระดาษสถานะ OPEN/BLOCKED
- phone tree
- วิทยุสื่อสารหากมี
- รายชื่อ “ช่องทางติดต่อ” ไม่จำเป็นต้องเป็นฐานข้อมูลบุคคลเต็มรูปแบบ

**ถ้าระบบดิจิทัลตาย DAG ทางสังคมยังต้องเดินต่อได้**

---

## 10. เชื่อมกับ FloodConnect เดิม

ข้อมูลเดิมเข้ามาช่วยเปลี่ยนสถานะ node/edge ได้ แต่ต้องไม่ข้าม epistemic boundary:

- ระดับน้ำคลอง/ปั๊ม/ฝน → contextual signal
- flood-road telemetry → supporting evidence ของ edge
- community report → local evidence
- canal/burden graph → ภาพโครงสร้างน้ำ
- social listening → สัญญาณพื้นที่ใกล้เคียง

ไม่มี source ใด source เดียวควรเปลี่ยน edge เป็น `OPEN` โดยอัตโนมัติ หากยังไม่มี evidence
ว่าคน/รถชนิดที่ประกาศใช้ผ่านช่วงนั้นได้จริง

---

## 11. ขั้นตอนทำให้กราฟ “มีชีวิต”

ไฟล์ `site/inputs/community/self_help_dag.yaml` ตั้งใจเริ่มจาก UNKNOWN

งานภาคสนามรอบแรก:

1. สร้าง household/buddy cells จริงโดยไม่ต้องเผยแพร่เลขบ้าน
2. กำหนด zone boundaries ที่คนในพื้นที่เข้าใจตรงกัน
3. สำรวจ internal-safe candidate
4. สำรวจ egress อย่างน้อย 2 ทางเมื่อทำได้
5. หา external-safe candidate หลายทิศ
6. ตรวจ capacity/services/accessibility
7. ตั้ง freshness window ของ node/edge
8. ซ้อมส่ง request/offer/route-check
9. ลองตัดอินเทอร์เน็ตแล้วดูว่า network ยังทำงานได้หรือไม่

เมื่อผ่านจึงเปลี่ยน:

```yaml
status: SAFE
fresh: true
verified_safe: true
```

หรือ edge:

```yaml
status: OPEN
safety: CLEAR
fresh: true
field_verified: true
```

---

## 12. หลักการสุดท้าย

FloodConnect community DAG ไม่ได้พยายามแทนรัฐหรือหน่วยกู้ภัย

มันแก้ช่องว่างก่อนหน่วยภายนอกมาถึง:

[
	ext{Self}
ightarrow
	ext{Buddy}
ightarrow
	ext{Zone}
ightarrow
	ext{Internal Safe}
ightarrow
	ext{Egress}
ightarrow
	ext{External Safe}
]

เป้าหมายคือให้ **แต่ละพื้นที่กลายเป็น node ที่รู้สถานะของตัวเอง รับ-ส่งความช่วยเหลือได้
และเชื่อมต่อไปยัง node ที่ปลอดภัยกว่าโดยไม่ต้องเดาเส้นทาง**.
