#!/usr/bin/env python3
"""
Environmental degradation clocks for flood-affected households/shelters.

Purpose:
- represent hazards that can worsen with time even when water depth is stable;
- keep immediate contamination hazards separate from time-delayed hazards;
- provide fail-closed triggers for shelter_decision.py;
- never infer gas concentration, pathogen concentration, or a universal "safe age" of water.

This module is qualitative unless measured values/timestamps are explicitly supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

UNKNOWN = "UNKNOWN"
STABLE = "STABLE"
DEGRADING = "DEGRADING"
UNSAFE = "UNSAFE"

TRIGGER_SEWAGE_CONTAMINATION = "SEWAGE_CONTAMINATION"
TRIGGER_SEWER_BACKFLOW = "SEWER_BACKFLOW"
TRIGGER_SEWER_GAS_UNRESOLVED = "SEWER_GAS_UNRESOLVED"
TRIGGER_H2S_MEASURED_ELEVATED = "H2S_MEASURED_ELEVATED"
TRIGGER_MOLD_PREVENTION_WINDOW = "MOLD_PREVENTION_WINDOW_CLOSING"
TRIGGER_ASSUME_MOLD = "ASSUME_MOLD_PRESENT"
TRIGGER_VECTOR_CONTROL = "VECTOR_CONTROL_NEEDED"
TRIGGER_VECTOR_CYCLE_ESCALATED = "VECTOR_CYCLE_ESCALATED"
TRIGGER_ANAEROBIC_ODOR_PLAUSIBLE = "ANAEROBIC_ODOR_PLAUSIBLE"
TRIGGER_DRY_TRAP_SEWER_GAS = "DRY_TRAP_SEWER_GAS_PATH"
TRIGGER_BACKWATER_WATER_USE_LIMIT = "BACKWATER_WATER_USE_LIMIT"
TRIGGER_ENVIRONMENT_UNKNOWN = "ENVIRONMENTAL_STATE_UNKNOWN"

# Evidence-backed operational clocks. These are not universal water-safety thresholds.
MOLD_PREVENTION_WATCH_H = 24.0
MOLD_ASSUME_H = 48.0
VECTOR_WEEKLY_CONTROL_H = 168.0  # CDC recommends weekly source reduction.
# NIOSH occupational 10-minute ceiling. This is used only as a measured-hazard trigger,
# never as a residential "safe below this value" clearance criterion.
NIOSH_H2S_CEILING_PPM = 10.0


@dataclass(frozen=True)
class EnvironmentalResult:
    state: str
    triggers: tuple[str, ...] = ()
    hard_failures: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    mitigations: tuple[str, ...] = ()
    next_deadline_h: Optional[float] = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "triggers": list(self.triggers),
            "hard_failures": list(self.hard_failures),
            "unknowns": list(self.unknowns),
            "mitigations": list(self.mitigations),
            "next_deadline_h": self.next_deadline_h,
            "details": dict(self.details),
        }


def _dedup(items):
    return tuple(dict.fromkeys(items))


def _parse_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _age_h(start: Any, now: datetime) -> Optional[float]:
    dt = _parse_time(start)
    if dt is None:
        return None
    return max(0.0, (now - dt).total_seconds() / 3600.0)


def _min_deadline(*values: Optional[float]) -> Optional[float]:
    vals = [v for v in values if v is not None and v >= 0]
    return min(vals) if vals else None


def evaluate_environmental_degradation(
    node: dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> EnvironmentalResult:
    """Evaluate time-varying environmental/WASH degradation.

    Required input lives under node["environment"].

    Important epistemic rules:
    - suspected sewage contamination is not given a grace period;
    - odor alone never estimates H2S ppm;
    - absence of odor never clears H2S;
    - no universal stagnant-water "safe until N hours" claim is made;
    - mold and vector clocks are evidence-backed operational triggers, not water-quality models.
    """
    env = node.get("environment")
    if not isinstance(env, dict):
        return EnvironmentalResult(
            UNKNOWN,
            triggers=(TRIGGER_ENVIRONMENT_UNKNOWN,),
            unknowns=("environment",),
        )

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    triggers: list[str] = []
    failures: list[str] = []
    unknowns: list[str] = []
    mitigations: list[str] = []
    details: dict[str, Any] = {}
    deadlines: list[Optional[float]] = []

    # 1) Flood/sewage contamination: immediate, not an aging clock.
    sewage = str(env.get("sewage_intrusion", UNKNOWN)).upper()
    indoor_floodwater = env.get("indoor_floodwater_present", UNKNOWN)
    if sewage in {"SUSPECTED", "CONFIRMED"}:
        triggers.append(TRIGGER_SEWAGE_CONTAMINATION)
        failures.append("sanitation_hygiene")
        mitigations.extend([
            "avoid direct contact with suspected sewage/floodwater",
            "use verified safe drinking water",
            "restore/isolate wastewater service through qualified local utility/plumbing response",
        ])
    elif sewage == UNKNOWN and indoor_floodwater is True:
        unknowns.append("sewage_intrusion")

    # 2) Sewer surcharge/backflow.
    backflow = str(env.get("sewer_backflow", UNKNOWN)).upper()
    if backflow in {"SUSPECTED", "CONFIRMED"}:
        triggers.append(TRIGGER_SEWER_BACKFLOW)
        failures.extend(["sanitation_hygiene", "service_water_for_horizon"])
        mitigations.extend([
            "reduce nonessential wastewater generation until drainage/sewer function is restored",
            "use verified backflow protection appropriate to the building",
            "professionally inspect damaged or overloaded sewer/septic systems",
        ])
    elif backflow == UNKNOWN and env.get("drainage_surcharge_possible") is True:
        unknowns.append("sewer_backflow")

    backwater = str(env.get("backwater_valve_state", UNKNOWN)).upper()
    if backwater == "CLOSED":
        triggers.append(TRIGGER_BACKWATER_WATER_USE_LIMIT)
        mitigations.append(
            "limit toilet flushing, sinks, showers, laundry and other wastewater-generating use while the valve is closed"
        )

    # 3) Sewer-gas / H2S: measured elevation or unresolved suspicion.
    h2s = env.get("measured_h2s_ppm")
    if h2s is not None:
        try:
            h2s_f = float(h2s)
            details["measured_h2s_ppm"] = h2s_f
            if h2s_f >= NIOSH_H2S_CEILING_PPM:
                triggers.append(TRIGGER_H2S_MEASURED_ELEVATED)
                failures.append("air_quality")
                mitigations.extend([
                    "leave the affected enclosed/low-lying area and prevent unprotected entry",
                    "use qualified gas monitoring and ventilation/engineering controls",
                ])
        except (TypeError, ValueError):
            unknowns.append("measured_h2s_ppm")

    odor = str(env.get("sewer_gas_odor", "NONE")).upper()
    low_enclosed = env.get("low_lying_or_enclosed_space", UNKNOWN)
    ventilation = str(env.get("ventilation", UNKNOWN)).upper()
    if odor in {"ROTTEN_EGG", "SEWER", "SUSPECTED"}:
        triggers.append(TRIGGER_SEWER_GAS_UNRESOLVED)
        # Smell cannot quantify concentration and can disappear due to olfactory fatigue.
        if low_enclosed is True or ventilation in {"POOR", "NONE", UNKNOWN}:
            unknowns.append("sewer_gas_concentration")
        mitigations.extend([
            "do not use smell as a clearance test",
            "avoid confined/low-lying entry where sewer gas is suspected",
            "use qualified gas monitoring when H2S/sewer gas is plausible",
            "ventilate only when it can be done safely without electrical/ignition/confined-space risk",
        ])

    trap = str(env.get("drain_trap_state", UNKNOWN)).upper()
    if trap == "DRY":
        triggers.append(TRIGGER_DRY_TRAP_SEWER_GAS)
        mitigations.append(
            "restore the drain-trap liquid seal or maintain it with an appropriate building-maintenance method"
        )

    # 4) Indoor wet-material / mold clock.
    wet = env.get("indoor_materials_wet", UNKNOWN)
    wet_age = _age_h(env.get("indoor_wet_since"), now) if wet is True else None
    dried = env.get("fully_dried_and_remediated", False)
    if wet is True and dried is not True:
        if wet_age is None:
            unknowns.append("indoor_wet_since")
        else:
            details["indoor_wet_age_h"] = wet_age
            if wet_age >= MOLD_ASSUME_H:
                triggers.append(TRIGGER_ASSUME_MOLD)
                failures.append("indoor_environment")
            elif wet_age >= MOLD_PREVENTION_WATCH_H:
                triggers.append(TRIGGER_MOLD_PREVENTION_WINDOW)
                deadlines.append(MOLD_ASSUME_H - wet_age)
            else:
                deadlines.append(MOLD_PREVENTION_WATCH_H - wet_age)
        mitigations.extend([
            "remove water and dry wet materials as quickly as safely possible",
            "use ventilation/dehumidification only when electrical conditions are safe",
            "remove materials that cannot be cleaned and fully dried",
        ])

    # 5) Standing water / vector clock.
    standing = env.get("standing_water_present", UNKNOWN)
    standing_age = _age_h(env.get("standing_water_since"), now) if standing is True else None
    if standing is True:
        triggers.append(TRIGGER_VECTOR_CONTROL)
        mitigations.extend([
            "remove or drain unnecessary standing water where safe and permitted",
            "empty/scrub/cover water-holding containers on a weekly cycle",
            "for standing water that cannot be removed and is not drinking water, use only approved larval control according to label/local guidance",
        ])
        if standing_age is None:
            unknowns.append("standing_water_since")
        else:
            details["standing_water_age_h"] = standing_age
            if standing_age >= VECTOR_WEEKLY_CONTROL_H:
                triggers.append(TRIGGER_VECTOR_CYCLE_ESCALATED)
            else:
                deadlines.append(VECTOR_WEEKLY_CONTROL_H - standing_age)

    # 6) Anaerobic/odor potential. This is qualitative only.
    flow = str(env.get("water_movement", UNKNOWN)).upper()
    organic = str(env.get("organic_or_sewage_load", UNKNOWN)).upper()
    if flow in {"STAGNANT", "VERY_SLOW"} and (
        organic in {"HIGH", "SEWAGE", "PRESENT"} or sewage in {"SUSPECTED", "CONFIRMED"}
    ):
        triggers.append(TRIGGER_ANAEROBIC_ODOR_PLAUSIBLE)
        mitigations.extend([
            "restore drainage/flow where safe and authorized",
            "remove accessible organic waste/debris without entering contaminated or confined water",
            "prioritize source control over masking odor",
        ])
        details["h2s_model_note"] = (
            "anaerobic sulfide formation is plausible; no ppm is inferred without measurement"
        )

    hard = _dedup(failures)
    unk = _dedup(unknowns)
    trg = _dedup(triggers)
    mit = _dedup(mitigations)

    if hard:
        state = UNSAFE
    elif unk:
        state = UNKNOWN
    elif trg:
        state = DEGRADING
    else:
        state = STABLE

    return EnvironmentalResult(
        state,
        triggers=trg,
        hard_failures=hard,
        unknowns=unk,
        mitigations=mit,
        next_deadline_h=_min_deadline(*deadlines),
        details=details,
    )


def effective_environmental_horizon_h(
    node: dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> Optional[float]:
    """Return the next evidence-backed environmental deadline if known.

    None means no defensible time-to-trigger is currently available; it does NOT mean infinity.
    """
    return evaluate_environmental_degradation(node, now=now).next_deadline_h
