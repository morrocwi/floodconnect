# Human–Animal Household Unit (HAHU)

Status: FloodConnect repository construct / evidence-informed operational design.
Not a claimed global standard.

Flood disasters in Thailand repeatedly show that households do not consist only of people. Dogs, cats and other animals may remain with owners, require food/water/medicine/waste management, constrain evacuation, and determine which shelter is actually usable.

FloodConnect therefore models the household decision unit as:

U_h = H_h union A_h

where H_h is the declared human household and A_h is the declared animal-dependent unit.

Human and animal ledgers remain separate so one cannot mask failure in the other.

## 1. Thai field evidence

Hat Yai response records describe dogs and cats being evacuated with owners, animal illness/death and food shortages, mobile veterinary treatment, animal medicines and dog/cat food at evacuation centres.

Veterinary PSU donation/response records include dry and wet dog/cat food, cat litter, towels, pee pads, leashes/collars and food bowls.

Chiang Mai Night Safari accepted dog/cat food as well as pig, goat, sheep and chicken feed, drinking water, animal bowls, cat litter and blankets.

Nan livestock authorities distributed hay, TMR, pet food and animal survival bags alongside human relief.

Sources:
- Department of Livestock Development Hat Yai response: https://dld.go.th/webnew/index.php/dld-news/head/head-moac/2569/25681201-3
- Veterinary Faculty, Prince of Songkla University: https://vet.psu.ac.th/?p=8752
- NIA flood response including cat litter: https://www.nia.or.th/index.php/Inundation-hatyai-2025
- Chiang Mai Night Safari animal donations: https://chiangmainightsafari.com/th/news/
- Nan livestock flood response: https://region5.dld.go.th/

Interpretation: Thai flood logistics already behave as a multi-species support network. The evidence does not support treating animal needs as an optional afterthought.

## 2. Global evidence

Disaster research shows that animals can change human evacuation behavior. Heath et al. (2001) found pet-related impediments such as multiple animals, outdoor dogs and lack of cat carriers were associated with household evacuation failure. DOI 10.1093/aje/153.7.659.

A public-health review notes owners may refuse evacuation, remain stranded or attempt re-entry when animals cannot be moved or accommodated.

CDC emergency guidance recommends planning food, water, medication, carriers/leashes, identification and destination arrangements for animals, and notes many human shelters do not automatically accept pets.

Sources:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC5551593/
- https://www.cdc.gov/healthy-pets/emergency-preparedness/
- https://www.cdc.gov/healthy-pets/emergency-preparedness/pets-in-evacuation-centers.html

FloodConnect invariant:

HumanRouteFeasible does not imply HouseholdUnitRouteFeasible when animals are declared as co-evacuating dependents.

## 3. Three separate animal evaluators

FloodConnect no longer uses one combined animal-unit check for staying, moving and sheltering.

### 3.1 Animal sustainment
This asks whether declared animal dependents can continue safely for the planning horizon.

Hard resource/function fields may include:
- animal drinking water;
- species-appropriate food/feed;
- required medication;
- litter/waste hygiene;
- veterinary support only when explicitly required.

Containment equipment and transport readiness are deliberately excluded from stay-at-home sustainment.

`Missing carrier != home non-sustainable`

### 3.2 Animal movement readiness
This is evaluated only when movement may be needed.

It can include:
- carrier/crate/leash/harness or other species-appropriate containment;
- identification/records;
- verified transport capacity;
- handler continuity for assistance animals.

Hard movement state uses containment/transport capacity (and assistance-handler continuity when applicable). Identification/records are tracked as preparedness evidence but are not a universal blocker unless a destination explicitly requires them.\n\nStates: `READY / NOT_READY / UNKNOWN`.

### 3.3 Animal destination compatibility
This checks whether the destination can receive the declared animal topology.

Companion, assistance, livestock and community/stray animals are not forced through the same pathway.

This separation prevents an evacuation-preparedness gap from being misread as a household-resource failure.
## 4. Finite resource horizon

For any animal resource r, when stock, verified inflow and daily demand are measured in compatible finite units:

T_a_r = 24 * (Stock_a_r + VerifiedInflow_a_r) / DemandRate_a_r

The implementation uses exact rational arithmetic where this helper is used.

If daily demand is zero or unknown, FloodConnect does not return infinity. Use NOT_REQUIRED explicitly or return UNKNOWN.

## 5. Drinking water for animals

Primary input should be the animal's known normal consumption, veterinary instructions, or measured/declared household use.

If a planning estimate is needed for healthy dogs/cats, veterinary literature can provide a starting estimate, but it must not become a universal emergency entitlement.

AAHA maintenance-fluid guidance includes approximately dog 60 mL/kg/day and cat 40 mL/kg/day. Merck notes general mammalian water need around 44–66 mL/kg/day under thermoneutral conditions, with substantial variation by diet, environment, activity and health.

Therefore the preferred equation is:

D_animal_water_h(T) = T * sum_a(q_declared_a_water)

