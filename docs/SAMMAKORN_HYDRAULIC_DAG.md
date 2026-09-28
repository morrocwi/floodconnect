# Sammakorn Hydraulic DAG — คลอง ↔ ประตู ↔ บึง ↔ ปั๊ม

**Status:** operational model with explicit unknowns. Do not infer unverified pump directions.

## Core model

แก้มลิงต้องแยกทางน้ำเป็น 2 edge คนละหน้าที่:

```text
คลอง/ท่อระบายน้ำภายนอก
        |
        |  GATE / CONTROLLED INLET
        |  gravity inflow when H_canal > H_pond
        v
      [ บึง ]
        |
        |  PUMP / CONTROLLED OUTLET
        |  mechanical outflow
        v
คลองรับน้ำภายนอก → โครงข่ายคลองหลัก → คลองแสนแสบ
```

ดังนั้น ห้ามแทนความสัมพันธ์คลองกับบึงด้วยลูกศรเส้นเดียวถาวร.

## Hydraulic DAG

```text
                         ┌──────────────────────────────┐
                         │  external canal / drainage  │
                         │  C                          │
                         └──────────────┬───────────────┘
                                        │
                         gate_open AND H_C > H_P
                         gravity / controlled inflow
                                        │
                                        v
                         ┌──────────────────────────────┐
                         │  retention pond P           │
                         │  temporary storage          │
                         └──────────────┬───────────────┘
                                        │
                       pump_on AND receiving_capacity
                           mechanical outflow
                                        │
                                        v
                         ┌──────────────────────────────┐
                         │ receiving canal R           │
                         └──────────────┬───────────────┘
                                        │
                                        v
                                wider canal network
                                        │
                                        v
                                  Khlong Saen Saep
```

### Important

- `GATE` ไม่ใช่ปั๊ม: ทำหน้าที่เปิด/ปิด hydraulic connection.
- `PUMP` ไม่ใช่ประตู: ทำหน้าที่สร้าง head เพื่อบังคับน้ำออกจากบึง.
- คำว่า 'ดึงน้ำเข้าบึง' ไม่ได้แปลว่าต้องมี pump-in; ถ้า H_canal > H_pond และประตูเปิด น้ำเข้าได้ด้วย gravity.
- ขณะนี้หลักฐานสนับสนุน pump-out ของระบบบึงสัมมากร แต่ **pumped inflow เข้า 4 บึงยังไม่ established**.

## Node and edge semantics

### Nodes

- `C`: external canal / local drainage node
- `P`: retention pond / storage node
- `R`: receiving canal node
- `S`: Saen Saep trunk node

### Edge A — canal → pond

```text
C --[gate / inlet]--> P
```

Active only when:

```text
gate_state == OPEN
AND H_C > H_P
AND pond_storage_available > 0
```

Interpretation: **gravity inflow / capture**.

### Edge B — pond → receiving canal

```text
P --[pump]--> R
```

Active only when:

```text
pump_available == true
AND pump_on > 0
AND receiving_capacity != BLOCKED
```

Interpretation: **mechanical outflow / pre-drain / recovery drain**.

### Edge C — receiving canal → Saen Saep

```text
R --> ... --> S
```

This edge follows the verified canal topology. It is not assumed from geographic bearing.

## Operating states

| State | Gate | Pump | Expected movement | Meaning |
|---|---|---|---|---|
| PRE_DRAIN | closed/controlled | ON | P → R | lower pond before rain |
| CAPTURE | OPEN | usually OFF/controlled | C → P | accept excess water into storage |
| HOLD | CLOSED/controlled | OFF/limited | none/minimal | keep stored water while downstream is constrained |
| RECOVERY | closed/controlled | ON | P → R | empty pond after downstream improves |
| FAIL_CLOSED | UNKNOWN | UNKNOWN | do not infer | insufficient telemetry |

## Minimal equations

### Gravity inflow eligibility

```text
DeltaH_in = H_C - H_P
gravity_inflow_possible = gate_open AND DeltaH_in > 0 AND storage_available
```

### Pumped outflow eligibility

```text
pumped_outflow_possible = pump_on > 0 AND receiving_canal_can_accept
```

Do not infer actual Q from pump count alone; delivered flow depends on pump curve, head, blockage and operating condition.

## Sammakorn implementation

Model each of the four pond systems independently:

```text
external/local canal C1 -> gate G1 -> pond P1 -> pump ST.SPS.01 -> receiving canal R1
external/local canal C2 -> gate G2 -> pond P2 -> pump ST.SPS.02 -> receiving canal R2
external/local canal C3 -> gate G3 -> pond P3 -> pump ST.SPS.03 -> receiving canal R3
external/local canal C4 -> gate G4 -> pond P4 -> pump ST.SPS.04 -> receiving canal R4
```

Known at system level: the four-pond project is intended to temporarily store water associated with Khlong Ban Ma, Khlong Ban Ma 2 and Khlong Saphan Sung / Ramkhamhaeng drainage, then drain back to the surrounding canal network.

**Do not assign R1/R3/R4 to a specific named canal until asset-level evidence is found.**

Station 2 may be associated with Khlong Ban Ma 2, but the exact inlet/outlet hydraulic drawing should still be treated separately from the station's location.

## Fail-closed rules

1. Missing gate state → `UNKNOWN`, never assume OPEN.
2. Missing pond water level → cannot determine gravity direction.
3. Missing external canal level → cannot determine gravity direction.
4. Pump count > 0 proves operation, not actual discharge.
5. High receiving-canal water can reduce pump effectiveness; do not assume nameplate flow.
6. Never convert the word `ดึงน้ำ` into `pump_in` without direct engineering evidence.

## Evidence anchors

- BMA identifies monkey-cheek storage as part of Bangkok flood management and separately tracks pump stations and floodgates as drainage assets.
- Public reporting on the Sammakorn project describes the four ponds as receiving/holding water associated with Ban Ma, Ban Ma 2 and Saphan Sung drainage, then releasing it later.
- FloodConnect live pump telemetry already exposes pump and gate fields for ST.SPS.01-04; this DAG supplies the missing hydraulic semantics.

## Data requirement for full verification

For each pond/station obtain:

- pond water level and datum
- outside canal water level and datum
- gate opening/state
- pump ON/total
- pump design direction
- intake coordinate
- discharge coordinate
- receiving canal name
- pump curve / design Q and head if available

Then the system can resolve **why water is not moving** rather than only saying a pump is on/off.