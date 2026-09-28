# Sammakorn Pond–Canal Hydraulic DAG

Status: evidence-backed model with explicit unknowns.

## Core DAG

~~~text
                    RAIN / ROAD DRAINAGE
                             |
                             v
                   LOCAL DRAINS / CANALS
                             |
                 [INLET / WATER GATE]
                             |
          if H_canal > H_pond and gate is open
                             |
                             v
                    SAMMAKORN POND
                  (temporary storage)
                             |
                    [PUMP STATION]
                             |
               forced discharge outward
                             v
       HUAMAK / BAN MA / BAN MA 2 / SAPHAN SUNG
                             |
                             v
                       SAEN SAEP
                             |
                             v
                   WIDER DRAINAGE SYSTEM
~~~

The pond–canal connection is **not one arrow**. It contains two distinct hydraulic functions:

1. **Controlled gravity inflow**: canal/drain -> pond
2. **Pumped outflow**: pond -> receiving canal

## Two-node primitive

Let:
- C = connected canal/drain node
- P = Sammakorn retention-pond node
- H_C = water surface at canal
- H_P = water surface in pond

Represent the connection as:

~~~text
C --[gate/open connection; gravity]--> P
P --[pump]---------------------------> C
~~~

### Gravity inflow condition

~~~text
DeltaH_in = H_C - H_P
~~~

If:
- gate/inlet is open,
- DeltaH_in > 0,
- pond still has storage,

then water can enter the pond without an inlet pump:

~~~text
C ----gravity----> P
~~~

### Pumped outflow condition

A pump creates a mechanical edge:

~~~text
P ----pump----> C
~~~

The pump can move water outward even when gravity alone would not empty the pond, subject to pump head, pump availability and receiving-canal capacity.

## Why the gate matters

The gate is a **connection controller**, not the device that moves water mechanically.

Gate functions:
- OPEN: permit hydraulic connection and possible gravity flow.
- PARTIAL: throttle flow.
- CLOSED: isolate pond from canal and prevent unwanted exchange/backflow.

Therefore the same physical pond can be:
- capturing water,
- holding water,
- or being emptied,

depending on gate state, pump state and the two water levels.

## Operational DAG / state machine

### A. PRE-DRAIN

Before heavy rain, create free storage:

~~~text
POND --PUMP--> CANAL
~~~

Goal: lower H_P.

### B. CAPTURE

When external drainage rises above the pond:

~~~text
CANAL/DRAIN --OPEN GATE + GRAVITY--> POND
~~~

Goal: remove volume temporarily from overloaded drains/canals.

### C. HOLD

When downstream is overloaded:

~~~text
CANAL  X|GATE|X  POND
             pumps may be OFF / constrained
~~~

Goal: keep stored water in the pond until a discharge window exists.

### D. RECOVERY

When the receiving canal has capacity:

~~~text
POND --PUMP--> RECEIVING CANAL --> SAEN SAEP SYSTEM
~~~

Goal: restore pond storage for the next storm.

## Direction table

| Condition | Gate | Pump | Dominant flow |
|---|---|---|---|
| H_C > H_P, pond has room | open | off/optional | C -> P by gravity |
| H_C > H_P, pond nearly full | restricted/closed | depends | inflow constrained |
| H_P > H_C | open | off | P -> C may occur by gravity if structure permits |
| Need to empty pond | controlled | on | P -> C mechanically |
| Receiving canal too high/full | usually isolate as required | constrained/off | HOLD |

The row "P -> C by gravity" is **structure-dependent**. FloodConnect must not assume a free two-way sluice unless the inlet/outlet geometry is verified.

## Evidence specific to Sammakorn

BMA's monkey-cheek database describes the Sammakorn retention basin as receiving water from Sammakorn Village and draining to Khlong Saen Saep. BMA district documentation also shows Khlong Ban Ma 2 connecting Khlong Saen Saep to Sammakorn Village.