A veterinary estimate is an optional fallback only when assumptions are explicitly declared.

Sources:
- https://www.aaha.org/resources/2024-aaha-fluid-therapy-guidelines-for-dogs-and-cats/
- https://www.merckvetmanual.com/management-and-nutrition/nutrition-small-animals/

Animal drinking water remains distinct from human drinking water in the ledger even if both draw from the same physical stock.

## 6. Animal food

Preferred calculation:

D_animal_food_h(T) = T * sum_a(q_declared_a_food)

where q comes from the animal's normal feeding plan, product instructions or veterinary plan.

For dogs/cats, veterinary energy equations may be used as a starting estimate, not an automatic operational default:

RER = 70 * BW_kg^0.75
MER = k * RER

where k depends on species, life stage, neuter status, activity and condition.

Merck explicitly notes substantial individual variation, so FloodConnect does not infer food quantity solely from body weight when an actual feeding rate is available.

Source: https://www.merckvetmanual.com/management-and-nutrition/nutrition-small-animals/nutritional-requirements-of-small-animals

## 7. Cat litter / waste management

Real Thai donation requests include cat litter, pee pads, towels and other waste-management items.

FloodConnect does not invent a universal litter kg/cat/day rate.

D_litter(T) = q_declared_litter * T

when a household has an observed/declared burn rate.

Otherwise use cat_litter_for_horizon = SUFFICIENT / INSUFFICIENT / UNKNOWN.

Animal waste management also includes dog waste bags, pee pads where used, litter boxes, cleaning/disinfection and separation from food preparation.

CDC evacuation-centre guidance recommends regular litter-box cleaning, leash/carrier control, separation from food areas and hygiene after animal waste handling.

## 8. Movement readiness

For co-evacuating animals, movement readiness is evaluated separately from sustainment.

`AnimalMoveReady = containment AND identification/handler continuity AND transport_capacity`

The movement route itself must still be field-verified and feasible.

If occupancy is physically unsafe but animal movement is not ready:

`PhysicalUnsafe AND AnimalMoveNotReady -> REQUEST_ASSISTED_EVACUATION_WITH_ANIMALS`

The system must not convert this into a recommendation to remain in an unsafe location.

## 9. Destination compatibility and co-located animal nodes

A human shelter can be compatible with animals in two ways:

1. animal accommodation is embedded in the human shelter; or
2. the human shelter links to a fresh, operational, co-located animal service node.

This supports real layouts such as:

`Human shelter <-> linked animal area/veterinary node`

rather than requiring animals to sleep inside the human sleeping area.

Compatibility checks include:
- accepted species;
- free animal capacity;
- animal drinking water;
- animal food/feed;
- animal waste/litter management;
- containment area;
- separation from food preparation;
- veterinary support when explicitly required.

## 10. Household-unit continuity

Let:
- `T_H` = human effective horizon;
- `T_A` = animal sustainment horizon.

For a co-resident household unit:

`T_HAHU = min(T_H, T_A)`

Movement readiness and destination compatibility are not part of this stay/sustain minimum.
They are checked only when movement is considered.

This means:
- food/litter failure can shorten household-unit continuity;
- lack of a carrier does not shorten safe-home sustainment;
- lack of a carrier becomes critical when movement is necessary.

## 11. Animal topology

FloodConnect now distinguishes animal topology from species list.

### Companion animals
Examples: dog, cat, bird, rabbit/small mammal, reptile, fish.

Destination capability: `companion_animal_accommodation`.

### Assistance animals
This is a role, not a species.

An assistance animal is modeled as part of human functional-support continuity.
Destination capability: `assistance_animal_access`.

It must not be redirected to a pet-only shelter as though it were ordinary companion accommodation.

### Livestock / working animals
Examples: cattle/buffalo, pigs, goats/sheep, poultry, horses.

Destination capability: `livestock_holding`.

These typically require separate feed, holding space and transport nodes.

### Community / stray animals
These are not inferred as private household dependents.

Operational capability: `community_animal_handoff`, normally through zone/civil-society/veterinary response.

### Mixed topology
One household or response node may involve more than one topology. FloodConnect reports `MIXED` rather than forcing one animal type to stand in for all others.
## 12. Privacy

Public/community graph may store species/category counts, resource gaps and accommodation needs, but no pet name, owner phone, microchip number or exact house identifier.

A restricted local rescue roster may hold owner/animal identity, contact, microchip/vaccination records and exact pickup location, but must not be committed to the public FloodConnect repository.

## 13. Safety and evidence boundary

- Animal needs never justify ignoring an official evacuation instruction.
- FloodConnect seeks an animal-compatible or assisted evacuation option rather than recommending remaining in a physically unsafe location.
- No universal litter-use, feed-use or medication rate is invented.
- Species/body-weight formulas are evidence-informed starting estimates only.
- Livestock and wildlife require domain-specific veterinary/agricultural planning beyond this companion-animal module.