# Environmental Degradation Clocks for Flood-Affected Nodes

Status: FloodConnect operational design layer
Scope: household, zone, micro-hub and shelter nodes exposed to floodwater, standing water, wet building materials, sewer surcharge/backflow, wastewater or sewer-gas conditions.

This layer answers a different question from water depth:
A place may be safe to occupy at time t0, yet become unsafe later even if water depth is unchanged. What clock is running, what trigger changes the node state, and what verified intervention can extend the usable horizon?

It composes with Toledo/FloodConnect; it does not replace hydrology or public-health guidance.

## 1. Do not model one universal age of floodwater

Flood hazards age in different ways.

Immediate contamination hazards: if sewage intrusion/backflow is suspected or confirmed, FloodConnect does not give the water a grace period. Floodwater/sewage contamination is treated as an immediate WASH/health hazard until the source and water quality are verified.

Time-dependent hazards include wet indoor materials and mold, persistent standing water and vectors, stagnant organic/sewage-loaded water and anaerobic odor/sulfide potential, and sewer-gas accumulation in low/enclosed poorly ventilated spaces.

## 2. Core environmental state

For node i:

X_env_i(t) = (Contamination, Backflow, Gas, Moisture/Mold, Vector)

Environmental state:
- UNSAFE when a verified hard environmental failure exists.
- UNKNOWN when no verified failure is established but a safety-critical mechanism remains unresolved.
- DEGRADING when current occupancy may continue but a verified clock/trigger is active.
- STABLE when no current environmental trigger is declared.

UNKNOWN != SAFE.

## 3. Contamination and sewer-backflow triggers

SewageSuspected = 1 => sanitation/WASH failure. No aging term is used.

SewerBackflow in {SUSPECTED, CONFIRMED} => sanitation_hygiene failed and service-water function degraded.

If a backwater valve is closed, wastewater generation inside the building should be reduced because discharge may not pass the valve while the sewer is surcharged.

## 4. Mold / wet-building clock

Let A_wet(t) = t - t_wet_start for indoor materials that remain wet and have not been fully dried/remediated.

24 h <= A_wet < 48 h => MOLD_PREVENTION_WINDOW_CLOSING.
A_wet >= 48 h => ASSUME_MOLD_PRESENT unless the affected materials were fully dried/remediated.

This is an indoor-material moisture clock, not a floodwater contamination threshold.

Clock-reset/delay actions: remove water where safe, dry wet materials quickly, use ventilation/dehumidification only when electrical conditions are safe, and remove materials that cannot be cleaned and fully dried.

## 5. Standing-water / vector clock

StandingWater = 1 => VECTOR_CONTROL_NEEDED immediately.

CDC recommends weekly source reduction. Some common mosquitoes can develop from egg to adult in about 7-10 days. FloodConnect therefore uses 168 h only as a weekly control-cycle deadline, not as a universal claim that mosquito risk begins exactly on day 7.

A_standing >= 168 h => VECTOR_CYCLE_ESCALATED.

## 6. Sewer gas / hydrogen sulfide

Research on sewers shows that under anaerobic conditions sulfate-reducing bacteria can produce sulfide/H2S. Formation depends on multiple interacting terms including biodegradable organic load, sulfate, hydraulic residence time, temperature and anaerobic conditions.

Conceptually:
Phi_H2S = f(Anaerobicity, OrganicLoad, Sulfate, HRT, Temperature)

FloodConnect does not calculate ppm from this expression without measured/calibrated inputs.

Instead:
Stagnant_or_VerySlow AND (HighOrganicLoad OR SewageIntrusion) => ANAEROBIC_ODOR_PLAUSIBLE.

Rotten-egg/sewer odor triggers SEWER_GAS_UNRESOLVED, but absence of smell cannot clear H2S because olfactory fatigue/paralysis can occur.

If qualified monitoring reports elevated H2S, the node becomes a measured gas-hazard case. FloodConnect uses the NIOSH 10 ppm 10-minute ceiling only as a conservative measured-hazard trigger, never as a residential safe-below-this-value clearance criterion.

## 7. Drain traps vs sewer surcharge

A dry drain trap can remove the liquid seal that normally blocks sewer gas:
TrapSeal = DRY => DRY_TRAP_SEWER_GAS_PATH.

Maintaining/restoring the trap liquid seal can address this pathway.

Sewer surcharge/backflow is different. A trap seal does not solve system surcharge; backflow protection, reduced wastewater generation and restoration of sewer capacity are separate controls.

## 8. Thai term 'น้ำเน่า'

Do not encode 'น้ำเน่า' as one scientific state.

Map it into observable mechanisms:
stagnation, organic/sewage load, odor, color change, anaerobic potential, WASH contamination, vector habitat.

Thai Department of Health guidance describes prolonged floodwater as potentially becoming dark and foul-smelling and recommends rapid drainage where possible, preventing food waste/rubbish from entering the water, and clearing drainage paths.

## 9. Time-to-unsafety

For every time-based mechanism j with a defensible deadline:
T_env_i_j = T_trigger_i_j - t.

The next environmental deadline is:
T_env_i = min over known environmental deadlines.

Unknown clocks are not treated as infinity.

The effective occupancy/shelter horizon is:
T_effective_i = min(T_resource_i, T_environment_i, T_access_i, T_forward_hazard_i).

If T_environment_i < T_planning, the node cannot be claimed sustainable for the full planning horizon unless a mitigation plan is verified to occur before the deadline.

## 10. Intervention as a clock-shift operator

For intervention k:
M_k: (T_trigger, State) -> (T'_trigger, State').

FloodConnect records a clock extension only when intervention effect is actually verified.

