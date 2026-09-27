# Hierarchical Flood Zoom — Urban → Zone/Node → Point

**Status:** proposal / not a Toledo theorem.

The model separates three questions that should not be collapsed into one:

1. **Urban:** is the city-scale drainage envelope under pressure?
2. **Zone/Node:** is local storage accumulating or draining under Toledo-consistent bounds?
3. **Point:** at this exact coordinate, is water surface above ground elevation?

## Layer 1 — Urban screening

Use an equivalent-depth drainage-debt ledger:

[
D_{t+1}=max(0,;D_t+P_t-C_t)
]

where (D,P,C) may be intervals.

For a forecast ensemble:

[
P_tin[P_t^{-},P_t^{+}],qquad
C_tin[C_t^{-},C_t^{+}]
]

then

[
D_{t+1}^{-}
=
max(0,D_t^{-}+P_t^{-}-C_t^{+})
]

[
D_{t+1}^{+}
=
max(0,D_t^{+}+P_t^{+}-C_t^{-})
]

Interpretation:

- (D^- > 0): **ROBUST_DEFICIT**
- (D^- = 0 < D^+): **POSSIBLE_DEFICIT**
- (D^+ = 0): **NO_DEFICIT_SIGNAL**

This layer can remain computable even if local geometry, runoff coefficient, pump state,
or street elevation is still missing. It is **not** Toledo and must never be described as
a point flood-depth prediction.

## Layer 2 — Zone / Node zoom

Use the Toledo PROP-FLOOD-03 structure as the criterion:

[
Delta S
=
P A c
+
Q_{in}	au
-
Q_{out}	au
]

Instead of inventing a missing scalar, use declared finite bounds:

[
Pin[P^-,P^+],;
Ain[A^-,A^+],;
cin[c^-,c^+],;
Q_{in}in[Q_{in}^-,Q_{in}^+],;
Q_{out}in[Q_{out}^-,Q_{out}^+]
]

For non-negative physical quantities:

[
Delta S^-
=
P^-A^-c^- + Q_{in}^-	au^-
-
Q_{out}^+	au^+
]

[
Delta S^+
=
P^+A^+c^+ + Q_{in}^+	au^+
-
Q_{out}^-	au^-
]

Readout:

- (Delta S^- > 0): guaranteed accumulation within declared bounds
- (Delta S^+ < 0): guaranteed drainage within declared bounds
- otherwise: uncertain sign

If no finite bound can be justified, this layer still **REFUSES**. The refusal does not
invalidate the already-computed urban layer.

## Layer 3 — Point zoom

When a compatible water-surface interval and ground-elevation interval exist:

[
d_p = max(0,H_p-z_p)
]

with

[
H_pin[H^-,H^+],qquad z_pin[z^-,z^+]
]

then

[
d_p^-
=
max(0,H^- - z^+)
]

[
d_p^+
=
max(0,H^+ - z^-)
]

Readout:

- (d^- > 0): inundated under all declared bounds
- (d^- = 0 < d^+): possibly inundated
- (d^+ = 0): no inundation under declared bounds

A compatible vertical datum is mandatory.

## Why this solves the scale problem

A city can legitimately receive an **urban flood pressure warning** before the system
knows exactly which street or house will flood.

The output becomes progressively more specific:

[
	ext{Urban deficit}
ightarrow
	ext{Node accumulation}
ightarrow
	ext{Point depth}
]

Each layer has a separate claim boundary. Missing local data widens uncertainty or stops
only the local zoom; it does not force the whole city-scale calculation to disappear.

## Implementation

- `hierarchical_flood_zoom.py`
- exact Toledo ledger remains unchanged in `water_balance.py`

The hierarchy is intentionally one-way: a coarse urban warning must never be laundered
into a claim that a particular point will flood.