A 2023 government inspection states that Sammakorn pond pump stations 1–4 are used **to drain water outward** to Khlong Huamak, Khlong Ban Ma and Khlong Saphan Sung.

MEA identifies Sammakorn pond pump station 2 at Khlong Ban Ma 2.

Therefore:

~~~text
verified:
  pumped_outflow: pond -> external canal

supported hydraulic role:
  controlled_inflow: external drainage/canal -> pond

not established:
  pumped_inflow: external canal -> pond
~~~

The phrase "ดึงน้ำเข้าบึง" should not be encoded as "pump water into the pond" unless an asset drawing or field record specifically confirms an inlet pump.

## Sammakorn network DAG

~~~text
KHLONG SAEN SAEP
   ^      ^       ^
   |      |       |
   |      |       +-- KHLONG SAPHAN SUNG
   |      +---------- KHLONG BAN MA / BAN MA 2
   +----------------- wider receiving network

                    pumped recovery paths
                          ^  ^  ^
                          |  |  |
                    [PUMP 1..4]
                          |
              +-----------+-----------+
              |  SAMMAKORN PONDS 1-4 |
              +-----------+-----------+
                          ^
                          |
                  [GATES / INLETS]
                          |
             local drains + adjacent canals
                          ^
                          |
               RAMKHAMHAENG / VILLAGE
~~~

This drawing is functional, not a claim that every one of pumps 1–4 connects directly to Saen Saep. Current evidence says the four stations discharge to Huamak, Ban Ma and Saphan Sung canals, which then belong to the wider drainage network.

## Graph schema

For every pond–canal interface create **two possible directed edges**, with evidence kept separately:

~~~yaml
nodes:
  - id: pond
    type: retention_storage
  - id: canal
    type: canal

edges:
  - id: canal_to_pond
    from: canal
    to: pond
    mechanism: gravity
    actuator: gate
    conditions:
      - gate_open
      - H_canal_gt_H_pond
      - storage_available
    status: possible_when_verified_connection_exists

  - id: pond_to_canal
    from: pond
    to: canal
    mechanism: pump
    actuator: pump_station
    conditions:
      - pump_available
      - receiving_capacity_available
    status: verified_for_sammakorn_system
~~~

## Fail-closed rules

FloodConnect must return UNKNOWN rather than invent direction when any of these are missing:
- exact inlet/outlet geometry,
- exact pump-to-canal mapping,
- gate position,
- water level on both sides,
- pump status,
- receiving-canal capacity.

Do not infer flow direction from map orientation.

## Minimum live variables

For each interface:
- H_pond
- H_canal
- gate_opening
- pump_on / pump_total
- pump nominal capacity
- pond remaining storage
- receiving-canal state
- observation timestamp

Then:

~~~text
if gate_open and H_canal > H_pond and storage_available:
    gravity_capture = POSSIBLE

if pump_on > 0 and receiving_capacity_available:
    pumped_release = POSSIBLE

if receiving_capacity is UNKNOWN:
    pumped_release_effectiveness = UNKNOWN
~~~

## Sources

- BMA Monkey Cheek Database — Sammakorn retention basin:
  https://monkeycheek.bangkok.go.th/mngkaccordion/27
- Saphan Sung District Action Plan — Khlong Ban Ma 2 connects Khlong Saen Saep to Sammakorn Village:
  https://webportal.bangkok.go.th/public/user_files_editor/99/ITA/2568/Action_Plan_2568.pdf
- Government water-system inspection (11 Apr 2023) — pump stations 1–4 drain outward to Huamak, Ban Ma and Saphan Sung:
  https://www.thailandplus.tv/archives/690882
- MEA (18 Jul 2024) — Sammakorn pond pump station 2 at Khlong Ban Ma 2:
  https://www.mea.or.th/public-relations/corporate-news-activities/announcement/OpMsOL7FX
