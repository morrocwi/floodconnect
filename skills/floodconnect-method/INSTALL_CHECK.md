# Install self-test — 15 questions

Run these against the installed skill (any AI, any of the four install paths in
`SKILL.md` §1) before trusting it on a real question. Each question's expected
answer is derived directly from a rule in `SKILL.md` — if the AI's answer
contradicts the "expected" line, the install is wrong, not the rule.

---

**Q1. The point's own pond (Z0) reads calm (GREEN), but a station on the point's
declared outlet path (คลองแสนแสบ → แม่น้ำเจ้าพระยา for หมู่บ้านสัมมากร) is at or over
its critical level. What colour is shown overall?**

Expected: **🟡 เฝ้าระวัง (YELLOW), never GREEN and never RED.** Outlet congestion
floors the colour at YELLOW even with a calm Z0 reading (§3, "Outlet rule") — the
point's own water has nowhere to go. It is never escalated to RED or ORANGE purely
from outlet congestion; RED stays reserved for the point's own Z0 ring.

---

**Q2. WL.SMK.01 reads −0.31 m at 05:00, warning 0.35 m, critical 0.44 m. The
current-interval slope is 0.047 m/h; the longer-window slope is 0.02 m/h. The
trend is RISING. What must the answer include, and is a bare single ETA number
acceptable?**

Expected: a **range**, not a single number — about **14-33 h to warning** and
**16-37 h to critical**, computed from both the fast (current) and slow
(longer-window) slopes, labelled **PROPOSAL (PROP-FLOOD-02, linear, two
windows)** (§4) — **never** `PROP-FLOOD-11` (that is a separate, registered
but not-implemented acceleration-aware proposal). A single unlabelled ETA
number is wrong on two counts: it drops the required range, and it omits the
mandatory PROPOSAL tag.

---

**Q3. The user has never saved a reading before and asks for today's status. What
does the continuity section say?**

Expected: **`NO_PREVIOUS`**, stated explicitly (§5) — never a guessed prior state,
never silence about there being no comparison available.

---

**Q4. A household's shelter info was not given at all. What is the home-shelter
verdict, and is `STAY_PREPARED` ever a safe default here?**

Expected: **`UNKNOWN_ASK_INPUTS`**, naming the missing input — **never**
`STAY_PREPARED` (§7, §9). Missing input never defaults to "stay"; the colour being
UNKNOWN does not change this either, since UNKNOWN ≠ safe.

---

**Q5. A station 2 km upstream of the point is reporting RED (at/over critical), but
the middle layer (Z1/Z2) shows no rise along the KG path toward the point, and the
point's own Z0 reading is calm. What colour does the point itself get?**

Expected: **🟡 เฝ้าระวัง (YELLOW)**, not RED and not ORANGE. RED is reserved for the
point's own Z0 ring (§3); ORANGE requires the middle layer to *confirm* water moving
toward the point, which this scenario explicitly does not have. There is no
kilometre-distance rule that would make 2 km automatically RED or ORANGE.

---

**Q6. A station's declared "bank" and "critical" thresholds are both `0`. The
station's raw reading is, say, 1.2 m. What colour does this threshold support?**

Expected: **⚪ ไม่ทราบ (UNKNOWN)** for that basis — a `0`/`null` threshold is not
usable (§3, "Zero/null thresholds"). The answer must not report RED just because
1.2 m is numerically "over" a broken zero threshold, and must not default to GREEN
either.

---

**Q7. Drill engine, case 1 — the TOP (TMD+RID) report and the BOTTOM (province)
report both read calm for the point's area. Does the AI ask the user whether to
drill, and what is the one-line output?**

Expected: **it never asks.** The rule-1 match fires automatically:
`ต้องขยับไหม: ไม่ — <reason> (TOP @<time>, BOTTOM @<time>)` (§0b). The answer stops
there — no Sandwich zoom, no question back to the user.

---

**Q8. Drill engine, case 2 — TOP is calm nationwide, but BOTTOM (the province
report) names the point's own area at warning-or-worse. What fires, and what
happens next?**

