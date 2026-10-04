# เล่ม 13/16 — คู่มือการคำนวณปริมาณน้ำผ่านอาคารชลประทาน

> สถานะการ์ด: TRANSCRIBED (ถอดความจากภาพสแกน อ่านด้วยสายตาทีละหน้า — ไฟล์ PDF ไม่มีชั้นข้อความ, `pdftotext` ได้ผลว่าง)
> ทุกสมการในการ์ดนี้ = การถอดความ ไม่ใช่การตรวจสอบ — **ไม่มีสมการใดผ่าน Toledo แล้ว**

## บรรณานุกรม

| ฟิลด์ | ค่า |
|---|---|
| หน่วยงาน | กรมชลประทาน |
| ชุด | คู่มือการปฏิบัติงานด้านบริหารจัดการน้ำ — เล่มที่ 13/16 |
| ชื่อเล่ม | คู่มือการคำนวณปริมาณน้ำผ่านอาคารชลประทาน (ชื่อไฟล์ต้นทางสะกด "ขลประทาน") |
| หน่วยรับผิดชอบที่ระบุ | ฝ่ายจัดสรรน้ำและปรับปรุงระบบชลประทาน (ฝจน.คป./ฝจน.คบ.) ของโครงการชลประทาน/โครงการส่งน้ำและบำรุงรักษา (น. 13-2) |
| ปีพิมพ์ | ไม่พบปีพิมพ์ในเล่ม (เอกสารอ้างอิงล่าสุดในเล่มลงปี 2554 — น. 13-4) |
| ความยาว | 30 หน้า PDF; เลขหน้าที่พิมพ์ = "๑๓-N" (หน้า PDF = N+1) |
| สำเนาในเครื่อง | `raw/knowledge/rid_manuals/rid_vol13_discharge_structures.pdf` (gitignored) |

เอกสารอ้างอิงของเล่ม (น. 13-4, ระบุเฉพาะชื่อเรื่อง/หน่วยงาน): อภิธานศัพท์เทคนิคด้านการชลประทานและการระบายน้ำ (กรมชลประทาน 2551); คู่มือการใช้อาคารชลประทาน (ฝ่ายพัฒนาการใช้น้ำชลประทาน 2542); คู่มือการใช้อาคารชลประทานในแบบจำลองทางกายภาพของระบบคลองส่งน้ำ TCP/THA/310/CA (2553); การวัดน้ำชลประทาน (ม.เกษตรศาสตร์ 2533); อาคารชลศาสตร์ (ม.เกษตรศาสตร์ 2544).

## วัตถุประสงค์และขอบเขต (น. 13-1)

- เสนอแนะสูตรคำนวณปริมาณน้ำผ่านอาคารชลประทานที่ก่อสร้างแล้วเสร็จ ให้ถูกต้อง ใกล้ความจริง และไม่ยุ่งยาก เหมาะกับการปฏิบัติในสนาม
- ขอบเขต: อาคารบังคับน้ำปากคลองส่งน้ำ, อาคารในระบบชลประทาน, อาคารวัดน้ำ — ทั้งการไหลแบบอิสระ (Free Flow) และแบบจม (Submerged Flow)
- นิยามสำคัญ (น. 13-1): Free Flow = ระดับน้ำท้ายไม่มีอิทธิพลต่อการไหล; Submerged Flow = ระดับน้ำท้ายมีอิทธิพลต่อการไหล; C.H.O. Turnout นิยมตั้งความต่างระดับน้ำคงที่ 8 หรือ 10 ซม. (ในประเทศไทย)

## กระบวนการ (ผังกระบวนการ น. 13-2)

1. รวบรวมข้อมูลอาคารชลประทานและค่าตัวแปรทางชลศาสตร์ตามชนิดอาคาร เช่น ความยาวสันฝาย ความลึกน้ำเหนือสันฝาย สัมประสิทธิ์การไหล — 1 วัน (ฝจน.คป./ฝจน.คบ.)
2. เลือกสูตรให้ตรงกับ **ชนิดอาคาร + ลักษณะการไหล (อิสระ/จม)** แล้วแทนค่าตัวแปรเพื่อได้ปริมาณน้ำผ่านอาคาร — 1 วัน
3. วิเคราะห์ผลและสรุปรายงาน — 1 วัน

