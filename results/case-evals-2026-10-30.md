# Denial-case evaluation, 2026-10-30

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 493.6 s. Second opinion: meta-models/muse-spark-open-1026, 28 ran.

| Measure | Value |
|---|---|
| Accuracy | 26 / 30 (86.7%) |
| Intended consistent | 9 / 10 (90.0%) |
| Intended inconsistent | 12 / 13 (92.3%) |
| Intended not_settled | 4 / 6 (66.7%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 75 / 75 (100.0%) over 19 letters |
| Letter claims struck | 0 / 75 (0.0%) |
| Critic revisions accepted | 15 of 19 reviewed |
| Cost per case | mean $0.0935, p50 $0.0981, total $2.8062 |
| Seconds per case | mean 45.3, p50 49.0 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |
| Dual routes (side by side) | 3 / 3 (dc-012, dc-021, dc-030) |
| Second opinion agrees with the verdict | 28 / 28 (100.0%) of the cases where both ran |
| Second opinion right, verdict wrong | 0 |
| Verdict right, second opinion wrong | 0 |
| Second opinion cost per case | mean $0.0079 over 28 runs |
| Second opinion failed, timed out, skipped | 0, 0, 2 |
| Second opinion skip reasons | the chain did not reach the verdict (1); the plan is outside the corpus: the verdict makes no model call (1) |

| Program | Correct |
|---|---|
| florida_kidcare | 2 / 3 (66.7%) |
| florida_medicaid_ltc | 2 / 3 (66.7%) |
| florida_medicaid_mma | 9 / 11 (81.8%) |
| medicare_a | 2 / 2 (100.0%) |
| medicare_advantage | 3 / 3 (100.0%) |
| medicare_b | 4 / 4 (100.0%) |
| medicare_part_d | 3 / 3 (100.0%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 12 / 12 (100.0%) |
| Florida | 12 / 16 (75.0%) |
| both | 2 / 2 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds | Second opinion |
|---|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 5 / 5 | $0.1013 | 65.5 | inconsistent (agrees) |
| dc-002 | consistent | inconsistent | no | 5 / 5 | $0.1179 | 69.3 | inconsistent (agrees) |
| dc-003 | consistent | consistent | yes | n/a | $0.0762 | 39.8 | consistent (agrees) |
| dc-004 | consistent | consistent | yes | n/a | $0.0791 | 31.0 | consistent (agrees) |
| dc-005 | consistent | consistent | yes | n/a | $0.0691 | 32.0 | consistent (agrees) |
| dc-006 | consistent | consistent | yes | n/a | $0.0798 | 32.2 | consistent (agrees) |
| dc-007 | inconsistent | inconsistent | yes | 5 / 5 | $0.1206 | 63.0 | inconsistent (agrees) |
| dc-008 | inconsistent | inconsistent | yes | 4 / 4 | $0.1028 | 51.1 | inconsistent (agrees) |
| dc-009 | not_settled | consistent | no | n/a | $0.0774 | 36.7 | consistent (agrees) |
| dc-010 | not_settled | not_settled | yes | 4 / 4 | $0.1126 | 56.4 | not_settled (agrees) |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 | skipped |
| dc-012 | inconsistent | inconsistent | yes | 5 / 5 | $0.1451 | 62.0 | inconsistent (agrees) |
| dc-013 | inconsistent | not_settled | no | 3 / 3 | $0.0978 | 55.8 | not_settled (agrees) |
| dc-014 | not_settled | not_settled | yes | 5 / 5 | $0.0957 | 48.4 | not_settled (agrees) |
| dc-015 | inconsistent | inconsistent | yes | 5 / 5 | $0.0886 | 49.0 | inconsistent (agrees) |
| dc-016 | consistent | consistent | yes | n/a | $0.0792 | 30.2 | consistent (agrees) |
| dc-017 | not_settled | inconsistent | no | 3 / 3 | $0.1029 | 46.5 | inconsistent (agrees) |
| dc-018 | inconsistent | inconsistent | yes | 6 / 6 | $0.1096 | 52.2 | inconsistent (agrees) |
| dc-019 | consistent | consistent | yes | n/a | $0.0557 | 27.5 | consistent (agrees) |
| dc-020 | not_settled | not_settled | yes | 3 / 3 | $0.0984 | 50.1 | not_settled (agrees) |
| dc-021 | inconsistent | inconsistent | yes | 2 / 2 | $0.1286 | 53.2 | inconsistent (agrees) |
| dc-022 | inconsistent | inconsistent | yes | 5 / 5 | $0.0938 | 54.5 | inconsistent (agrees) |
| dc-023 | inconsistent | inconsistent | yes | 4 / 4 | $0.1059 | 48.9 | inconsistent (agrees) |
| dc-024 | consistent | consistent | yes | n/a | $0.0590 | 26.2 | consistent (agrees) |
| dc-025 | consistent | consistent | yes | n/a | $0.0750 | 30.0 | consistent (agrees) |
| dc-026 | inconsistent | inconsistent | yes | 3 / 3 | $0.1025 | 50.2 | inconsistent (agrees) |
| dc-027 | inconsistent | inconsistent | yes | 3 / 3 | $0.1006 | 55.9 | inconsistent (agrees) |
| dc-028 | inconsistent | inconsistent | yes | 3 / 3 | $0.1099 | 48.6 | inconsistent (agrees) |
| dc-029 | consistent | consistent | yes | n/a | $0.0784 | 35.5 | consistent (agrees) |
| dc-030 | not_settled | not_settled | yes | 2 / 2 | $0.1426 | 56.5 | skipped |

Wrong cases:

- dc-002: intended consistent, got inconsistent
- dc-009: intended not_settled, got consistent
- dc-013: intended inconsistent, got not_settled
- dc-017: intended not_settled, got inconsistent

Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):

| Case | Intended | Got | Stage | Why |
|---|---|---|---|---|
| dc-002 | consistent | inconsistent | retrieval | no question's passages reached the hinge page fl-04 p4 (6 questions planned, plan from the model) |
| dc-009 | not_settled | consistent | verdict | the hinge page fl-10 p5 was quoted (f1, f2, f4); the model proposed consistent, decisive fact "The request is for 300 test strips for one month, which is more than the 200-per-month limit, without an approved prior authorization for the higher quantity" (letter); exceptions: f4 unchecked |
| dc-013 | inconsistent | not_settled | retrieval | no question's passages reached the hinge page fl-16 p7 (5 questions planned, plan from the model) |
| dc-017 | not_settled | inconsistent | verdict | the hinge page fl-27 p31 was quoted (f1, f2, f3, f6); the model proposed inconsistent, decisive fact "The prescription specified "dispense as written"" (letter); exceptions: f6 unchecked |

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
