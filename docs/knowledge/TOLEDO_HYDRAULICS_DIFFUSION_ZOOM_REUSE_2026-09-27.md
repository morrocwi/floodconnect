# Toledo-first reuse: สมการการแพร่ · ชลศาสตร์ · การ zoom สำหรับ FloodConnect (2026-09-27)

**คำสั่งฟาวน์เดอร์ (คำต่อคำ)**: "เปิด Toledo หาสมการการแพร่และชลศาสตร์ใน readout genesis ของเรามาเสริมสมการให้แข็งแกร่ง" + "รวมทั้งสมการการ zoom"

**สถานะไฟล์**: การ์ด lookup/reuse (read-only ต่อ registry) — ไม่แก้ registry, ไม่แก้โค้ด, ไม่ commit.
ทุกรหัสด้านล่าง **อ่าน statement เต็มแล้ว** จาก `registry/CANONICAL.json` (1,344 รายการ) และยืนยัน verdict ด้วย
`toledo_mcp.cli show <code>` (MEASURED: ทุกรหัสที่อ้างเป็น parent ได้ `REGISTERED_CURRENT usable=true` ยกเว้นที่ระบุเป็นอื่น).
ความสมมูลที่ยอมรับ = **renaming / positive scale / constant substitution เท่านั้น**; keyword hit ที่อ่านแล้วไม่ตรง = NOT A MATCH.
ทุกบรรทัดที่ไม่มี parent ที่ขึ้นทะเบียน = **NEW DERIVATION / PROPOSAL — not yet in Toledo** (ห้ามใช้ในโค้ด/หน้าเว็บจนกว่าจะขึ้นทะเบียน).

Tag: `VERIFIED` ตรวจเองในงานนี้ · `MEASURED` ผลที่รัน/เห็นเอง · `INSTINCT` การตีความ · `OPEN` ยังไม่ปิด · `RELAYED` ยกมาจากแหล่งอื่น.

---

## 0. Lens note (Step 0 — 3 บรรทัด)

1. สิ่งที่ "อ่านได้จริง" คืนนี้ = ระดับน้ำรายสถานีเป็นค่า ℚ ที่ tick จำกัด (cadence ≈ 25 นาที), สถานะประตูบางส่วน, ช่วง (interval) ที่ประกาศ — **ไม่มี** ปริมาณการไหล (flow telemetry 0) และ **ไม่มี** stage–storage ⇒ ขนาดการไหลเป็น non-readout ในตอนนี้ ไม่ใช่ตัวเลขที่รอคำนวณ.
2. ของที่ค้นมี 3 ชนิดที่ห้ามปน: object ที่ขึ้นทะเบียน (Th_coqc/Definition/untagged), proposal (PROP-FLOOD-xx, Dr, unverified), heuristic คัดกรอง — ป้ายของ claim ต้องไม่แรงกว่าชนิดของมัน.
3. ความละเอียดคือกราฟจำกัด + tick จำนวนเต็ม + ε-resolution; object ที่เขียนด้วย `dt`, `∇`, `√`, Laplace–Beltrami, `h→0` ถูกปฏิเสธเป็น parent (non-readout I1/I2) แม้ชื่อจะตรง.

(ชนิดปัญหาตั้งชื่อหลังโน้ต: equation-reuse lookup, route `toledo`, gate TG-RFG-01.)

---

## 1. สรุปสั้น (≤ 10 บรรทัด)

- **การแพร่ (A)**: parent หลักมีจริงและแข็ง — `weld/M.01.v1` (δ_R ⊢ L_R, Th_coqc), `weld/S.22.v1` (stepper), `Keystone/M.02–M.08.v1` (พลังงานผลต่างระดับ + relaxation ไม่เพิ่ม), `weld/M.43.v1` + `L_R/M.22.v1` (ker L_R = ค่าคงที่ ⇒ สมดุลคือน้ำราบ), `R/M.14.v1` (หางการลดลงแบบเรขาคณิต — ใช้กับ recession แสนแสบได้ทันที), min-plus `Z/M.21.v1`/`A2/M.07.v1` (เวลาเดินทางตามเส้นทาง).
- **ชลศาสตร์ (B)**: ไม่มีสมการ weir/orifice/Manning ใน Toledo (Bernoulli `EQ-015/P.60.v1` มีแต่ชื่อ) ⇒ ห้ามใช้; ที่ใช้ได้คือ clamp `A2/M.24.v1`, bottleneck `Z/M.23.v1`, admissibility `EQ-001/C.04.v1`, และ **sign soundness `D/M.71–D/M.76.v1`** ซึ่งเป็น parent ที่ PROP-FLOOD-01/04 ยังไม่ได้อ้าง.
- **Zoom (C)**: กฎ one-way + ป้าย 3 สถานะ = **ประกอบจาก object ที่ขึ้นทะเบียนแล้ว** (`weld/E.08.v1`, `EQ-002/M.01.v1`, `weld/E.07.v1`, `EQ-001/C.07.v1`, `D/M.71–77.v1`, `D/M.79–80.v1`); delta จริงมี **1 ชิ้น**: monotone endpoint enclosure (+ เงื่อนไข nested box).
- **PROP-FLOOD-09**: 4 ใน 5 ข้อเป็น composition; delta จริงเหลือ **ข้อเดียว** — edge coupling identity พร้อม delay จำนวนเต็ม. 09 **ไม่ได้ให้ขนาดการไหล**; ขนาดจากผลต่างระดับเป็น regime-instance ของ L_R (ค่า w_e OPEN) ส่วนรูปอิ่มตัว/สลับประตูเป็น delta แยก.
- **08 vs 09 vs zoom**: ไม่เป็น twin ถ้า (ก) point-depth ของ zoom อ้าง E_k ของ 08 โดย renaming แทนการตั้งใหม่ และ (ข) enclosure lemma ขึ้นทะเบียนครั้งเดียวให้ทั้ง 08 §4.4 และ zoom ใช้ร่วม.

---

## 2. Family A — การแพร่/การส่งต่อบนกราฟจำกัด

เป้าหมาย: ขนาดการไหลบน edge จากผลต่างระดับ (04 ให้ทิศเท่านั้น), recession front แสนแสบคืนนี้ (SSB.01/03 ลด ขณะ 07/09/12 นิ่ง), lag หนองจอก→พระโขนง, outfall ที่ถูกน้ำขึ้นล็อก.

