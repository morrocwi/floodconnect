# Sammakorn Hydraulic DAG — evidence-first

**Status:** evidence-backed topology with unresolved as-built links.

This document supersedes the earlier simplified assumption that every pond has a directly
verified `canal -> gate -> pond -> pump -> canal` layout. That exact point-to-point layout
has **not** been established for all ponds.

## What is verified

1. BMA's monkey-cheek database describes the aggregate Sammakorn retention system as:

   `รับน้ำจากหมู่บ้านสัมมากร -> ระบายน้ำลงสู่คลองแสนแสบ`

2. BMA's 2023 inspection wording says the internal Sammakorn drainage system at pond pump
   stations 1–4 is used **เพื่อระบายน้ำออกสู่คลองหัวหมาก คลองบ้านม้า และคลองสะพานสูง**.

3. BMA's 2567 flood-plan control-structure table identifies:

   - Pond station 1, at Khlong Saphan Sung: **1.00 m3/s = 2 x 0.50**
   - Pond station 2, at Khlong Ban Ma 2: **0.75 m3/s = 3 x 0.25**
   - Pond station 4, at Khlong Wat Yai: **2.00 m3/s = 2 x 1.00**
   - Khlong Ban Ma 2 station: **4.00 m3/s = 4 x 1.00**

   The table says the pond-station gates are opened/closed according to water condition
   and level. It does **not** by itself show the buried intake/discharge pipes.

4. BMA's Saphan Sung canal inventory says **Khlong Ban Ma 2 runs from Khlong Saen Saep to
   Sammakorn Village**, width about 3–5 m and length about 1.41 km.

5. The official BMA project budget scope for project `0412002-55-30` includes:

   - 4 pump stations matching the design capacity families above;
   - seven connections of **0.80 m drainage pipe**;
   - **HDPE 0.50 m ~258 m**;
   - **HDPE 0.315 m ~135 m**;
   - a **2.0 x 2.0 m box drain ~15 m**;
   - canal/embankment works.

   This proves there are engineered pipe/conveyance links that may not be visible on
   satellite imagery. The budget summary is **not the full BOQ / ปร.4 / as-built drawing**.

## Evidence-first DAG

The system should currently be represented as:

```text
ROAD / HOUSEHOLD DRAINAGE
          |
          | collection network
          | (pipe / drain / local channel; exact mechanism by pond unresolved)
          v
  +-------------------+
  | SAMMAKORN PONDS   |
  | retention storage |
  +---------+---------+
            |
            | pond pump stations 1–4
            | direction: INTERNAL SYSTEM -> EXTERNAL CANAL SYSTEM
            v
  +-----------------------------+
  | LOCAL / PUBLIC CONVEYANCE   |
  | Huamak / Ban Ma /           |
  | Saphan Sung / Wat Yai etc.  |
  +--------------+--------------+
                 |
                 | canal topology + downstream structures
                 v
        +------------------+
        | KHLONG SAEN SAEP |
        +------------------+
```

### Important correction

Do **not** claim that road water reaches each pond by gravity only. The project contains
pipes and pump structures, but the exact road/drain -> pond intake arrangement is still
unresolved without the construction drawings.

Do **not** claim that a pond pump discharges onto the road surface. The verified system
purpose is to move water from the internal Sammakorn system toward public canals and
ultimately Saen Saep. A buried pipe may run under or along a road, but that is not the
same as discharging water "onto the road".

## Verified BMA station-code mapping

BMA PumpHistory on 28 Sep 2026 directly maps the Saphan Sung codes:

| code | BMA station name | capacity / pumps |
|---|---|---|
| `ST.SPS.01` | สถานีสูบน้ำคลองบ้านม้า 2 | 4.00 m3/s = 4 x 1.00 |
| `ST.SPS.02` | สถานีสูบน้ำบึงที่ 4 ตอนคลองวัดใหญ่ | 2.00 m3/s = 2 x 1.00 |
| `ST.SPS.03` | สถานีสูบน้ำบึงที่ 2 ตอนคลองบ้านม้า 2 | 0.75 m3/s = 3 x 0.25 |
| `ST.SPS.04` | สถานีสูบน้ำบึงที่ 1 ตอนคลองสะพานสูง | 1.00 m3/s = 2 x 0.50 |