Examples:
- complete drying/remediation ends the wet-material mold clock;
- safe drainage/removal ends or reduces the standing-water clock;
- removal of organic waste plus restored flow reduces conditions supporting anaerobic odor;
- sewer repair/isolation/backflow control changes the sewer-backflow state;
- restored trap seal closes a dry-trap gas pathway;
- source reduction/vector control resets the operational vector-control cycle.

No guaranteed hour/day extension is assigned to EM, chemicals, aeration or other treatment without local measurement/validated performance.

## 11. Node schema

environment:
  evaluated_at: 2026-09-28T20:00:00+07:00
  sewage_intrusion: UNKNOWN
  indoor_floodwater_present: false
  sewer_backflow: UNKNOWN
  drainage_surcharge_possible: true
  backwater_valve_state: UNKNOWN
  sewer_gas_odor: NONE
  low_lying_or_enclosed_space: false
  ventilation: UNKNOWN
  measured_h2s_ppm: null
  drain_trap_state: UNKNOWN
  indoor_materials_wet: false
  indoor_wet_since: null
  fully_dried_and_remediated: false
  standing_water_present: true
  standing_water_since: 2026-09-26T04:00:00+07:00
  water_movement: STAGNANT
  organic_or_sewage_load: UNKNOWN
  mitigation_plan_verified: false
  mitigation_before_deadline: false

## 12. Decision integration

environmental_degradation.py returns STABLE, DEGRADING, UNSAFE or UNKNOWN plus active triggers, hard failures, unresolved mechanisms, source-control actions and the next evidence-backed deadline if known.

shelter_decision.py applies:
E = UNSAFE => Sustainment = NOT_SUSTAINABLE.
E = UNKNOWN => Sustainment = UNKNOWN.
E = DEGRADING and T_env <= T_planning and no verified mitigation => Sustainment = UNKNOWN.

This allows SAFE_NOW -> DEGRADING -> UNSAFE without waiting for water depth to rise.

## 13. Thailand-specific evidence

- Department of Health Thailand, 15 Oct 2024, prolonged stagnant floodwater, foul odor, drainage and waste-control guidance: https://anamai.moph.go.th/th/news-anamai/43815
- Department of Health Thailand, 25 Sep 2026, standing-water/environmental hygiene risks: https://anamai.moph.go.th/th/news-anamai/45229
- Department of Health Thailand, 26 Sep 2026, flood-affected drinking/service water contamination precautions: https://www.anamai.moph.go.th/th/news-anamai/45231
- Department of Disease Control Thailand, 4 Sep 2026, food/water contamination during and after floods: https://ddc.moph.go.th/odpc7/news.php?news=60036
- Microbiological evaluation of water during the 2011 flood crisis in Thailand, Science of the Total Environment 463-464 (2013) 959-967, DOI 10.1016/j.scitotenv.2013.06.071.

## 14. Global evidence anchors

- WHO environmental health in emergencies and stagnant-water/vector guidance.
- CDC floodwater safety and mold prevention guidance.
- FEMA Urban Flooding guidance on backwater valves and reduced water use.
- US EPA guidance on sewer gas barriers and drain traps.
- OSHA/NIOSH hydrogen sulfide hazard, monitoring and odor-fatigue guidance.
- Zhang et al. (2023), Hydrogen sulfide control in sewer systems: A critical review of recent progress, Water Research 240:120046, DOI 10.1016/j.watres.2023.120046.
- Park et al. (2014), Mitigation strategies of hydrogen sulphide emission in sewer networks – A review, International Biodeterioration & Biodegradation 95A:251-261, DOI 10.1016/j.ibiod.2014.02.013.

## 15. Safety boundary

This module does not provide instructions for entering sewers/manholes/confined spaces, chemical sulfide treatment, improvised gas neutralization or unmonitored wastewater dosing.

When sewer gas/H2S is suspected in a low/enclosed space, the safe operational response is source isolation, avoidance, qualified monitoring and appropriate ventilation/engineering control—not smell-based testing or improvised entry.

## 16. Finite temporal accumulation — Toledo discipline

FloodConnect never represents an infinite environmental history.

Every accumulation request declares one finite observation window:

[
W=[t_0,t_1],qquad t_1>t_0
]

and one finite verified event set:

[
E_W={e_1,ldots,e_n},qquad n<infty
]

For mechanism (m), exact active duration inside that window is:

[
A_m(W)
=
sum_{j=1}^{k_m}
left(t^{end}_{m,j}-t^{start}_{m,j}ight)
]

where all declared durations are represented as rational values (Q/Fraction), not infinity
or an silently rounded floating-point accumulation.

The ledger records separately:
- current episode duration inside the declared window;
- cumulative active duration inside the declared window;
- recurrence count;
- whether the mechanism remains active at the window end;
- number of currently active mechanisms;
- maximum concurrent mechanisms observed inside the finite window.

These are **temporal diagnostics, not a risk score**.

### Left censoring

If an event is observed active but its START is unknown:

[
OBSERVED_ACTIVE land START=UNKNOWN
Rightarrow LEFT_CENSORED
]

FloodConnect does not assign zero hours and does not extrapolate backward.

### Incomplete history

If the operator cannot certify that the event history for the declared window is complete:

[
complete
e true
Rightarrow REFUSED
]

for exact accumulated duration.

### Mitigation is not resolution

A mitigation event is retained on the timeline but does not stop the clock:

[
MITIGATION 
otRightarrow RESOLVED
]

Only a verified resolution event can close an active interval.

This follows the same epistemic discipline as the finite Toledo water-balance layer:
bounded declared objects, finite diagnostics and first-class refusal instead of silent
defaults.

Implementation: `finite_temporal_ledger.py`.
