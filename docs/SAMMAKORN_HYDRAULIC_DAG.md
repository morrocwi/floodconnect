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

## Pond-level asset model

### Pond 1

```text
local drainage -> [unresolved intake] -> Pond 1
Pond 1 -> ST.SPS.01 -> interface associated with Khlong Saphan Sung
```

Verified design capacity: **1.00 m3/s (2 x 0.50)**.

### Pond 2

```text
local drainage -> [unresolved intake / buried conveyance] -> Pond 2
Pond 2 -> ST.SPS.02 -> interface associated with Khlong Ban Ma 2
```

Verified design capacity: **0.75 m3/s (3 x 0.25)**.

This does **not** mean Pond 2 must visibly touch an open canal. BMA's canal inventory says
Khlong Ban Ma 2 terminates at/extends to Sammakorn Village, while the project budget
contains multiple pipe connections. The exact connection from Pond 2 to that canal remains
an **as-built question**.

### Pond 3

The 2567 control-structure table excerpt used here does not list Pond 3. The original
project budget has a second `2 x 0.50 m3/s` station after accounting for Pond 1, so Pond 3
is a plausible match, but this is **inference only** and must not be promoted to verified
asset data without a direct record.

### Pond 4

```text
local drainage -> [unresolved intake] -> Pond 4
Pond 4 -> ST.SPS.04 -> interface named "ตอนคลองวัดใหญ่"
```

Verified design capacity: **2.00 m3/s (2 x 1.00)**.

The station name and field imagery locate the structure at the pond edge, but the exact
buried discharge route from Khlong Wat Yai onward still requires an as-built plan.

## Separate downstream station: Khlong Ban Ma 2

BMA lists a separate asset:

```text
Khlong Ban Ma 2 -> Pump station Khlong Ban Ma 2 -> Saen Saep-side network
```

Capacity: **4.00 m3/s (4 x 1.00)**.

MEA also distinguishes `สถานีสูบน้ำบึงที่ 2 ตอนคลองบ้านม้า 2` from
`สถานีสูบน้ำคลองบ้านม้า 2 ตอนคลองแสนแสบ`. Treat these as **different nodes**.

Therefore the topology can contain two pumping stages:

```text
Pond 2
  -> pond pump ST.SPS.02
  -> local/pipe/canal conveyance
  -> Khlong Ban Ma 2
  -> downstream Ban Ma 2 pump/control structure
  -> Saen Saep
```

The middle pipe/channel geometry is still unresolved.

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