This mapping is now canonical. Earlier FloodConnect versions shifted the codes and incorrectly
invented `ST.SPS.03 = Pond 3`; that mapping is withdrawn.

### ST.SPS.01 — Khlong Ban Ma 2 terminal station

Verified:
- BMA name: `สถานีสูบน้ำคลองบ้านม้า 2`.
- capacity 4.00 m3/s, four 1.00 m3/s pumps.
- BMA canal inventory: Khlong Ban Ma 2 connects Khlong Saen Saep to Sammakorn Village.
- MEA separately calls this asset `สถานีสูบน้ำคลองบ้านม้า 2 ตอนคลองแสนแสบ`.

Strong working interpretation:
```text
internal Sammakorn / Khlong Ban Ma 2
              -> ST.SPS.01
              -> Saen Saep-side network
```

Calling it the **main outlet/gateway for the village** is a strong topology hypothesis because
it is the largest-capacity station and sits at the Ban Ma 2–Saen Saep end. It is not yet a
verbatim BMA designation.

### ST.SPS.02 — Pond 4 / Khlong Wat Yai

Verified:
- BMA name: `สถานีสูบน้ำบึงที่ 4 ตอนคลองวัดใหญ่`.
- capacity 2.00 m3/s, two 1.00 m3/s pumps.
- BMA canal inventory identifies Khlong Wat Yai Bon as connecting to Khlong Ban Ma.

Working topology:
```text
southern Sammakorn / Pond 4
        <-> ST.SPS.02
        <-> Khlong Wat Yai system
        -> Khlong Ban Ma network
```

Exact intake/discharge direction by operating mode still requires the as-built drawing.

### ST.SPS.03 — Pond 2 / Khlong Ban Ma 2

Verified:
- BMA name: `สถานีสูบน้ำบึงที่ 2 ตอนคลองบ้านม้า 2`.
- capacity 0.75 m3/s, three 0.25 m3/s pumps.
- located in the central Sammakorn retention system.

Supported system-function hypothesis:
```text
road / internal drainage
        -> Pond 2 storage
        ->/from ST.SPS.03 interface
        -> Khlong Ban Ma 2 system
```

BMA says the Sammakorn monkey-cheek receives water from the village/Ramkhamhaeng area, but
**whether ST.SPS.03 itself pumps road/drain water into Pond 2 remains unverified**. The road
capture role is supported; the exact actuator/direction is not.

### ST.SPS.04 — Pond 1 / Khlong Saphan Sung

Verified:
- BMA name: `สถานีสูบน้ำบึงที่ 1 ตอนคลองสะพานสูง`.
- capacity 1.00 m3/s, two 0.50 m3/s pumps.

Supported capture hypothesis:
```text
road drainage + Khlong Saphan Sung high-water diversion
                       -> Pond 1
```

The 2018 project description says the retention system helps draw water associated with
Khlong Saphan Sung into storage. The exact gate/pipe/pump mechanism at Pond 1 is unresolved.

**Unknown:** whether Pond 1 and Pond 2 are directly connected through a buried pipe or another
internal conveyance. Do not add that edge until BOQ/as-built evidence is found.

## Canonical working model — legacy interconnected ponds + new Saen Saep outlet

The current working model is:

1. **Legacy village system:** the original Sammakorn ponds form one interconnected storage
   network. Historical BMA wording says the large ponds were **เชื่อมต่อกัน** before the
   BMA monkey-cheek project was completed.

2. **Do not interpret "interconnected" as every pond having a direct pipe to every other pond.**
   The exact internal topology may be chain, trunk, culvert, pipe, or local channel. What is
   supported is system-level hydraulic connectivity.

3. **BMA project intervention:** the most useful current hypothesis is that BMA added/improved a
   conveyance route from the central storage area toward the large terminal station
   `ST.SPS.01 = สถานีสูบน้ำคลองบ้านม้า 2`, which then discharges at the Saen Saep side.

Working topology:

