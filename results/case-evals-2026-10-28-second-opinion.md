# Denial-case evaluation, 2026-10-28

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 526.2 s. Second opinion: meta-models/muse-spark-open-1026, 28 ran.

| Measure | Value |
|---|---|
| Accuracy | 27 / 30 (90.0%) |
| Intended consistent | 9 / 10 (90.0%) |
| Intended inconsistent | 12 / 13 (92.3%) |
| Intended not_settled | 5 / 6 (83.3%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 81 / 81 (100.0%) over 20 letters |
| Letter claims struck | 0 / 81 (0.0%) |
| Critic revisions accepted | 14 of 20 reviewed |
| Cost per case | mean $0.0956, p50 $0.1010, total $2.8681 |
| Seconds per case | mean 48.6, p50 53.4 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |
| Second opinion agrees with the verdict | 27 / 28 (96.4%) of the cases where both ran |
| Second opinion right, verdict wrong | 0 |
| Verdict right, second opinion wrong | 1 (dc-009) |
| Second opinion cost per case | mean $0.0079 over 28 runs |
| Second opinion failed, timed out, skipped | 0, 0, 2 |
| Second opinion skip reasons | no reason recorded (1); the plan is outside the corpus: the verdict makes no model call (1) |

| Program | Correct |
|---|---|
| florida_kidcare | 2 / 3 (66.7%) |
| florida_medicaid_ltc | 3 / 3 (100.0%) |
| florida_medicaid_mma | 10 / 11 (90.9%) |
| medicare_a | 2 / 2 (100.0%) |
| medicare_advantage | 3 / 3 (100.0%) |
| medicare_b | 4 / 4 (100.0%) |
| medicare_part_d | 2 / 3 (66.7%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 11 / 12 (91.7%) |
| Florida | 14 / 16 (87.5%) |
| both | 2 / 2 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds | Second opinion |
|---|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 5 / 5 | $0.1038 | 60.8 | inconsistent (agrees) |
| dc-002 | consistent | not_settled | no | 4 / 4 | $0.0998 | 68.9 | not_settled (agrees) |
| dc-003 | consistent | consistent | yes | n/a | $0.0647 | 39.2 | consistent (agrees) |
| dc-004 | consistent | consistent | yes | n/a | $0.0663 | 31.0 | consistent (agrees) |
| dc-005 | consistent | consistent | yes | n/a | $0.0970 | 38.5 | consistent (agrees) |
| dc-006 | consistent | consistent | yes | n/a | $0.0818 | 34.0 | consistent (agrees) |
| dc-007 | inconsistent | inconsistent | yes | 5 / 5 | $0.1076 | 53.5 | inconsistent (agrees) |
| dc-008 | inconsistent | inconsistent | yes | 5 / 5 | $0.1046 | 50.9 | inconsistent (agrees) |
| dc-009 | not_settled | not_settled | yes | 4 / 4 | $0.1103 | 56.4 | consistent (disagrees) |
| dc-010 | not_settled | not_settled | yes | 2 / 2 | $0.1084 | 50.9 | not_settled (agrees) |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 | skipped |
| dc-012 | inconsistent | inconsistent | yes | 3 / 3 | $0.1588 | 59.8 | inconsistent (agrees) |
| dc-013 | inconsistent | inconsistent | yes | 5 / 5 | $0.1181 | 65.8 | inconsistent (agrees) |
| dc-014 | not_settled | not_settled | yes | 5 / 5 | $0.1022 | 56.3 | not_settled (agrees) |
| dc-015 | inconsistent | inconsistent | yes | 3 / 3 | $0.0920 | 55.8 | inconsistent (agrees) |
| dc-016 | consistent | consistent | yes | n/a | $0.0576 | 26.7 | consistent (agrees) |
| dc-017 | not_settled | inconsistent | no | 3 / 3 | $0.0984 | 53.2 | inconsistent (agrees) |
| dc-018 | inconsistent | inconsistent | yes | 4 / 4 | $0.1238 | 58.5 | inconsistent (agrees) |
| dc-019 | consistent | consistent | yes | n/a | $0.0758 | 31.2 | consistent (agrees) |
| dc-020 | not_settled | not_settled | yes | 4 / 4 | $0.1022 | 55.4 | not_settled (agrees) |
| dc-021 | inconsistent | inconsistent | yes | 4 / 4 | $0.1252 | 59.0 | inconsistent (agrees) |
| dc-022 | inconsistent | inconsistent | yes | 6 / 6 | $0.1057 | 66.3 | inconsistent (agrees) |
| dc-023 | inconsistent | inconsistent | yes | 6 / 6 | $0.1064 | 56.3 | inconsistent (agrees) |
| dc-024 | consistent | consistent | yes | n/a | $0.0631 | 30.4 | consistent (agrees) |
| dc-025 | consistent | consistent | yes | n/a | $0.0769 | 30.8 | consistent (agrees) |
| dc-026 | inconsistent | inconsistent | yes | 4 / 4 | $0.0987 | 51.2 | inconsistent (agrees) |
| dc-027 | inconsistent | not_settled | no | 4 / 4 | $0.1134 | 74.5 | not_settled (agrees) |
| dc-028 | inconsistent | inconsistent | yes | 5 / 5 | $0.0949 | 50.8 | inconsistent (agrees) |
| dc-029 | consistent | consistent | yes | n/a | $0.0730 | 32.7 | consistent (agrees) |
| dc-030 | not_settled | not_settled | yes | 0 / 0 | $0.1377 | 58.3 | skipped |

Wrong cases:

- dc-002: intended consistent, got not_settled
- dc-017: intended not_settled, got inconsistent
- dc-027: intended inconsistent, got not_settled

Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):

| Case | Intended | Got | Stage | Why |
|---|---|---|---|---|
| dc-002 | consistent | not_settled | retrieval | no question's passages reached the hinge page fl-04 p4 (5 questions planned, plan from the model) |
| dc-017 | not_settled | inconsistent | verdict | the hinge page fl-27 p31 was quoted (f1, f2, f3); the model proposed inconsistent, decisive fact "whether the prescription specified "dispense as written"" (letter); exceptions: f3 unchecked |
| dc-027 | inconsistent | not_settled | verdict | the hinge page fed-10 p41 was quoted (f1, f3); the model proposed not_settled, decisive fact "whether a formulary exception was approved for this non-formulary drug" (payer_determination); exceptions: f3 unchecked |

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