มาตรฐานงาน (น. 13-4): ใช้ค่าตัวแปรถูกต้อง; **ค่าสัมประสิทธิ์การไหลควรมาจากการสอบเทียบอาคาร** (โยงไปเล่ม 14); ใช้สูตรตรงชนิดอาคารและลักษณะการไหล.
ระบบติดตาม (น. 13-4): ติดตามการหาปริมาณน้ำผ่านอาคารเป็นรายสัปดาห์ รายงานผล สภาพปัญหา อุปสรรค.
แบบฟอร์มที่ใช้: "-" (ไม่มี).

## เครื่องมือ/อาคารที่กล่าวถึง

ปตร.ปากคลองส่งน้ำ (Main Head Regulator: บานตรง Slide Gate, บานโค้ง Radial/Tainter Gate) · อาคารท่อส่งน้ำเข้านา FTO (Sluice Gate, Baffled Distribution, Stop Log) · อาคารรับน้ำปากคู (บานเดี่ยวท่อสี่เหลี่ยม/ท่อกลม, C.H.O.) · อาคารน้ำตก (Vertical Drop, แบบพื้นเอียง, Pipe Drop) · อาคารทิ้งน้ำ Side Channel Spillway · ฝายวัดน้ำ (สี่เหลี่ยมไม่บีบข้าง/บีบข้าง, Cipolletti, V-notch 90°, ฝายทดน้ำ Ogee, Duck Bill, ฝายสันกว้าง) · รางวัดน้ำ (Parshall, Cutthroat). ระยะติดตั้งจุดวัดเฮดตามภาพ: ≥ 4H เหนือฝาย, ระยะข้าง ≥ 2H (ภาพ น. 13-21 ถึง 13-23).

## ข้อสังเกตทั่วไปเรื่องสัมประสิทธิ์

**เล่มนี้ไม่มีตารางค่าสัมประสิทธิ์** — ช่องค่า C/Cd/Cs ในหน้ารายละเอียดเป็นกล่องว่างให้กรอก. ค่าตัวเลขที่เล่มให้ไว้มีเพียง: Stop Log C = 1.5–2.2; ท่อรับน้ำปากคู C = 0.6–0.7; อาคารน้ำตก C แนะนำ 1.822; Side Channel Spillway 1.84; Parshall n1 = 1.522–1.600, n2 = 1.000–1.275, C2 = 0.0044; Cutthroat nf = 1.542–2.000, ns = 1.200–1.750. **Cs ของ Sluice Gate แบบจม "ขึ้นอยู่กับ H และ Go" แต่ไม่มีตาราง/กราฟในเล่ม** (น. 13-9).

g = 9.81 m/s² ทุกสูตร.

## การ์ดสมการ

รูปแบบ: `id` — ชื่อ — สูตร — สัญลักษณ์/หน่วย — เงื่อนไข — หน้า.
**ทุกการ์ด:** Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

### ก. ปตร.ปากคลองส่งน้ำ (Main Head Regulator)

**vol13-eq1** — Slide Gate, Free Flow (น. 13-3, 13-6)
$Q = C\,L\,h\,\sqrt{2 g y_1}$
C = สัมประสิทธิ์การไหล (ไม่มีค่าในเล่ม); L = ความกว้างทั้งหมดของบาน ปตร. [m]; h = ความสูงที่เปิดบาน [m]; y₁ = ความลึกน้ำหน้า ปตร. [m]; Q [m³/s]. เงื่อนไข: ระดับน้ำท้ายไม่มีอิทธิพล.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq2** — Slide Gate, Submerged Flow (น. 13-3, 13-6)
$Q = C\,A\,\sqrt{2 g h}$, $A = G_0 L$, $h = y_1 - h_s$
A = พื้นที่น้ำไหลผ่านบาน [m²]; G₀ = ความสูงที่เปิดบาน [m]; L = ความกว้างทั้งหมดของบาน [m]; h = ผลต่างความลึกเหนือน้ำ–ท้ายน้ำ [m]; h_s = ความลึกน้ำท้าย [m]; y₁ = ความลึกน้ำเหนือ ปตร. [m]; Q [m³/s]. เงื่อนไข: ระดับน้ำท้ายมีอิทธิพล. **หมายเหตุ: สัญลักษณ์ h ในสูตรนี้คือผลต่างระดับน้ำ ไม่ใช่ช่องเปิด (ต่างจาก eq1)**.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq3** — Radial/Tainter Gate, Free Flow (น. 13-3, 13-7)
$Q = C\,L\,h\,\sqrt{2 g y_1}$ — สัญลักษณ์เดียวกับ eq1; เพิ่ม r = รัศมีบานโค้ง [m] (ระบุในนิยาม แต่ไม่ปรากฏในสูตร).
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq4** — Radial/Tainter Gate, Submerged Flow (น. 13-3, 13-7)
$Q = C\,A\,\sqrt{2 g h}$, $A = G_0 L$, $h = y_1 - h_s$ — สัญลักษณ์เดียวกับ eq2.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