```text
                ORIGINAL SAMMAKORN STORAGE NETWORK
        +-----------------------------------------------+
        |                                               |
        |   Pond 1 ----?---- Pond 2/central ----?---- Pond 4
        |      \              |                  /       |
        |       \             |                 /        |
        |        +---- legacy interconnected network ----+
        |                                               |
        +-------------------------+---------------------+
                                  |
                                  | NEW / IMPROVED CONVEYANCE
                                  | exact route unresolved
                                  v
                         Khlong Ban Ma 2 corridor
                                  |
                                  v
                             ST.SPS.01
                         4.0 m3/s terminal
                                  |
                                  v
                           KHLONG SAEN SAEP
```

### Role of ST.SPS.02 / 03 / 04 under this model

- `ST.SPS.02` at Pond 4 / Khlong Wat Yai: interface/control asset on the interconnected
  pond system. **Inflow vs outflow remains unresolved.**
- `ST.SPS.03` at Pond 2 / Khlong Ban Ma 2: interface/control asset at the central pond.
  It may participate in road-water capture, redistribution, or drawdown. Exact pump
  direction remains unresolved.
- `ST.SPS.04` at Pond 1 / Khlong Saphan Sung: interface/control asset at the eastern pond.
  It may participate in capture from road drainage / Saphan Sung overflow. Exact pump
  direction remains unresolved.
- `ST.SPS.01` at Khlong Ban Ma 2: treated as the **main terminal outlet to the Saen Saep
  side** in the current working model.

### Important epistemic distinction

Supported:

```text
Pond system = interconnected
Pond system -> new/improved outlet corridor -> ST.SPS.01 -> Saen Saep
```

Still unresolved:

```text
Pond 1 -> Pond 2 direct pipe?
Pond 4 -> Pond 2 direct pipe?
Which exact pipe/channel is the new outlet corridor?
Does ST.SPS.02 pump into or out of Pond 4?
Does ST.SPS.03 pump into or out of Pond 2?
Does ST.SPS.04 pump into or out of Pond 1?
```

This avoids a false precision problem: the network can be historically interconnected even
when the pairwise pipe map is unknown.


## Working hydraulic architecture — three capture interfaces, one terminal outlet

The current functional hypothesis is:

```text
                 EAST / SAPHAN SUNG
road + Saphan Sung overflow
             |
             v
        ST.SPS.04
             |
             v
          Pond 1
             \
              \
               +--------------------+
                                    |
ROAD / INTERNAL DRAINAGE            |
             |                      |
             v                      |
        ST.SPS.03                   |
             |                      |
             v                      |
       Pond 2 / CENTRAL ------------+----> interconnected pond network
                                    |
                                    |
REAR / SOUTH / BAN MA               |
Khlong Ban Ma                       |
             |                      |
             v                      |
        ST.SPS.02                   |
             |                      |
             v                      |
          Pond 4 -------------------+
                                    |
                                    | central outlet connection
                                    v
                               ST.SPS.01
                            4.0 m3/s terminal
                                    |
                                    v
                              KHLONG SAEN SAEP
```

Interpretation:

- **ST.SPS.01**: strongest role assignment — main terminal **outlet** from the Sammakorn
  storage network to the Saen Saep side.
- **ST.SPS.04**: eastern **capture/inlet-side** station serving Pond 1 from road drainage
  and the Khlong Saphan Sung side. Exact hydraulic actuator/direction remains a working
  hypothesis until as-built confirmation.
- **ST.SPS.03**: central **capture/inlet-side** station serving Pond 2 from road/internal
  drainage. Exact pipe route remains unresolved.
- **ST.SPS.02**: rear/southern Ban Ma-side interface serving Pond 4. Current working
  hypothesis favors **capture from the Ban Ma side into Pond 4**, but this has lower
  confidence than the ST.SPS.01 outlet role and remains unresolved without the pump
  plan/section or as-built drawing.

This yields a **3-in / 1-out** functional model:

```text
ST.SPS.04 -> Pond 1 \
ST.SPS.03 -> Pond 2  > interconnected storage -> ST.SPS.01 -> Saen Saep
ST.SPS.02 -> Pond 4 /
```

The internal pond-to-pond connection geometry is not yet mapped. "Interconnected storage"
means hydraulic system connectivity, not a claim that every pond has a direct pipe to the
central pond.


## Gate semantics

A gate at a pond station is a control structure, but its exact hydraulic side must not be
guessed. Until the as-built drawing is found:

