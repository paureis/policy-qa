# Denial-case evaluation, 2026-10-26

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 1. Wall time: 42.8 s.

| Measure | Value |
|---|---|
| Accuracy | 1 / 1 (100.0%) |
| Intended not_settled | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | not run |
| Letter claims verified | 0 / 0 over 1 letters |
| Letter claims struck | 0 / 0 |
| Critic revisions accepted | 0 of 1 reviewed |
| Cost per case | mean $0.1075, p50 $0.1075, total $0.1075 |
| Seconds per case | mean 42.4, p50 42.4 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |

| Program | Correct |
|---|---|
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 1 / 1 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds |
|---|---|---|---|---|---|---|
| dc-030 | not_settled | not_settled | yes | 0 / 0 | $0.1075 | 42.4 |

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
