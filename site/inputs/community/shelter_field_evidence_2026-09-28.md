# Field evidence for shelter/community sustainment schema — Bangkok flood, 28 Sep 2026

**Status:** RELAYED field evidence supplied to the project maintainer.  
**Purpose:** schema/failure-mode extraction only.  
**Not used as:** measured telemetry, hydraulic data, a safety declaration, or a population estimate.

Privacy rule: no resident names, phone numbers, diagnoses, room numbers, or precise household
identifiers are retained here. Medical observations are converted only into functional support
needs.

## Case A — low site beside receiving canal

Source: public post from Darul Ibadah Mosque (Hua Mak Noi), relayed by maintainer on 28 Sep 2026.

Reported pattern:
- water was being pumped into Khlong Hua Mak;
- canal level was reported much higher than normal;
- water overflowed into the mosque area;
- the mosque site was described as lower than the canal;
- the mosque's own pump could not keep up;
- requests included sandbags and additional pumping support.

Schema consequences:
1. A large/religious/community building is not automatically a shelter.
2. `site_hazard_safety` must include receiving-water/flood exposure, not building type.
3. `perimeter_flood_defense` and `dewatering_capability` are PRE_OPEN requirements.
4. A dewatering plan must include a viable discharge destination; pumping into a constrained
   receiver can fail to improve the site.
5. If site hazard is known unsafe, shelter screening rejects the candidate regardless of
   capacity or services.

## Case B — occupied residential blocks with electricity but no service water

Source: public field report by The Reporters from Khlong Chan flats, relayed by maintainer
on 28 Sep 2026.

Reported pattern:
- some residents retained electricity but lacked usable water for toilets/washing;
- residents improvised a long hose from another building and rationed service water;
- older people living alone and people needing mobility/medical assistance required checks
  or assisted transport;
- infant feeding needs were reported;
- some people exposed themselves to floodwater while trying to obtain food;
- parked vehicles on a bridge interfered with boat access in one location;
- relatives were used as an alternative destination to public shelter.

Schema consequences:
1. `drinking_water` and `service_water` are separate shelter resources.
2. Member needs are recorded as aggregate functional categories:
   `older_adult_alone`, `mobility_assistance`, `essential_medication`,
   `time_critical_medical_followup`, `infant_feeding`, etc.
3. An occupied site with a service-water failure is not a fully viable OCCUPIED shelter.
4. Hunger/resource failure must not automatically trigger unsafe self-evacuation; the decision
   layer first looks for verified delivery/support or assisted movement.
5. Access includes responder/boat access, not only resident road access.
6. A relative/family location may be a destination only after the same current safety,
   access and capacity verification applied to any other external node.

## Case C — local food stockout and central-kitchen response

Source: public post from Mirror Foundation, verified public account, relayed by maintainer
on 28 Sep 2026.

Reported pattern:
- field teams found older residents living alone and single-caregiver families with young
  children unable to cross floodwater to obtain food;
- some people who could reach shops encountered depleted shelves / replenishment lag;
- household food was reported to be running out while floodwater remained;
- a central kitchen was established to transform donated ingredients into prepared meals
  for last-mile delivery to people unable to leave home.

Schema consequences:
1. Supply availability at a shop is time-varying; a mapped store is not a verified supply point.
2. `RESUPPLY_WINDOW` requires a verified supplier **and** a verified path.
3. When mobility closes, support shifts from household travel to support-network delivery.
4. Central kitchens/distribution hubs are support nodes, not necessarily shelters.
5. Social nodes must aggregate who cannot self-access supplies before allocating helpers.
6. `single_caregiver`, `older_adult_alone` and `infant_feeding` belong in the
   privacy-preserving member-need profile.

## Phase-aware resource library

### PRE_OPEN / before flood or before shelter activation
- site hazard/flood and receiving-water exposure;
- structural/fire safety;
- access for residents and responders;
- perimeter barriers/materials where appropriate;
- dewatering pump(s), hoses, fuel/power, and a viable discharge destination;
- backup/critical power;
- communications and charging;
- capacity and management roles;
- safe parking/vehicle plan that does not obstruct bridges, egress or boat launch points;
- exit/closure/relocation plan.

### OCCUPIED / during isolation or shelter operation
- drinking water;
- service water for toilets/washing/cleaning;
- sanitation and hygiene;
- food + special diets/infant feeding;
- essential medicines and time-critical health access;
- critical power;
- communications/charging;
- member accountability and door-to-door/buddy checks;
- mobility/accessibility support;
- sleeping protection (mats/bedding/mosquito protection/light);
- waste management;
- continuing resupply access or delivery mechanism;
- last-mile coverage tracking so "near a main road" is not treated as "already reached".

### RECOVERY / after water recedes
- safe re-entry/site hazard re-check;
- service water and sanitation restoration;
- cleaning/disinfection supplies and protective equipment;
- waste/debris removal;
- health follow-up;
- communications;
- exit from temporary shelter / return / relocation / closure.

## Epistemic boundary

These cases demonstrate failure modes and missing fields. They do not calibrate universal
quantities, stock-duration thresholds, route speeds, flood depths, shelter capacities, or
probabilities. Every operational value remains UNKNOWN until declared/verified for the
specific node and time.
