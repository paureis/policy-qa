# Denial-case evaluation, 2026-10-29

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 415.4 s. Second opinion: meta-models/muse-spark-open-1026, 28 ran.

| Measure | Value |
|---|---|
| Accuracy | 28 / 30 (93.3%) |
| Intended consistent | 9 / 10 (90.0%) |
| Intended inconsistent | 13 / 13 (100.0%) |
| Intended not_settled | 5 / 6 (83.3%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 71 / 71 (100.0%) over 20 letters |
| Letter claims struck | 0 / 71 (0.0%) |
| Critic revisions accepted | 12 of 20 reviewed |
| Cost per case | mean $0.0942, p50 $0.0979, total $2.8267 |
| Seconds per case | mean 38.5, p50 41.7 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |
| Second opinion agrees with the verdict | 26 / 28 (92.9%) of the cases where both ran |
| Second opinion right, verdict wrong | 0 |
| Verdict right, second opinion wrong | 1 (dc-009) |
| Second opinion cost per case | mean $0.0078 over 28 runs |
| Second opinion failed, timed out, skipped | 0, 0, 2 |
| Second opinion skip reasons | the chain did not reach the verdict (1); the plan is outside the corpus: the verdict makes no model call (1) |

| Program | Correct |
|---|---|
| florida_kidcare | 2 / 3 (66.7%) |
| florida_medicaid_ltc | 3 / 3 (100.0%) |
| florida_medicaid_mma | 10 / 11 (90.9%) |
| medicare_a | 2 / 2 (100.0%) |
| medicare_advantage | 3 / 3 (100.0%) |
| medicare_b | 4 / 4 (100.0%) |
| medicare_part_d | 3 / 3 (100.0%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 12 / 12 (100.0%) |
| Florida | 14 / 16 (87.5%) |
| both | 2 / 2 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds | Second opinion |
|---|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 4 / 4 | $0.1034 | 54.7 | inconsistent (agrees) |
| dc-002 | consistent | inconsistent | no | 5 / 5 | $0.0991 | 57.2 | inconsistent (agrees) |
| dc-003 | consistent | consistent | yes | n/a | $0.0631 | 31.7 | consistent (agrees) |
| dc-004 | consistent | consistent | yes | n/a | $0.0868 | 26.6 | consistent (agrees) |
| dc-005 | consistent | consistent | yes | n/a | $0.0942 | 32.2 | consistent (agrees) |
| dc-006 | consistent | consistent | yes | n/a | $0.0641 | 26.3 | consistent (agrees) |
| dc-007 | inconsistent | inconsistent | yes | 4 / 4 | $0.0985 | 39.8 | inconsistent (agrees) |
| dc-008 | inconsistent | not_settled | yes | 3 / 3 | $0.0978 | 40.7 | inconsistent (disagrees) |
| dc-009 | not_settled | not_settled | yes | 3 / 3 | $0.1079 | 42.7 | consistent (disagrees) |
| dc-010 | not_settled | not_settled | yes | 3 / 3 | $0.1179 | 46.1 | not_settled (agrees) |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 | skipped |
| dc-012 | inconsistent | inconsistent | yes | 6 / 6 | $0.1670 | 57.9 | inconsistent (agrees) |
| dc-013 | inconsistent | inconsistent | yes | 4 / 4 | $0.1140 | 46.3 | inconsistent (agrees) |
| dc-014 | not_settled | not_settled | yes | 4 / 4 | $0.0957 | 39.2 | not_settled (agrees) |
| dc-015 | inconsistent | inconsistent | yes | 3 / 3 | $0.0864 | 44.0 | inconsistent (agrees) |
| dc-016 | consistent | consistent | yes | n/a | $0.0722 | 27.3 | consistent (agrees) |
| dc-017 | not_settled | inconsistent | no | 2 / 2 | $0.0992 | 43.9 | inconsistent (agrees) |
| dc-018 | inconsistent | inconsistent | yes | 5 / 5 | $0.0980 | 42.2 | inconsistent (agrees) |
| dc-019 | consistent | consistent | yes | n/a | $0.0797 | 28.0 | consistent (agrees) |
| dc-020 | not_settled | not_settled | yes | 4 / 4 | $0.1177 | 41.1 | not_settled (agrees) |
| dc-021 | inconsistent | inconsistent | yes | 2 / 2 | $0.1205 | 47.0 | inconsistent (agrees) |
| dc-022 | inconsistent | inconsistent | yes | 4 / 4 | $0.1059 | 42.5 | inconsistent (agrees) |
| dc-023 | inconsistent | inconsistent | yes | 4 / 4 | $0.1058 | 44.9 | inconsistent (agrees) |
| dc-024 | consistent | consistent | yes | n/a | $0.0625 | 25.5 | consistent (agrees) |
| dc-025 | consistent | consistent | yes | n/a | $0.0661 | 25.3 | consistent (agrees) |
| dc-026 | inconsistent | inconsistent | yes | 4 / 4 | $0.0958 | 43.9 | inconsistent (agrees) |
| dc-027 | inconsistent | inconsistent | yes | 3 / 3 | $0.1034 | 46.0 | inconsistent (agrees) |
| dc-028 | inconsistent | inconsistent | yes | 4 / 4 | $0.0868 | 34.7 | inconsistent (agrees) |
| dc-029 | consistent | consistent | yes | n/a | $0.0706 | 27.3 | consistent (agrees) |
| dc-030 | not_settled | not_settled | yes | 0 / 0 | $0.1466 | 49.4 | skipped |

Wrong cases:

- dc-002: intended consistent, got inconsistent
- dc-017: intended not_settled, got inconsistent

Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):

| Case | Intended | Got | Stage | Why |
|---|---|---|---|---|
| dc-002 | consistent | inconsistent | retrieval | no question's passages reached the hinge page fl-04 p4 (5 questions planned, plan from the model) |
| dc-017 | not_settled | inconsistent | verdict | the hinge page fl-27 p31 was quoted (f1, f2, f3); the model proposed inconsistent, decisive fact "The prescription specified "dispense as written"." (letter); exceptions: f3 unchecked |

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
