# Denial-case evaluation, 2026-10-30

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 6. Wall time: 123.1 s. Second opinion: meta-models/muse-spark-open-1026, 5 ran.

| Measure | Value |
|---|---|
| Accuracy | 5 / 6 (83.3%) |
| Intended consistent | 1 / 1 (100.0%) |
| Intended inconsistent | 3 / 3 (100.0%) |
| Intended not_settled | 1 / 2 (50.0%) |
| Refusal on the medical question (dc-011) | not run |
| Letter claims verified | 15 / 15 (100.0%) over 4 letters |
| Letter claims struck | 0 / 15 (0.0%) |
| Critic revisions accepted | 2 of 4 reviewed |
| Cost per case | mean $0.1220, p50 $0.1182, total $0.7317 |
| Seconds per case | mean 58.6, p50 59.0 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |
| Dual routes (side by side) | 3 / 3 (dc-012, dc-021, dc-030) |
| Second opinion agrees with the verdict | 4 / 5 (80.0%) of the cases where both ran |
| Second opinion right, verdict wrong | 1 (dc-010) |
| Verdict right, second opinion wrong | 0 |
| Second opinion cost per case | mean $0.0091 over 5 runs |
| Second opinion failed, timed out, skipped | 0, 0, 1 |
| Second opinion skip reasons | the plan is outside the corpus: the verdict makes no model call (1) |

| Program | Correct |
|---|---|
| florida_medicaid_ltc | 1 / 1 (100.0%) |
| florida_medicaid_mma | 2 / 3 (66.7%) |
| medicare_b | 1 / 1 (100.0%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 1 / 1 (100.0%) |
| Florida | 2 / 3 (66.7%) |
| both | 2 / 2 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds | Second opinion |
|---|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 5 / 5 | $0.1087 | 61.1 | inconsistent (agrees) |
| dc-005 | consistent | consistent | yes | n/a | $0.0710 | 43.0 | consistent (agrees) |
| dc-010 | not_settled | consistent | no | n/a | $0.0800 | 42.5 | not_settled (disagrees) |
| dc-012 | inconsistent | inconsistent | yes | 6 / 6 | $0.1957 | 76.1 | inconsistent (agrees) |
| dc-021 | inconsistent | inconsistent | yes | 4 / 4 | $0.1486 | 72.0 | inconsistent (agrees) |
| dc-030 | not_settled | not_settled | yes | 0 / 0 | $0.1276 | 56.9 | skipped |

Wrong cases:

- dc-010: intended not_settled, got consistent

Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):

| Case | Intended | Got | Stage | Why |
|---|---|---|---|---|
| dc-010 | not_settled | consistent | verdict | the hinge page fl-06 p6 was quoted (f2, f3, f6); the model proposed consistent, decisive fact "the behavior assessment and behavior plan for this authorization period support no more than 25 hours per week" (letter); exceptions: f4 unchecked |

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