| code | statement (ยกคำต่อคำ) | Genesis gate/section | tier · Coq | mapping → FloodConnect | verdict |
|---|---|---|---|---|---|
| `weld/M.01.v1` | "δ_R = (a ♯ b) ⊢[Th_coqc] L_R = D_W − W ⊢[Dr] F (MQ.08 stepper); concretely S_{n+1}=F(S_n,u_n,c_n,T_n) …" | THE ONE-LINE MASTER EQUATION; II.1 MQ.08 Discrete Stepper | Th_coqc (เฉพาะ δ_R⊢L_R; stepper = Dr) · closed `weld__M_01_v1.v` | L_R บนกราฟคลอง: node = สถานี/บึง, `w_e ≥ 0` = conductance ที่ประกาศ; `(L_R h)_u = Σ_v w_uv (h_u − h_v)` คือผลรวม "แรงขับจากผลต่างระดับ" ที่โหนด u (renaming X→h) | **REUSE-AS-PARENT** (โครงสร้าง operator) |
| `weld/S.22.v1` | "LR = DW − W (forced Laplacian); A := LR + Γ; s[n+1] = s[n] + dt(−A s[n] + J)" | II.1 | Definition · closed | `s` := ระดับ, `J` := ฝนเข้า/ inflow ที่ประกาศ, `Γ` := การสูบออกสู่ขอบเขต; **ใช้ได้เฉพาะ regime** ประตู OPEN / ไม่อิ่มตัว / ไหลด้วยแรงโน้มถ่วง และพื้นที่ผิวน้ำต่อโหนดเท่ากัน (positive scale ตัวเดียว) | **REUSE-AS-PARENT (regime-restricted)** + **DELTA**: น้ำหนักพื้นที่ต่อโหนด `diag(1/a_b)` (capacity matrix) ไม่ใช่ positive scale ตัวเดียว; การอิ่มตัว/สลับประตูไม่อยู่ใน S.22 — §2.2 ของเอกสาร method ตัดสินว่า "DRIFT" ถูกต้องสำหรับ *กฎทั้งก้อน* แต่ *ภายใน regime* เป็น instance จริง |
| `Keystone/M.02.v1`, `Keystone/M.03.v1` | "Lemma keystone_edge : forall phi e, B_edge phi e == I_edge phi e." / "B_form phi g == I_form phi g" (I_edge = w·(φ_i−φ_j)²) | Operator-first (Dirichlet energy = retained information) | Th_coqc · closed | `I(h) = Σ_e w_e (h_u − h_v)²` = "พลังงานผลต่างระดับ" ของทั้งสาย — ตัวชี้วัดเดียวว่าสายยังไม่ราบ | **REUSE-AS-PARENT** |
| `Keystone/M.08.v1` | "relaxation_dissipation : 0 < tau -> (weights ≥ 0) -> − ((2 # 1) / tau) * B_form phi g <= 0" | Face 4 Stability/Energy | Th_coqc · closed | recession ที่ไม่มีฝน/ไม่มี inflow: อัตราการเปลี่ยนของพลังงานผลต่างระดับไม่เป็นบวก | **REUSE-AS-PARENT** (เป็น *เครื่องหมายของอัตรา*; ขั้นแบบ tick ต้องผ่านเงื่อนไขขนาด τ ด้านล่าง) |
| `weld/M.42.v1` (+ `q_formal/M.14.v1` CFL, untagged) | "x^T L x ≤ 2 d_max ‖x‖² ⇒ 0 ≤ λ ≤ 2 d_max" | II.1 (CFL เป็น finite_diagnostic) | Th_coqc · closed | ประตูตรวจ τ ก่อนเดิน stepper: `d_max` = ผลรวม w สูงสุดต่อโหนด | **REUSE** (ceiling) + **DELTA เล็ก**: corollary "τ·2·d_max ≤ 2 ⇒ ขั้นไม่ขยาย" ยังไม่ขึ้นทะเบียน (Genesis II.1 เองบอกว่าเงื่อนไขเป็น *sufficient* ไม่ใช่ necessary) |
| `weld/M.43.v1` + `L_R/M.22.v1` | "Graph connected ⇒ ker(L_R) ⊆ {constant vectors} (λ_2>0)" / "Sum n (fun j => Lap i j * 1) == 0" | Operator-first; turbulence ledger ker(L_R)=constants | Th_coqc · closed | contrapositive: ถ้าช่วงสายไม่มี source/sink และ edge เปิดจริง สภาวะนิ่งต้อง "ราบ"; **นิ่งแต่ยังมีผลต่างระดับ > ε** ⇒ มี edge ถูกตัด (ประตูปิด/อุดตัน) หรือมี source/ปั๊ม — เป็นเหตุผลทางคณิตให้ F3 (07) และ 05a | **REUSE-AS-PARENT**. คืนนี้ (INSTINCT): SSB.12 1.22 / SSB.10 1.01 / SSB.09 0.94 / SSB.07 0.40 นิ่งทั้งหมดแต่ต่างระดับชัด และ SSB.10, SSB.09 **เป็นประตูระบายน้ำ** ⇒ สอดคล้องกับ "ถูกตัดเป็นช่วง ๆ ด้วยประตู" มากกว่า "การแพร่ยังไม่ถึง" — ต้องยืนยันด้วย `gate_opening_m` |
| `EQ-001/C.07.v1` | "A quotient fixed point can hide source-state cycles or currents; therefore fixed quotient readout alone establishes only observational stationarity." | V-A A.13 / Face 10 | untagged · closed | **FLAT ≠ ไม่มีการไหล**: ระดับนิ่งที่สถานีเกิดได้ขณะน้ำไหลผ่านคงที่ | **REUSE-AS-PARENT** (คำเตือนให้ 01/07) |
| `R/M.14.v1` | "geom_majorant_tail : (∀k, 0 <= t k) -> (∀k, t (S k) <= rho * t k) -> ∀ M N, (1 - rho) * tailsum t N M <= t N" | Face 2 Decay/Impermanence | Th_coqc · closed | recession แสนแสบ: `t_k := h(k) − h(k+1)` (ระดับที่ลดต่อ tick, ≥ 0 ในช่วง FALLING); ถ้า **วัด** ได้ ρ < 1 ที่ครอบทุก tick ⇒ ระดับที่จะลดต่อทั้งหมด ≤ `t_N/(1−ρ)` = "พื้นล่างของการลด" (ขอบเขต ไม่ใช่พยากรณ์) | **REUSE-AS-PARENT** (ใช้ได้ทันทีกับ SSB.01/03/04 เมื่อมี ≥ 3 tick FALLING ต่อเนื่อง; ρ เป็น MEASURED envelope ที่หักล้างได้ — tick ใดเกิน ρ ⇒ ถอน) — `R/M.32.v1` คือรูปมีเครื่องหมาย |
| `R/M.09.v1`, `A2/M.03.v1` | "FTCC_exact : agg f N == f N - f 0" / "ftcc_Z : fold Z.add 0 (zdelta f) N = f N - f 0" | discrete FTC (IDM) | Th_coqc · closed | ผลรวมผลต่างระดับตามสาย telescopes = ระดับหัวสาย − ท้ายสาย; ผลรวม lag ต่อ edge = lag ทั้งเส้นทาง | **REUSE-AS-PARENT** |
| `MQ08-stepper/M.01.v1` | "discrete causal derivative on edge e of a causal-delay graph: CC f(e) := (f(head(e))-f(tail(e)))/delay(e); … sum over a causal path of CC f * delay = f(end)-f(start)" | II.1 | Theorem-as-sourced · open_prop · **REGISTERED_UNVERIFIED** | กราฟที่ทุก edge มี `delay(e) = τ_e`: "ความชันต่อเวลาเดินทาง" บน edge; path-sum ใช้กับหนองจอก→พระโขนง | **REUSE-AS-PARENT (ต้องแจ้ง caveat unverified ทุกครั้งที่อ้าง)** |
| `Z/M.21.v1`, `Z/M.12–14.v1`, `A2/M.07.v1`, `A2/M.24–25.v1` | "minplus_distrib : tadd a (tmin b c) = tmin (tadd a b) (tadd a c)" / "path_is_fold : path_accum v0 f N = fold Z.min v0 f N" / "relax_nonincreasing : Z.min d cand <= d" | discrete semiring (IDM_Tropical) | Th_coqc · closed (บน ℤ) | lag หนองจอก→พระโขนง = `min` over เส้นทาง ของ `Σ d_e` (d_e เป็น tick จำนวนเต็ม — ตรงกับ ℤ พอดี) = เวลาถึงที่เร็วที่สุด (ขอบล่าง) | **REUSE-AS-PARENT** (ค่า d_e ทุก edge ยัง OPEN; คืนนี้มีแค่ขอบล่าง `lag(SSB.03→SSB.07) ≥ 6 h`, MEASURED ตามเอกสาร method §3.1) |
| `EQ-001/P.35.v1`, `EQ-001/P.36.v1`, `EQ-001/P.61.v1` | "…telegraph process with finite front speed v=√(D/τ_c)…" / "The finite front speed bounds a causal cone \|x\|≤v·t." / "The graph front-speed v is declared (not derived) as playing the role a measured propagation speed would play…" | II.2; Face 5 | untagged · definition / definition / not_formalisable | กติกาความซื่อสัตย์ของ τ_e: **ประกาศหรือวัด ไม่ derive จากมิติคลอง**; recession-front estimator ของ method §3 เป็น instance | **REUSE-AS-PARENT** สำหรับ P.36 (โครงสร้าง cone) และ P.61 (สถานะของความเร็ว); สูตร `√(D/τ_c)` เอง **ไม่ใช้** (√ = I1) |
| `weld/S.12.v1`, `weld/P.05.v1` | "τ ∂t j + j = −D∇s" / "τ_R dI_R/dt + L_R I_R = S_R + η_R" | II.2, II.8 (Layer 2 RTPE) | Definition · not_formalisable / Definition · open_prop, **REGISTERED_UNVERIFIED** | "ความเฉื่อย" ของการไหล (น้ำยังไหลต่อหลังผลต่างระดับกลับทิศ) | **NOT A MATCH (ตามที่เขียน)** — สัญลักษณ์ต่อเนื่อง ∂t/∇; รูป discrete ต่อ node มีใน II.1 (M.01 stepper, Dr) แต่ **flux-with-memory ต่อ edge = DELTA** และไม่มีข้อมูล flow ให้ calibrate ⇒ อย่าเปิดตอนนี้ |
| `L_R/M.27.v1`, `L_R/M.28.v1` | "diag_inertia_additive …" / "schur_pivots_are_boundary_and_complement …" | — | Th_coqc · closed | — | **NOT A MATCH** — "inertia" ที่นี่คือ Sylvester inertia (นับ pivot ติดลบ) ไม่ใช่ความเฉื่อยของน้ำ (กับดัก keyword); M.28 เป็นกรณี 2×2 ไม่พอรองรับ Kron reduction |
| `CMC/P.06.v1`, `CMC/P.10.v1` | "cattaneo_telegraph_closure_witness …" / "flux_limited_diffusion_closure_witness …" | CMC root | Th_coqc · closed | — | **NOT A MATCH** เป็น parent เชิงสมการ — พิสูจน์ว่า *คลาส* certified readout มีรูป closure ไม่ได้ให้สูตร flux จำกัด |
| `q_formal/M.10.v1`, `BiologyDomain_living_unit/B.14.v1`, `ChemDomain_ledger/C.42.v1` | "Graph Laplacian → Laplace–Beltrami convergence" / "Fick's first law rate = D A (dC/dx)" / "Stokes-Einstein D = kB T/(6 pi eta r)" | — | untagged / Definition | — | **NOT A MATCH** — limit ต่อเนื่อง (I2) หรือการแพร่ระดับโมเลกุล ไม่ใช่การส่งต่อบนเครือข่ายคลอง |
| `EQ-001/C.01.v1` | "If the declared closed boundary preserves ledger L(n)=A n, then A(n1-n0)=0." | VI-A B.2a generic conservation ledger [Dr] | untagged · closed | ความเข้ากันได้ของ 03/09 (ใช้อยู่แล้ว) | **REUSE** (compatibility, ไม่ใช่สูตรไหล) |