- `gate_open` means a hydraulic connection is permitted;
- it does **not** prove whether the instantaneous flow is into or out of the pond;
- flow direction requires compatible water-surface levels on both sides;
- pump direction must come from asset/design evidence, not from water-level difference alone.

## Fail-closed rules

1. Station name `ตอนคลอง X` = verified **association/location label**, not proof that an
   open canal physically touches the pond.
2. Satellite absence of an open canal != absence of hydraulic connection.
3. Project pipe quantities prove hidden conveyance exists, but not which pipe belongs to
   which pond.
4. Never assign a specific intake/discharge route from capacity matching alone.
5. Pond 3 remains unresolved.
6. The full BOQ/ปร.4, construction plan, pipe profile, and as-built drawings are still
   required to close the topology.

## Documents still needed

Request/search for project:

**โครงการก่อสร้างแก้มลิงหมู่บ้านสัมมากรและระบบระบายน้ำถนนรามคำแหง**  
Project budget code: **0412002-55-30**  
Contract period reported by BMA: **20 Jul 2013 – 21 Jul 2018**  
Contractor: **บริษัท ชัยเจริญไมตรี จำกัด**

Priority artifacts:

- แบบ ปร.4 / ปร.5
- ใบแจ้งปริมาณงานและราคา / BOQ
- General Layout / Drainage Layout
- Pump Station Plan & Section for ponds 1–4
- Intake / Discharge Pipe Plan
- Pipe Profile
- Gate Detail
- As-built Drawing

## Sources

- BMA monkey-cheek database:
  https://monkeycheek.bangkok.go.th/mngkaccordion/27
- BMA Saphan Sung canal inventory / action plan:
  https://webportal.bangkok.go.th/public/user_files_editor/99/ITA/2568/Action_Plan_2568.pdf
- BMA official flood-plan library:
  https://dds.bangkok.go.th/content/doc3/index.php
- BMA FY2558 project budget scope:
  https://budget.bangkok.go.th/main/upload/2015/09/29/A20150929142318.pdf
- 2023 government inspection wording:
  https://www.thailandplus.tv/archives/690882
- MEA 2024 inspection distinguishing the two Ban Ma 2 pump assets:
  https://www.mea.or.th/public-relations/corporate-news-activities/announcement/OpMsOL7FX
- BMA statement on contract/contractor:
  https://www.thaipr.net/general/3647868


## Working hypothesis: canal capture into ponds

**Hypothesis status:** supported at system-function level; exact hydraulic hardware path unresolved.

The strongest current interpretation of BMA's 2018 description is that, during a high-water
capture phase, water associated with **Khlong Ban Ma, Khlong Ban Ma 2 and Khlong Saphan Sung**
is intentionally diverted/stored in the Sammakorn retention ponds before later release.

Working DAG:

```text
Khlong Ban Ma / Ban Ma 2 / Saphan Sung
              |
              | controlled diversion
              | pipe / gate / local channel
              | exact hardware unresolved
              v
       Sammakorn retention ponds
              |
              | temporary storage
              v
          HOLD / BUFFER
              |
              | later, when receiving system can accept
              v
      pond pump stations 1–4
              |
              v
      public canal network
              |
              v
         Khlong Saen Saep
```

This hypothesis reconciles two BMA statements that otherwise look contradictory:

1. the ponds help **draw/capture water coming from Ban Ma, Ban Ma 2 and Saphan Sung**; and
2. private retention ponds, including Sammakorn, were equipped with pumps/gates so operators
   can **lower pond level in advance** and create storage before heavy rain.

Therefore FloodConnect should model the system as **time-dependent bidirectional exchange**:

- capture phase: external canal/drainage -> pond;
- recovery/pre-drain phase: pond -> external canal network by pump.

What remains unresolved is whether the capture phase uses only gravity through a gate/pipe,
or whether any separate inlet pump assists flow. The presence of ST.SPS.01–04 must not be
used as proof of inlet pumping.


## Live code source

- BMA PumpHistory live station table:
  https://weather.bangkok.go.th/Station/PumpHistory
  (28 Sep 2026 table rows ST.SPS.01–04 provide the exact code/name mapping.)