### ข. อาคารท่อส่งน้ำเข้านา (FTO)

**vol13-eq5** — Sluice Gate, Free Flow (น. 13-3, 13-8)
$Q = C_d\,L\,G_o\,\sqrt{2 g h}$, $h = Y - 0.60\,G_o$, $Y = U_s - \text{ระดับธรณีประตู}$
C_d = สัมประสิทธิ์การไหลแบบ Free Flow; G_o = ระยะเปิดบาน [m]; U_s = ระดับน้ำเหนือน้ำ [m รทก.]; D_s = ระดับน้ำท้ายน้ำ [m รทก.]; L = ความกว้างช่องเปิด [m]; Q [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq6** — Sluice Gate, Submerged Flow (น. 13-3, 13-9)
$Q = C_s\,L\,G_o\,\sqrt{2 g h}$, $h = U_s - D_s$, $H = D_s - \text{ระดับธรณีประตู}$
C_s = สัมประสิทธิ์การไหลแบบ Submerged **ซึ่งขึ้นอยู่กับ H และ G_o** (ไม่มีตารางในเล่ม); หน่วยอื่นเหมือน eq5.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq7** — Baffled Distribution, Free Flow (น. 13-3, 13-10) — สูตรและนิยามเหมือน eq5 ทุกตัว ($h = Y - 0.60G_o$).
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq8** — Baffled Distribution, Submerged Flow (น. 13-3, 13-11) — สูตรและนิยามเหมือน eq6.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq9** — Stop Log (น. 13-3, 13-12)
$Q = C\,L\,H^{3/2}$; C = 1.5–2.2; L = ความยาวสันฝายที่น้ำล้น [m]; H = ความลึกน้ำเหนือสันฝาย [m]; Q [m³/s]. ไม่แยก free/submerged.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

### ค. อาคารรับน้ำปากคู

**vol13-eq10** — บานเดี่ยว ท่อสี่เหลี่ยม (น. 13-3, 13-13)
$Q = C\,A\,\sqrt{2 g\,\Delta h}$, $A = G_0 W$; C = 0.6–0.7; G₀ = ระยะเปิดบาน [m]; W = ความกว้างช่องน้ำผ่าน [m]; Δh = ผลต่างระดับน้ำหน้า–ท้ายอาคาร [m] (y₁ = ระดับน้ำหน้าอาคาร, h_s = ระดับน้ำท้ายอาคาร); Q [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq11** — บานเดี่ยว ท่อกลม (น. 13-3, 13-14)
$Q = C\,A\,\sqrt{2 g h}$ (ตารางสรุปเขียน $\sqrt{2g\Delta h}$). พื้นที่ **ตามที่พิมพ์ในเล่ม**: $A = \dfrac{(360-\theta)}{360\pi R^2} + \dfrac{\sin\theta}{2R^2}$; $\theta = 2(90-\beta)$ [องศา]; $\beta = \sin^{-1}((G_0 - R)/R)$ [องศา]; π = 22/7; R = รัศมีภายในท่อ [m]; C = 0.6–0.7.
หมายเหตุผู้ถอด (INSTINCT): รูปพื้นที่ตามที่พิมพ์ดูเหมือนพิมพ์ตำแหน่ง πR² ผิด (มิติไม่เป็นพื้นที่) — ถอดตามต้นฉบับ ไม่แก้; ต้องตรวจกับแหล่งอ้างอิงก่อนใช้.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq12** — Constant Head Orifice (C.H.O.) (น. 13-3, 13-15)
$Q = C\,A\,\sqrt{2 g\,\Delta h}$, $A = W \times Y$; C = สัมประสิทธิ์ของ Orifice Gate (ไม่มีค่า); W = ความกว้างจริงของ Orifice Gate [m]; Y = ความสูงขอบล่างบานเหนือธรณี [m]; Δh = ความต่างระดับน้ำหน้า–ท้าย Orifice Gate **ทั่วไปใช้ 0.06 m** (น. 13-15; ขณะที่นิยาม น. 13-1 ว่านิยม 8 หรือ 10 ซม.); X₀ = ระยะเกลียวเหนือเพลา [m].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

### ง. อาคารน้ำตก / อาคารทิ้งน้ำ

**vol13-eq13** — Vertical Drop (น้ำผ่านกำแพง Wing Wall/Side Wall) (น. 13-3, 13-16)
$Q = C\,L\,(H + V_a^2/2g)^{3/2}$; C แนะนำ 1.822; L = ความยาวรวมของกำแพง [m]; V_a = ความเร็วเฉลี่ยเหนือน้ำ [m/s]; H = ความสูงน้ำที่ท่วม sidewalls [m]; Q [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq14** — อาคารน้ำตกแบบพื้นเอียง (Overflow Discharge) (น. 13-3, 13-17)
$Q = C\,L\,H^{3/2}$; C แนะนำ 1.822; L = ความยาวรวม sidewalls รวมความกว้างของ check [m]; H = ความสูงน้ำที่ท่วม sidewalls [m].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq15** — Pipe Drop Structure (น. 13-3, 13-18)
$Q = \tfrac{1}{4}\pi D^2 V$; D = เส้นผ่านศูนย์กลางท่อ [m]; V = ความเร็วน้ำกรณีไหลเต็มท่อ [m/s] ไม่เกิน V_max: ≤ 1.00 m/s (Earth Outlet Transition), ≤ 1.50 m/s (Concrete Outlet Transition).
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq16** — Side Channel Spillway (น. 13-3, 13-19)
$Q = 1.84\,L_C\,H^{3/2}$; L_C = ความยาว crest [m]; H = head เหนือ spillway crest [m]; Q [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

### จ. ฝายวัดน้ำ (หน่วยในสูตรเหล่านี้คือ **เซนติเมตร → ลิตร/วินาที** ตามที่ระบุ)

**vol13-eq17** — Suppressed Rectangular Weir ไม่คิดความเร็วก่อนถึงอาคาร (น. 13-3, 13-20)
$Q = 0.01838\,L\,H^{3/2}$; L = ความยาวสันฝาย [cm]; H = ความลึกน้ำเหนือสันฝาย [cm]; Q [L/s] (เล่มเว้นช่อง "หรือ ลบ.ม./วินาที" ให้แปลง).
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq18** — Suppressed Rectangular Weir คิดความเร็วก่อนถึงอาคาร (น. 13-3, 13-20)
$Q = 0.01838\,L\,[(H+h)^{3/2} - h^{3/2}]$, $h = V^2/2g$; V = ความเร็วเฉลี่ยกระแสน้ำหน้าฝาย [cm/s]; h = เฮดความเร็ว [cm]; หน่วยอื่นตาม eq17. (ตารางสรุป น. 13-3 พิมพ์โดยไม่มี L)
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq19** — Contracted Rectangular Weir ไม่คิดความเร็ว (น. 13-3, 13-21)
$Q = 0.01838\,H^{3/2}(L - 0.2H)$ [cm, L/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq20** — Contracted Rectangular Weir คิดความเร็ว (น. 13-3, 13-21)
ตารางสรุป น. 13-3: $Q = 0.01838\{(H+h)^{3/2} - h^{3/2}\}(L - 0.2H)$; หน้ารายละเอียด น. 13-21 พิมพ์: $Q = 0.01838\,L((H+h)^{3/2} - h^{1/2})(L - 0.2H)$, $h = V^2/2g$.
**ความไม่สอดคล้องภายในเล่ม** (เลขชี้กำลังของ h และการมี L ซ้ำ) — ถอดทั้งสองแบบ ห้ามเลือกเองก่อนตรวจแหล่งต้น.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq21** — Cipolletti/Trapezoidal Weir (ลาดข้าง 4:1 ตั้ง:ราบ) ไม่คิดความเร็ว (น. 13-3, 13-22)
$Q = 0.01859\,L\,H^{3/2}$ [cm, L/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq22** — Cipolletti คิดความเร็ว (น. 13-3, 13-22)
$Q = 0.01859\,L\,(H + 1.5h)^{3/2}$, $h = V^2/2g$ [cm, cm/s, L/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq23** — Triangular / 90° V-Notch Weir (น. 13-3, 13-23)
ตารางสรุป น. 13-3: $Q = 2.49\,H^{2.48}$ (อยู่ในคอลัมน์ ลิตร/วินาที); หน้ารายละเอียด น. 13-23: $Q = 0.0138\,H^{2.5}$, H = ความลึกน้ำเหนือสันฝาย [cm], Q [L/s].
**ความไม่สอดคล้องภายในเล่ม** (สัมประสิทธิ์/เลขชี้กำลัง/หน่วยของ H ไม่ระบุในตาราง) — ถอดทั้งสองแบบ.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq24** — ฝายทดน้ำ Ogee Crest ไม่มีการควบคุม (น. 13-3, 13-24)
$Q = 0.5522\,C\,L_e\,H_e^{3/2}$; C = สัมประสิทธิ์ ซึ่งแปรตามความสูงฝาย รูปร่างฝาย ลาดด้านหน้า และระดับน้ำท้ายฝาย (ไม่มีตาราง); L_e = ความยาวประสิทธิผลของ crest [m]; H_e = head ทั้งหมดบน crest รวม velocity head ทางเข้า h_a [m]; Q [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq25** — Duck Bill Weir (ฝายสันยาว/ฝายปากเป็ด) (น. 13-3, 13-25)
$Q = C_d\,L\,\sqrt{2g}\,H^{3/2}$; เงื่อนไขที่เล่มระบุ: **ใช้เมื่อความเร็วเฉลี่ยของกระแสน้ำหน้าฝายมากกว่า 0.30 m/s**; H = ความสูงน้ำไหลข้ามสันฝาย [m]; L = ความยาวสันฝาย [m]; Q [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq26** — ฝายสันกว้าง (Broad-crested) (น. 13-3, 13-26)
$Q = c_d\,[b_c y_c + z\,y_c^2]\,[2g(H_1 - y_c)]^{1/2}$; c_d = สัมประสิทธิ์ขึ้นกับ H₁ และ L; y_c = ความลึกน้ำที่หน้าตัดควบคุม/ความลึกวิกฤต [m]; b_c = ความกว้างสันฝาย/หน้าตัดควบคุม [m]; H₁ = ความลึกน้ำเหนือน้ำจากระดับธรณี [m]; z = สัดส่วนลาดเทของหน้าตัดฝาย; Q [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

### ฉ. รางวัดน้ำ

**vol13-eq27** — Parshall Flume, Free Flow (น. 13-3, 13-27)
$Q_f = C\,H_a^{\,n_1}$; H_a = head ทางผายเข้า [m]; C = dimension factor ขึ้นกับความกว้างคอ (throat); n₁ = 1.522–1.600; Q_f [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq28** — Parshall Flume, Submerged Flow (น. 13-3, 13-27)
$Q_s = \dfrac{C_1 (H_a - H_b)^{n_1}}{\left(-(\log S + C_2)\right)^{n_2}}$; H_b = head ที่ส่วนคอ [m]; S = H_b/H_a; C₁ = dimensional factor ขึ้นกับความกว้างคอ; C₂ = 0.0044; n₁ = 1.522–1.600; n₂ = 1.000–1.275; Q_s [m³/s].
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq29** — Cutthroat Flume, Free Flow (น. 13-3, 13-28)
$Q_f = C_f\,H_U^{\,n_f}$, $C_f = K_f\,W^{1.025}$; K_f = สัมประสิทธิ์ความยาว flume; W = ความกว้างคอ [m]; H_U = ความลึกน้ำทางผายเข้า [m]; n_f = 1.542–2.000 (ขึ้นกับความยาว L); เลือกขนาด flume ให้ **H_U/L ≤ 0.33**.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

**vol13-eq30** — Cutthroat Flume, Submerged Flow (น. 13-3, 13-29)
$Q_S = \dfrac{C_S (H_U - H_D)^{n_f}}{(-\log S)^{n_s}}$, $C_S = K_S W^{1.025}$; S = H_D/H_U (**ไม่เกิน 0.95**); H_D = ความลึกทางผายออก [m]; n_s = 1.200–1.750; เลือกขนาดให้ **H_U/L ≤ 0.40**.
Toledo: not yet looked up — do not use in a derivation until registered (PROP or CANONICAL)

## ข้อมูลที่ต้องใช้ (ตามเล่ม)

ขนาดอาคาร (ความกว้างบาน/ช่องเปิด L หรือ W, ความยาวสันฝาย, เส้นผ่านศูนย์กลางท่อ), ระยะเปิดบาน G_o, ระดับธรณีประตู (sill) [m รทก.], ระดับน้ำเหนือ/ท้ายอาคาร [m รทก.], ความเร็วน้ำหน้าอาคาร (กรณีคิด approach velocity), และสัมประสิทธิ์การไหล — ซึ่ง **ควรได้จากการสอบเทียบอาคาร** (น. 13-4).

## ข้อจำกัดที่เล่มระบุ/ที่พบจากการถอด

- เล่มไม่ให้ตารางสัมประสิทธิ์สำหรับ C/Cd/Cs ของบาน ปตร. และ Sluice Gate (กล่องว่าง) — ผู้ใช้ต้องหาจากการสอบเทียบ (เล่ม 14).
- ไม่มีเกณฑ์เชิงตัวเลขในการตัดสิน free vs submerged (ยกเว้น Cutthroat S ≤ 0.95) — มีเพียงนิยามเชิงคุณภาพ (น. 13-1).
- ความไม่สอดคล้องภายในเล่ม 3 จุด: eq11 (สูตรพื้นที่ท่อกลม), eq20 (เลขชี้กำลัง h), eq23 (V-notch).
- สัญลักษณ์ h ถูกใช้หลายความหมาย (ช่องเปิดบาน / ผลต่างระดับน้ำ / เฮดความเร็ว) ตามแต่ละสูตร.

## สิ่งที่ FloodConnect จะใช้ได้ (INSTINCT, ≤5)

- vol13-eq2/eq4/eq6 (submerged) คือช่องทางแปลง "ส่วนต่างระดับน้ำหน้า–ท้าย" ในบัญชีภาระ (burden ledger) ที่ ปตร.มีนบุรี ให้เป็นอัตราการไหล **ถ้า** รู้: ความกว้างบานรวม L และจำนวนช่อง, ระยะเปิดบาน G_o ณ เวลาเดียวกับระดับน้ำ, ระดับธรณีประตู (เพื่อหา H และตัดสิน free/submerged), และค่า C_s ที่สอบเทียบแล้วของบานนั้น — **ทั้ง 4 อย่างนี้เรายังไม่มี**.
- ถ้าบานเปิดพ้นน้ำทั้งหมด/ไม่มีบาน สูตรกลุ่มฝาย (eq16, eq24) ใช้ไม่ได้ตรงๆ เพราะ ปตร. ไม่ใช่ฝาย — ต้องรู้ชนิดอาคารจริงของมีนบุรีก่อน (ยังไม่ยืนยัน).
- ถึงมีสูตร ผลลัพธ์จะเป็นช่วง (เพราะ C ไม่รู้) ไม่ใช่ค่าเดียว — ถ้าจะแสดงบนหน้าเว็บต้องแสดงเป็นช่วงและติด OPEN.
- ทั้งหมดต้องผ่าน Toledo (PROP-FLOOD-xx) ก่อนเขียนโค้ดคำนวณใดๆ.