### 2.1 เป้าหมาย "ขนาดการไหลบน edge จากผลต่างระดับ" — คำตัดสิน

- **Toledo check** (MEASURED): `Q_e(k) = w_e·(h_u(k) − h_v(k))` → `NOT_REGISTERED`; `Q_e = min(cap_e, w_e·(h_u − h_v))` → `NOT_REGISTERED`.
- แต่ **รูปเชิงเส้น** คือพจน์ off-diagonal ของ `L_R` ใน `weld/M.01.v1`/`weld/S.22.v1` ตรงตัว (renaming X→h, W→w_e) ⇒ ใช้เป็น **regime-instance** ได้โดยไม่ต้องขึ้นทะเบียนใหม่ **ถ้า** (a) ประตู OPEN, (b) ไม่อิ่มตัว, (c) `w_e` ประกาศพร้อมแหล่ง. ปัญหาคือ `w_e` ทุก edge = **OPEN** (ไม่มี flow telemetry ให้ calibrate) และความเป็นเชิงเส้นของ Q ต่อ Δh เป็น *ทางเลือกของโมเดล* (INSTINCT: การไหลในคลองเปิดจริงไม่เชิงเส้น).
- รูป **อิ่มตัว + สลับประตู** `Q_e = g_e(k)·min(cap_e, w_e·Δh_e)` = **DELTA** (องค์ประกอบมี parent: `A2/M.24.v1` clamp, gate state จาก 05a/07, `EQ-001/C.04.v1` admissibility — แต่การประกอบนี้ไม่ได้ขึ้นทะเบียน).
- เส้นทางที่ไม่ต้องเดา `w_e`: จัดรูป 03 หา `Q_e` เป็นเศษเหลือที่โหนดซึ่งพจน์อื่นวัดครบ (rearrangement ของ 03 — REUSE) — ติดที่ stage–storage 0/57 (TODO #74 เดิม).
- **ข้อสรุป**: คืนนี้ขนาดการไหล = **REFUSED (w_e / cap_e / stage–storage ไม่ประกาศ)** — ไม่ใช่ความล้มเหลวของสมการ.

### 2.2 outfall ที่ถูกน้ำขึ้นล็อก (tide-locked) เป็นขอบเขต

- **REUSE ตรงตัว**: statement ของ PROP-FLOOD-03 ระบุเองว่า `gate_flag(k)` "a declared readout (e.g. BMA gate status or **tide-lock condition**)" และ `Q_out := 0` เมื่อ CLOSED (constant substitution) — ไม่ต้องมีสมการใหม่.
- ระดับแม่น้ำ/น้ำทะเลเป็น **boundary data ที่วัด ไม่ใช่ที่แก้หา** — Genesis Face 12 ("Numbers are measured, not derived from zero") + `q_formal/M.26.v1` (pinned/Dirichlet path-graph Laplacian; untagged, wrapped_related, statement มีแต่ชื่อ ⇒ อ้างเป็น *แนวคิด* ของโหนดตรึงค่า ไม่ใช่สูตร).
- การลดทอนความจุเมื่อน้ำนอกสูง = `g_U(t)` ของ PROP-FLOOD-06 (DERATING_UNDECLARED เมื่อไม่ประกาศ) — REUSE.

---

## 3. Family B — ชลศาสตร์ (storage–outflow, head–discharge, junction, capacity, monotone)

| code | statement (ยกคำต่อคำ) | Genesis gate/section | tier · Coq | mapping → PROP-FLOOD-03/05/06 | verdict |
|---|---|---|---|---|---|
| PROP-FLOOD-03 (proposal) | "S_b(k+1) := S_b(k) + P(k)·A_b·c_b + Q_in(k)·τ − Q_out(k)·τ … Q_out := 0 if CLOSED, min(Q_out,meas, C_pump,b) if OPEN" | VI-A B.2a | Dr · unverified | storage–outflow และ junction (โหนด S ≡ 0) | **REUSE** (มีอยู่แล้ว) |
| `A2/M.24.v1`, `A2/M.25.v1` | "Z.min d cand <= d" / "Z.min (Z.min d cand) cand = Z.min d cand" | IDM reduction | Th_coqc · closed (ℤ) | flux ≤ ความจุ: clamp `min(Q, C)` ของ 03 ไม่เพิ่มค่าและทำซ้ำไม่เปลี่ยน ⇒ ตรวจซ้ำได้ปลอดภัย (ℚ → ℤ ด้วย positive scale บนกริด resolution ที่ประกาศ) | **REUSE-AS-PARENT** (เพิ่มเป็น parent ของกฎ Q_out ใน 03/09(ii)) |
| `Z/M.23.v1` + `Z/M.15–17.v1` | "bottleneck_distrib : tmin a (tmax b c) = tmax (tmin a b) (tmin a c)" | IDM_Tropical | Th_coqc · closed (ℤ) | ความจุของ *เส้นทาง* = min ของ cap_e; เส้นทางขนานที่ดีที่สุด = max (widest path) → "คอขวด" ของสายตะวันออก | **REUSE-AS-PARENT** — caveat: นี่คือ widest *single* path; max-flow/min-cut ของเครือข่าย **ไม่อยู่ใน Toledo** |
| `A2/M.26.v1` | "weak_duality_2 : … c1 <= y * a1 -> c2 <= y * a2 -> …" | — | Th_coqc | — | **NOT A MATCH** เกิน 2 ตัวแปร (LP ของเล่น ไม่ใช่ min-cut ของเครือข่าย) |
| `EQ-001/C.04.v1` | "Admitted coordinates satisfy n0+N xi ≥ 0 and all declared capacity/boundary inequalities." | V-A A.13 Gate 2 | untagged · open_prop | `|Q_e| ≤ cap_e` เป็น **ประตู admissibility** ไม่ใช่กฎเลขคณิต; ไม่ประกาศ cap ⇒ ⊥ (CAPACITY_UNDECLARED) | **REUSE-AS-PARENT** ของ 09(ii) |
| `D/M.71.v1`–`D/M.76.v1` | "classify_bot_iff : classify floor v = Sbot <-> (~ floor == 0 /\ - floor <= v /\ v <= floor)"; "classify_plus_sound : … classify floor v = Sp -> 0 < v"; "classify_minus_sound : … = Sm -> v < 0" | Face 10 Record/Readout; A.13 Gate 2 (1/0/⊥) | Th_coqc · closed | `floor := ε`, `v := Δ_k(t)` (01) หรือ `Δ_e(t)` (04): Sp/Sm/⊥ = RISING/FALLING/(FLAT หรือ UNRESOLVED) — **เครื่องหมายที่อ่านได้ไม่เคยโกหก** | **REUSE-AS-PARENT** — 01 และ 04 ตอนนี้อ้างแค่ `delta_R`; ควรเพิ่มรหัสนี้เป็น parent. ข้อสังเกต: ที่ ε > 0 แถบกลางคือ ⊥ (เครื่องมือแยกไม่ได้) ไม่ใช่ Sz (ราบจริง) — ป้าย "FLAT" ของ 01 ควรมีหมายเหตุว่าเป็น ⊥ |
| `R/M.30.v1`, `R/M.25.v1`, `Z/M.22.v1` | "Qmult_le_l_nonneg : 0 <= c -> a <= b -> c * a <= c * b" / "mono_step …" / "maxplus_distrib : tadd a (tmax b c) = tmax (tadd a b) (tadd a c)" | IDM certified arithmetic | Th_coqc · closed | ความเป็น monotone ของ P·A·c (ทุกพจน์ ≥ 0) และของ max(0, ·) — อิฐก้อนเล็กของ "monotone response" | **REUSE-AS-PARENT** (อิฐ); ตัว lemma enclosure ทั้งก้อน = DELTA (§4) |
| `EQ-015/P.60.v1` | "Bernoulli's equation (steady incompressible streamline energy balance)" | — | untagged · wrapped_related | สูตร weir `Q = C b H^{3/2}` / orifice `Q = C A √(2gΔh)` | **NOT A MATCH** — registry มีแต่ชื่อ ไม่มี statement ให้ reuse; สูตรต้องใช้ √ และ g (I1, non-readout) ⇒ ห้ามใช้; ถ้าจำเป็นในอนาคต = rating ที่เป็น **ตารางจำกัด monotone ที่หน่วยงานประกาศ** (DELTA, ต้องขึ้นทะเบียน) |
| pump curve | — | — | — | 06 นับ `P_run,p` rated ของปั๊มที่วิ่ง; 03 ใช้ `C_pump,b` | ไม่มีสมการใหม่ — **REUSE 03/06** |
| `Theta/P.05.v1` | "fixed_point_balance_law : (p0*p0*p0*s0 + p1*p1*p1*s1 + p2*p2*p2*s2 == 0)%Q." | Theta programme | Th_coqc | — | **NOT A MATCH** (สมดุลกำลังสามเฉพาะโปรแกรม Θ; keyword "balance") |
| `A.8/M.15.v1`, `A.8/M.08.v1` | "…MissingResource=>ProjectHold…" / "Λ=min(μ_L,…)…" | — | finite_diagnostic | — | **NOT A MATCH** (ความจุพอร์ตวิจัย/คอขวดเชิงสถาบัน) |
| `A.5/S.07.v1` | "C_{t+1} = G(x_t, C_t)" | — | Definition | toledo check ให้ `CANDIDATE_MATCH` กับ `D_{t+1} = max(0, D_t + P_t − C_t)` (MEASURED) | **NOT A MATCH** — รูปทั่วไปเกิน (structural only); recursion หนี้เป็น heuristic คัดกรองตาม 08 |
| `weld/S.01.v1` | (ต้นทางของ S.22) | — | `REGISTERED_SPLIT`, usable=false | — | **ห้ามอ้าง** — ใช้ `weld/S.22.v1` แทน |

### 3.1 แมปเข้า D_H, R_H, C_H ของ PROP-FLOOD-06 (ไม่แก้ statement ของ 06)

- `R_H = Σ_o max(0, Q_cap,o − Q_o,now)·H·3600` → `max(0, ·)` คือ positive part บน max-plus (`Z/M.15–17.v1`, `Z/M.22.v1`) — เพิ่มเป็น parent เชิงพีชคณิตได้ (occurrence ไม่ใช่ twin).
- `binding(U) := argmin(R_H, D_H)` → `tmin` (`Z/M.12–14.v1`); คอขวดตามเส้นทางขึ้นสู่ outlet → `Z/M.23.v1`.
- `D_H` ที่ใช้เฉพาะปั๊มที่วิ่ง และ `g_U(t)` → คงเดิม; clamp ต่อปั๊ม → `A2/M.24.v1`.
- `C_H` case (e) DESIGN_DECLARED → เป็นเรื่องของ 08 §4.1 ไม่ใช่ของไฟล์นี้.

---

## 4. Family C — Zoom / หลายสเกล (Urban → Zone/Node → Point)

สิ่งที่ตรวจ: paste ภายนอก "Hierarchical Flood Zoom" + โค้ด `hierarchical_flood_zoom.py` (อยู่นอกคลังนี้, ยังไม่ merge) และการ์ดรีวิว `card_thirdparty_urban_event_layer_and_zoom_2026-09-27.md` (ตรวจแล้ว: interval arithmetic ถูก 3 ฟังก์ชัน, tests 5/5 — RELAYED จากการ์ดนั้น).

| code | statement (ยกคำต่อคำ) | Genesis gate/section | tier · Coq | mapping → zoom | verdict |
|---|---|---|---|---|---|
| `weld/E.08.v1` | "K_local=K\|_{Ω_local}; T^Y_{ij}∘K_i ≅ K_j∘T^C_{ij}, ε_bridge=d(T^Y_{ij}∘K_i, K_j∘T^C_{ij}); Ω(K)={…: all required gates pass}" | IV.5 Commuting-Square Bridge Criterion | Definition · closed | กฎ one-way: ข้อความระดับจุดจะขึ้นเป็นระดับเมือง (หรือกลับกัน) ได้เฉพาะผ่าน transport ที่ประกาศพร้อม ε_bridge | **REUSE-AS-PARENT** |
| `EQ-002/M.01.v1` | "Φ:X→Z is readout-admissible relative to R:X→Y iff constant on every fiber of R … Φ = ḡ∘R (Factorization Theorem)…" | IV.5 / Face 10 | Definition · closed | สถานะ "จุด p ท่วม" **ไม่คงที่บน fiber** ของ readout ระดับเมือง ⇒ พิสูจน์ได้ว่า urban deficit **ไม่อนุญาต** claim ระดับจุด (ตรงกับ "must never be laundered" ของ paste) | **REUSE-AS-PARENT** |
| `weld/E.07.v1` | "τ_public(p) ≤ inf_{g∈G_p} τ(g) (Weakest-link claim ceiling, proved)" | A.13 | Dr · closed | tier ของผลที่ zoom ต่อกัน ≤ ชั้นที่อ่อนที่สุด (urban = heuristic ⇒ ทั้งโซ่ไม่เกิน heuristic ถ้าใช้ urban เป็นตัวรับน้ำหนัก) | **REUSE-AS-PARENT** |
| `weld/E.06.v1` + `weld/M.64.v1` | "Suff_{E,L}(…) ∈ {1,0,⊥}; Inv_E(z)≠Inv_E(z') ⟹ q_E(z)≠q_E(z')" / "ρ(s)=ρ(t) ⇒ s ∼_Q t" | V-A A.6–A.8 | Definition / Th_coqc · closed | การรวม node เป็น zone ห้ามรวมโหนดที่ต่างกันใน invariant ที่ต้องใช้ (สถานะประตู, outfall คนละตัว, datum คนละชุด) | **REUSE-AS-PARENT** |
| `EQ-001/C.07.v1` | (ดู §2) | — | untagged · closed | urban "NO_DEFICIT_SIGNAL" ≠ ทุกโหนดแห้ง | **REUSE** |
| `D/M.71–76.v1` | (ดู §3) | Face 10; A.13 Gate 2 | Th_coqc · closed | ช่วง `[lo, hi]` → `v := (lo+hi)/2`, `floor := (hi−lo)/2` (renaming): `lo>0 ⟺ Sp` (ROBUST / GUARANTEED_ACCUMULATION / INUNDATED), `hi<0 ⟺ Sm` (GUARANTEED_DRAINAGE), `lo=hi=0 ⟺ Sz` (FLAT / NO_…), อื่น ๆ `⟺ ⊥` (POSSIBLE / UNCERTAIN_SIGN / POSSIBLY_INUNDATED) — **ตรงทั้ง 3 ชั้นของ paste** (VERIFIED: ไล่เงื่อนไขกับโค้ด `classify_storage_increment`, `hierarchical_readout`) | **REUSE-AS-PARENT (exact renaming)** — ตอบ 08 §4.4 HOLD ข้อ 2: *ไม่ใช่ delta* |
| `D/M.77.v1` | "bot_monotone_in_floor : 0 <= f1 -> f1 <= f2 -> classify f1 v = Sbot -> classify f2 v = Sbot." | Face 10 | Th_coqc · closed | **กฎความสอดคล้องเมื่อ zoom** (มิติความละเอียด): หยาบลงทำให้ ⊥ โตได้อย่างเดียว; ร่วมกับ M.74/75 ⇒ เครื่องหมายที่ชัดในชั้นหยาบจะไม่ถูกพลิกโดยชั้นละเอียดที่อยู่ในกรอบเดียวกัน | **REUSE-AS-PARENT** + **DELTA เล็ก**: ต้องประกาศเงื่อนไข **nested box** (ช่วงชั้นละเอียด ⊆ ช่วงชั้นหยาบ) — paste ไม่ได้บังคับ |
| `D/M.79.v1`, `D/M.80.v1` | "signed_floor_below floor vs = certain_below floor vs + unresolved floor vs" / "certain_below floor vs <= signed_floor_below floor vs" | Face 10 | Th_coqc · closed | นับ "กี่จุด/กี่โหนดท่วมแน่" เมื่อรวมขึ้นไปชั้นบน: ใส่ `vs := [θ_i − h_i]` (instance) ⇒ จำนวนจริงอยู่ในวงเล็บ `[certain, certain + unresolved]` — ไม่เฉลี่ย | **REUSE-AS-PARENT** (aggregation แบบนับ zone→urban) |
| `EQ-001/C.15.v1`; `A2/M.11.v1`, `A2/M.15.v1`, `D/M.46.v1` | "A declared nonnegative-integer coarsening map P commutes with composition: P(c+d)=Pc+Pd." / "fold_add_split …" / "sum_list_perm …" / "measure_additive …" | VI-A B.2a | untagged · open_prop / Th_coqc · closed | งบน้ำของ zone = ผลรวมงบ 03 ของโหนดในโซน; **edge ภายในหักล้างกันได้ก็ต่อเมื่อ** มี identity 09(i) — นี่คือสะพานเชิงรูปนัยระหว่าง 09 กับ zoom | **REUSE-AS-PARENT** (C.15 ต้องแจ้งว่า open_prop) |
| `weld/M.13.v1` | "A0 ⊆ A1 ⊆ … ⊆ Am; l(d0_{x'}) = min{ j : x' ∉ Γ_j }" | V-A | Definition · closed | บันไดระดับ zoom; "ระดับแรกที่สถานะน้ำท่วมของจุดหนึ่งถูกแยกได้" | **REUSE-AS-PARENT** (เป็นการจัดดัชนีชั้น ไม่ใช่สูตรตัวเลข) |
| `EQ-001/C.18.v1` | "(∀P. b(P) ≤ N) ∧ (¬Closed(P) ⇒ b(P) < b(refine(P))) ⇒ ∀P ∃k. Closed(refine^k(P))" | V-A | Th_coqc · closed | การแตกเซลล์ zoom (เมือง→sub-polder→โหนด→จุด/แปลง) หยุดในจำนวนขั้นจำกัดเมื่อมีเพดานจำนวนเซลล์ที่ประกาศ | **REUSE-AS-PARENT** |
| `EQ-001/P.05.v1`, `q_formal/M.10.v1` | "Coarse-graining L_R over the ticks gives the spine second-order stepper…" / "Graph Laplacian → Laplace–Beltrami convergence" | II.2 | untagged | — | **NOT A MATCH** — coarse-grain ตามเวลาไปสู่รูปต่อเนื่อง ไม่ใช่การรวมเชิงพื้นที่ของเซลล์จำกัด |
| `EQ-015/P.17.v1` | "Group-averaging / Reynolds ("twirl") projection … Π(X)=(1/\|G\|)Σ RᵀXR …" | — | untagged | — | **NOT A MATCH** — การฉายตามสมมาตร และเป็นการเฉลี่ย (ขัดกฎ no-averaging) |
| Genesis IV.5 "InfoQuotientCompressionExactness" | Genesis เรียกว่า Th_coqc (lumpability) | IV.5 | — | จะเป็น parent ที่ดีที่สุดของ zoom แบบ evolve-then-quotient | **อ้างเป็นรหัสไม่ได้** — ค้น CANONICAL ทั้งไฟล์แล้วไม่พบ (MEASURED) ⇒ "not yet in Toledo"; อ้างได้เฉพาะเป็น Genesis gate |

### 4.1 ส่วนที่ paste ใช้แต่ไม่มี parent — delta จริงของ zoom

- **Monotone endpoint enclosure** (NEW DERIVATION / PROPOSAL — not yet in Toledo; toledo check `NOT_REGISTERED`, MEASURED):
  สำหรับ `f` ที่ monotone รายพิกัด (ไม่ลดในชุด I⁺, ไม่เพิ่มในชุด I⁻) บนกล่องจำกัดที่ประกาศบน ℚ: `f(box) ⊆ [f(x_lo*), f(x_hi*)]` โดย `x_lo*` = (ล่างใน I⁺, บนใน I⁻), `x_hi*` = กลับกัน; และแบบวนซ้ำ (recursion `D_{t+1} = f(D_t, …)` ที่ monotone ใน D) ขอบเขตยังคงอยู่ทุก tick.
  Parents (อิฐ): `R/M.30.v1`, `R/M.25.v1`, `Z/M.22.v1`, `Z/M.15–17.v1`, `A2/M.12–14.v1`; Genesis gate: A.13 Gate 2 (bound หาย ⇒ ⊥/REFUSED ของชั้นนั้นเท่านั้น).
  ใช้ร่วม: Urban `max(0, D+P−C)`, Zone ΔS± (03 ที่ปลายกล่อง), Point `max(0, H−z)`, และ **08 §4.4 ข้อ 1** — **ขึ้นทะเบียนครั้งเดียว** เป็น object ทั่วไปโดเมน M (ไม่ผูกน้ำท่วม) แล้วทุกที่อ้าง occurrence.
- **Nested-box declaration** (ส่วนหนึ่งของ delta เดียวกัน): ช่วงชั้นละเอียดต้อง ⊆ ช่วงชั้นหยาบบนตัวแปรที่แชร์ มิฉะนั้น D/M.77 ใช้ไม่ได้ ⇒ REFUSED NOT_NESTED.
- **Point depth `d_p = max(0, H_p − z_p)`** — **ไม่ใช่ object ใหม่** ถ้า 08 §4.3 ประกาศ `E_k := max(0, S_k − S_safe)` ในรูป "ส่วนเกินเหนือค่าอ้างอิงที่ประกาศ บน datum/หน่วยเดียวกัน": `d_p` = renaming (S→H, S_safe→z). ถ้า 08 ล็อก E_k เป็น "ปริมาตรเท่านั้น" จะเกิด twin ⇒ ข้อเสนอ: ให้ 08 ระบุหน่วยเป็นพารามิเตอร์ แล้ว zoom อ้าง 08.
- **Urban recursion** `D_{t+1} = max(0, D_t + P_t − C_t)` — คงเป็น **heuristic คัดกรอง** ตาม 08 §4.3/§7 (ไม่ใช่ Toledo object); ใส่ interval แล้วก็ยังเป็น heuristic.

### 4.2 คำตัดสินกฎ zoom

**กฎ zoom = composition ของ object ที่ขึ้นทะเบียนแล้ว + delta เดียว.**
Parents: `weld/E.08.v1` (one-way transport), `EQ-002/M.01.v1` (factorization ⇒ ห้าม launder), `weld/E.07.v1` (weakest-link),
`weld/E.06.v1`/`weld/M.64.v1` (ห้ามรวมต่าง invariant), `EQ-001/C.07.v1`, `D/M.71–77.v1` (ป้าย 3 สถานะ + ความสอดคล้องต่อความละเอียด),
`D/M.79–80.v1` (วงเล็บจำนวน), `EQ-001/C.15.v1` + `A2/M.11.v1` (รวมงบ), `weld/M.13.v1`, `EQ-001/C.18.v1`.
Delta: monotone endpoint enclosure + nested-box — ชิ้นเดียว ใช้ร่วมกับ 08.

---

## 5. AUDIT — PROP-FLOOD-09 candidate (เอกสาร method §2.2–2.3) และการชนกับ 08

เอกสาร method สรุปว่า "ต้องมี 09" หลังอ่าน 03/04/05/06 และตัด `weld/M.01.v1`/`weld/S.22.v1` เป็น DRIFT — **แต่ยังไม่ได้ค้น** root IDM (D/, A2/, Z/, R/) และ EQ-001/C.* ส่วน admissibility. ผลการค้นรอบนี้:

| ข้อของ 09 | object ที่ครอบแล้ว | ผล |
|---|---|---|
| (i) identity: `Q_e(k)` เป็นค่าเดียวกันใน `Q_out,u(k)` และ `Q_in,v(k+d_e)` | การหักล้างของ edge ภายในเมื่อรวม: `A2/M.11.v1`, `A2/M.15.v1`, `EQ-001/C.01.v1`, Genesis B.2a (J_out ของ u = J_in ของ v); delay บน edge: `MQ08-stepper/M.01.v1` (unverified) | **DELTA จริง (เล็ก)**: ไม่มี object ใดประกาศว่า "ค่าเดียวถูกบันทึกในสองบัญชีโหนดโดยเลื่อน d_e tick" |
| (ii) bound `\|Q_e\| ≤ cap_e`, pumped/gated ตาม 03 | `EQ-001/C.04.v1` (capacity inequality เป็น admissibility), `A2/M.24–25.v1` (clamp), 03 (กฎ Q_out) | **composition** |
| (iii) sign ของ `Q_e` ต้องตรงกับ 04 | `D/M.71–76.v1` (sign soundness) ∘ PROP-FLOOD-04 | **composition** |
| (iv) junction S ≡ 0 | PROP-FLOOD-03 กับ `S_b ≡ 0` (constant substitution) | **composition** (เอกสาร method เองก็เขียนว่า "no new arithmetic") |
| (v) boundary outfall | PROP-FLOOD-06 `R_H`/`g_U`, 03 `gate_flag` tide-lock, Genesis Face 12, `q_formal/M.26.v1` (แนวคิด) | **composition** |

**คำตัดสิน 09 (สองบรรทัด)**:
09 เป็น **composition** ของ 03/04/06/07 + `EQ-001/C.04.v1` + `A2/M.24.v1` + `D/M.71–76.v1` + `A2/M.11.v1`/`EQ-001/C.01.v1` ใน 4 จาก 5 ข้อ.
**Delta จริงเหลือข้อเดียว** = edge coupling identity พร้อม delay จำนวนเต็ม `d_e` (ข้อ i) — 09 ควรหดเหลือ clause นี้ + ตาราง composition; และ 09 **ไม่ให้ขนาดการไหล** (ขนาด = regime-instance ของ L_R ที่ w_e OPEN, หรือรูปอิ่มตัว/สลับประตูซึ่งเป็น delta แยก ไม่ควรยัดรวมใน 09).

**08 ↔ 09 (กัน twin)**:
- 08 = readout ระดับหน่วย/โหนด (`L_H`, `T_dd`, `E_k`) บนสถานะ 03; 09 = การผูก edge ระหว่างโหนด ⇒ **ไม่ซ้ำ** ตราบที่ 09 ไม่ใส่พจน์ deficit/drawdown (ฉบับ §2.3 ไม่ใส่ — VERIFIED).
- recession: `T_dd` ของ 08 (Q_out คงที่) กับ `R/M.14.v1` (อัตราการลดหดตัวที่วัดได้) **เสริมกัน ไม่ซ้ำ** — R/M.14 ขึ้นทะเบียนแล้ว ⇒ **ห้าม** ตั้ง object "recession" ใหม่อีกตัว; linear reservoir `Q_out = S/T` (NOT_REGISTERED, MEASURED) **ไม่ควรเปิด** เพราะจะเป็น twin ของ T_dd.
- 08 §4.4 HOLD: ข้อ 1 → delta enclosure ของ §4.1 (ขึ้นทะเบียนครั้งเดียว ใช้ร่วม); ข้อ 2 → **REUSE `D/M.71–76.v1`** (ไม่ใช่ delta); ข้อ 3 → REUSE Genesis A.13 Gate 2 + `weld/E.07.v1` (ไม่ใช่ delta).
- point depth ของ zoom ↔ E_k ของ 08: ดู §4.1 — ต้องเป็น occurrence เดียวกัน.

---

## 6. ชุดสมการที่ "แข็งแรงขึ้น" — รหัสเดิม vs delta (แยกขาด)

### 6.1 ใช้ได้เลย (อ้างรหัส, ไม่เขียนสมการใหม่)

- **ต่อโหนด**: PROP-FLOOD-03 (proposal) · clamp `A2/M.24.v1`, `A2/M.25.v1` · ledger `EQ-001/C.01.v1`.
- **แนวโน้ม/ทิศทาง (01, 04)**: เพิ่ม parent `D/M.71.v1`–`D/M.76.v1` (sign soundness) และ `D/M.77.v1` (ความละเอียด).
- **พลังงานผลต่างระดับ/การคลายตัว**: `weld/M.01.v1`, `weld/S.22.v1` (regime OPEN/ไม่อิ่มตัว), `Keystone/M.02.v1`, `Keystone/M.03.v1`, `Keystone/M.07.v1`, `Keystone/M.08.v1`, `weld/M.41.v1`, ceiling `weld/M.42.v1`.
- **สมดุล/การตัดขาด (F3, 05a)**: `weld/M.43.v1`, `L_R/M.22.v1`; คำเตือน FLAT ≠ ไม่ไหล `EQ-001/C.07.v1`.
- **recession**: `R/M.14.v1` (หาง), `R/M.32.v1`, telescoping `R/M.09.v1` / `A2/M.03.v1`.
- **เวลาเดินทาง/lag**: `Z/M.12–14.v1`, `Z/M.21.v1`, `A2/M.07.v1`, `A2/M.24.v1`; สถานะความเร็ว `EQ-001/P.36.v1`, `EQ-001/P.61.v1`; กราฟ delay `MQ08-stepper/M.01.v1` (unverified — แจ้งทุกครั้ง).
- **ความจุ/คอขวด**: `Z/M.23.v1` (widest path), admissibility `EQ-001/C.04.v1` (open_prop); 06 `R_H`/`D_H`/`g_U` (proposal) ไม่เปลี่ยน statement.
- **ขอบเขตน้ำขึ้น**: 03 `gate_flag` (tide-lock) + 06 `g_U` + Genesis Face 12.
- **Zoom**: `weld/E.08.v1`, `EQ-002/M.01.v1`, `weld/E.07.v1`, `weld/E.06.v1`, `weld/M.64.v1`, `EQ-001/C.07.v1`, `D/M.71–77.v1`, `D/M.79.v1`, `D/M.80.v1`, `EQ-001/C.15.v1`, `A2/M.11.v1`, `A2/M.15.v1`, `D/M.46.v1`, `weld/M.13.v1`, `EQ-001/C.18.v1`.

### 6.2 Delta — NEW DERIVATION / PROPOSAL — not yet in Toledo (ห้ามใช้ในโค้ด/หน้าเว็บจนกว่าจะขึ้นทะเบียน)

| # | delta | parents | สถานะ |
|---|---|---|---|
| Δ1 | **Edge coupling identity with integer delay**: สำหรับ edge ที่ประกาศ `e=(u,v)`, `d_e ∈ ℕ` ที่ประกาศ: ค่า `Q_e(k)` ตัวเดียวเป็น summand ของ `Q_out,u(k)` และของ `Q_in,v(k+d_e)`; d_e ไม่ประกาศ ⇒ TAU_UNDECLARED (ไม่ใช่ 0 เงียบ) | 03, `A2/M.11.v1`, `EQ-001/C.01.v1`, `MQ08-stepper/M.01.v1` (unverified), Genesis B.2a | = PROP-FLOOD-09 ฉบับหด; HOLD จน 04 (PR #61) ลง |
| Δ2 | **Monotone endpoint enclosure + nested-box** (ทั่วไป โดเมน M) | `R/M.30.v1`, `R/M.25.v1`, `Z/M.22.v1`, `Z/M.15–17.v1`, `A2/M.12–14.v1`, A.13 Gate 2 | ขึ้นทะเบียน **ครั้งเดียว**; 08 §4.4 และ zoom อ้าง occurrence |
| Δ3 | **Saturating/switched edge flow** `Q_e = g_e(k)·min(cap_e, w_e·Δh_e)` | `weld/S.22.v1` (regime), `A2/M.24.v1`, `EQ-001/C.04.v1`, 05a/07 gate state | **ไม่แนะนำให้เปิดตอนนี้** — w_e, cap_e OPEN ทั้งกราฟ; เปิดเมื่อมี flow telemetry ≥ 3 เหตุการณ์ |
| Δ4 | **ขั้น τ ไม่ขยาย** `τ·2·d_max ≤ 2` (corollary ของ `weld/M.42.v1`) | `weld/M.42.v1`, Genesis II.1 CFL | จำเป็นเฉพาะถ้าจะเดิน stepper Δ3/S.22 จริง |
| Δ5 | **Flux-with-memory ต่อ edge** (รูป discrete ของ `weld/S.12.v1`) | `weld/M.01.v1` (Dr), Genesis II.1/II.2 | **ไม่เปิด** — ไม่มีข้อมูล flow; บันทึกไว้เป็นช่องว่างเท่านั้น |

(ไม่เสนอ: weir/orifice/Manning, linear reservoir, recession object ใหม่, point-depth object ใหม่ — เหตุผลอยู่ใน §3, §4.1, §5.)

---

## 7. Pin caveat (readout ของขณะเดียว — repo ชนะ hub เมื่อขัดกัน)

`git log -1 --format='%h %cs'` (MEASURED ขณะเขียน):

| repo | HEAD | หมายเหตุ |
|---|---|---|
| main.hub | `bd8ee8f 2026-09-18` | hub pin ของ toledo ใน ROUTES = `a21d764`; worktree ที่อ่านอยู่บน branch อื่น (ข้างล่าง) |
| toledo (worktree flood06) | `d135045 2026-09-27` | มีไฟล์ untracked `docs/proposals/PROP-FLOOD-08-DRAFT.md` (ของ กระบวนการคู่ขนาน) — อ่านเป็น draft เท่านั้น; `CANONICAL.json` generated_from_commit `9ca306c` |
| readout_genesis | `6f2cb06 2026-09-13` | hub pin README = `864bb85` ซึ่ง **ไม่ใช่ ancestor** ของ HEAD ท้องถิ่น (MEASURED) ⇒ local กับ pin แยกทางกัน; ไม่ได้รัน `hub.py check --remote --heads` (ไม่ใช้ network ในงานนี้) ⇒ สถานะ remote = OPEN |
| thailand_flood_kg | `99c3692 2026-09-27` | — |

ถ้า hub กับ repo ขัดกัน: **repo ชนะ, hub stale**. ก่อนอ้างรหัสใดในงานที่ออกสู่ภายนอก ให้ `toledo_mcp.cli show <code>` ใหม่ (verdict อาจเปลี่ยนเมื่อ registry bump `.v<k>`).

ข้อจำกัดที่วัดได้ของเครื่องมือ lookup: `check --formula` จับคู่แบบข้อความ — รหัส Coq-form ที่มีอยู่จริง (เช่น `R/M.14.v1`, `D/M.71.v1`) ตอบ `NOT_REGISTERED` เมื่อป้อนเป็นสูตรพิมพ์เอง (MEASURED) ⇒ **ต้องอ่าน statement** ไม่ใช่เชื่อ check อย่างเดียว; ในทางกลับกัน `CANDIDATE_MATCH` ของ `A.5/S.07.v1` เป็น false positive.

---

## 8. TODOLIST (ต่อ #90)

| # | gap | fix | owner | prio |
|---|---|---|---|---|
| 90 | PROP-FLOOD-09 §2.3 ประกาศ 5 ข้อเป็น delta ทั้งที่ 4 ข้อเป็น composition | หด 09 เหลือ Δ1 (edge identity + integer delay) + ตาราง composition §5; parents เพิ่ม `EQ-001/C.04.v1`, `A2/M.24.v1`, `D/M.71–76.v1`, `A2/M.11.v1` | founder (D1) + committer | high |
| 91 | 01 และ 04 อ้าง parent แค่ `delta_R`; ป้าย FLAT ที่ ε>0 จริง ๆ คือ ⊥ | เพิ่ม `D/M.71–77.v1` เป็น parent (occurrence, bump `.v<k>` + LINEAGE ตามกติกา) และหมายเหตุ FLAT = ⊥ ที่ ε>0 | committer (registry) | high |
| 92 | enclosure lemma ถูกขอพร้อมกันจาก 08 §4.4 และ zoom → เสี่ยง twin | ขึ้นทะเบียน Δ2 ครั้งเดียวเป็น object ทั่วไปโดเมน M + Coq (อิฐ R/M.30, Z/M.22); 08 และ zoom อ้าง occurrence | committer (registry) + reviewer | high |
| 93 | point depth `max(0, H−z)` ของ zoom กับ `E_k` ของ 08 เป็นรูปเดียวกัน | 08 §4.3 ประกาศ E_k เป็น "ส่วนเกินเหนือค่าอ้างอิงที่ประกาศ บนหน่วย/datum เดียวกัน" แล้ว zoom อ้าง E_k (renaming) — ไม่ตั้ง object ใหม่ | 08-worker | medium |
| 94 | recession แสนแสบวัดได้แค่ขอบล่าง lag | เพิ่ม readout ตาม `R/M.14.v1`: ต่อสถานีที่ FALLING ≥ 3 tick บันทึก `t_k`, ρ envelope, ขอบบนการลดคงเหลือ `t_N/(1−ρ)` ลง `readout_log` (kind recession_front); ρ ถูกหักล้าง ⇒ ถอน | committer | high |
| 95 | ยังไม่ได้ยืนยันว่าความต่างระดับที่นิ่งข้าม SSB.10/SSB.09 มาจากประตูปิด | อ่าน `gate_opening_m` ของ ปตร.มีนบุรี/บางชัน ช่วงเดียวกัน; ถ้าปิด ⇒ สอดคล้อง contrapositive `weld/M.43.v1` (F3/05a); ถ้าเปิด ⇒ "การแพร่ยังไม่ถึง" (บันทึกทั้งสองแบบ ไม่ตัดสินเกินข้อมูล) | committer | medium |
| 96 | lag หนองจอก→พระโขนงไม่มีวิธีประกอบจาก edge | เมื่อมี d_e ต่อ edge: คำนวณ earliest arrival ด้วย min-plus (`Z/M.21.v1`, `A2/M.07.v1`) บน tick จำนวนเต็ม; รายงานเป็นขอบล่าง ไม่ใช่ค่ากลาง | committer | medium |
| 97 | ขนาดการไหลบน edge ไม่มี w_e/cap_e | คง REFUSED; เปิด Δ3/Δ4 เฉพาะเมื่อมี flow telemetry ≥ 3 เหตุการณ์ (TODO #75 เดิม) — ห้าม Manning/weir | founder + committer | low |
| 98 | กฎ zoom ในโค้ดภายนอกไม่บังคับ nested box / datum | ถ้ารับโค้ดเข้าคลัง: guard NOT_NESTED + DATUM_MISMATCH; ป้ายสถานะทุกชั้นอ้าง `D/M.71–76.v1`; urban layer ติดป้าย heuristic | committer | medium |
| 99 | Genesis IV.5 อ้าง "InfoQuotientCompressionExactness" (Th_coqc) แต่ไม่พบใน CANONICAL | แจ้งฝั่ง Toledo ให้ค้น/ขึ้นทะเบียน (ถ้ามีไฟล์ Coq จริง) ก่อนใครอ้างเป็นรหัส | Toledo registrar | low |
| 100 | readout_genesis local ไม่ตรงกับ hub pin (`864bb85` ไม่ใช่ ancestor) | รัน `hub.py check --remote --heads` ในงานที่มี network; ถ้า repo ต่าง ⇒ repo ชนะ, บันทึก hub stale | committer | low |
| 101 | ไฟล์นี้ maker = checker | reviewer อิสระอ่าน statement ของทุกรหัสใน §2–§5 เทียบ mapping อีกรอบ + leak scan ก่อนนำเข้า PR | reviewer | high |