Expected: rule 3 fires (TOP calm, BOTTOM not — a conflict, one calm and one
not) — `ต้องขยับไหม: ใช่ — ขัดแย้งกัน` (§0b) — then the Sandwich zoom (§3) runs
and pulls the middle layer from the APIs (§2). This is still decided by the
rule table alone, never by asking the user.

---

**Q9. Drill engine, case 3 — the BOTTOM report (province) could not be fetched at
all (404/timeout) today. TOP is calm. What fires?**

Expected: rule 3 fires on the missing report alone — `ต้องขยับไหม: ใช่ — รายงาน
ขาด/เก่าเกินรอบ` (§0b) — regardless of what TOP said, because a missing slice can
never be skimmed. This is **not** a scored/weighted decision; a single missing
report is enough by itself.

---

**Q10. An agency reading says the pond is calm, but the user reports water on the
ground near their house right now. Also: should the AI cross-check the TOP and
BOTTOM reports against each other line-by-line before answering?**

Expected two things:
- **Facts vs conclusions stay separate** — the agency reading and the user's
  ground report are both kept as FACTS, each tagged with its own source and age;
  the conflict is shown on both sides, never silently resolved to the agency's
  number; the safest action wins, never the agency number alone, when ground
  truth and the agency reading disagree (§3's floor rule).
- **No cross-check/sweep.** §0b skims each once for one question only and never
  re-reads either report to double-check the other (token cost).

---

**Q11. The point's own Z0 reading is RED and no official evacuation order
exists yet for the area. What does the answer say?**

Expected: it tells the user to **move to safety now**, plus the exact line
**"ยังไม่มีคำสั่งทางการ — อย่ารอ"** (§3's precedence rule). It must **never**
say only "ทำตามประกาศทางการ" — a missing official order never lowers a verdict
the reading itself already put at RED/LEAVE; an order can only raise a
verdict, never lower one.

---

**Q12. A weak model asks "where did this ETA number come from, and can I trust
the outlet station you mentioned?" What should the PROVENANCE block have
already told it?**

Expected: the model should already know — (1) the ETA's source of truth is a
Toledo-registered equation code with its tier shown (`PROP-FLOOD-02`, linear,
two windows, tier `Dr`, `PROPOSAL`, not a settled theorem — not
`PROP-FLOOD-11`, which is registered but not implemented in this release);
(2) the outlet station is only
usable because it reached the answer via a **declared KG edge with a declared
source** — never a heuristic (code-family/name-only/radius) join, which would
not even appear in the evidence list (§2's KG-only rule); (3) agency data is
always the agency's own, fetched fresh, never this file's memory of a number.

---

**Q13. (SCC) The §0b drill ESCALATEs for an area. The pumps dimension's source
times out (no response at all). What happens to the rest of the assessment?**

Expected: the walk **continues to every other dimension** (pond, outlet,
rain, road flooding, forecast, upstream pressure) — the pumps dimension alone
is marked **`OPEN`**, with the timeout named as the reason (§4b, rule 2). A
single dimension's source failure is never treated as a failure of the whole
assessment, and the AI must not stop early or report the area as UNKNOWN
just because pumps timed out.

---

**Q14. (SCC) Only the pond (Z0) dimension has real data; every other
dimension (pumps, outlet, rain, road flooding, forecast, upstream pressure)
came back `OPEN`. Can the AI give an overall colour for the area?**

Expected: **no overall verdict.** An overall colour needs both the pond
(Z0) and the outlet/receiving canal `FOUND` (§4b, rule 3) — that minimum
load-bearing pair is not met here: the outlet is `OPEN`. The answer names
which dimensions are `FOUND` (pond only) and which are `OPEN` (the outlet
and the rest), lowers confidence accordingly (rule 4), and does **not**
collapse this into a single area-wide colour as if the other six dimensions
didn't matter.

---

**Q15. (SCC) The pond is FALLING, the receiving canal/outlet it drains to is
reading high, and the rain forecast shows more rain ahead. What single
verdict, if any, should the answer give?**

Expected: **not a single collapsed verdict** — current state and forward
hazard are reported as two separate lines (§4b, rule 5 / AI.md rule 1):
something like "stable now, elevated ahead" — the falling pond plus high
receiver describes the current reading, the rain forecast describes a
separate forward hazard, and neither cancels the other.
