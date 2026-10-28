# Denial-case evaluation, 2026-10-28

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 494.2 s.

| Measure | Value |
|---|---|
| Accuracy | 26 / 30 (86.7%) |
| Intended consistent | 9 / 10 (90.0%) |
| Intended inconsistent | 11 / 13 (84.6%) |
| Intended not_settled | 5 / 6 (83.3%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 81 / 81 (100.0%) over 20 letters |
| Letter claims struck | 0 / 81 (0.0%) |
| Critic revisions accepted | 13 of 20 reviewed |
| Cost per case | mean $0.0973, p50 $0.1035, total $2.9188 |
| Seconds per case | mean 47.4, p50 50.0 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |

| Program | Correct |
|---|---|
| florida_kidcare | 2 / 3 (66.7%) |
| florida_medicaid_ltc | 3 / 3 (100.0%) |
| florida_medicaid_mma | 10 / 11 (90.9%) |
| medicare_a | 2 / 2 (100.0%) |
| medicare_advantage | 3 / 3 (100.0%) |
| medicare_b | 4 / 4 (100.0%) |
| medicare_part_d | 1 / 3 (33.3%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 10 / 12 (83.3%) |
| Florida | 14 / 16 (87.5%) |
| both | 2 / 2 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds |
|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 5 / 5 | $0.1147 | 78.0 |
| dc-002 | consistent | inconsistent | no | 5 / 5 | $0.1148 | 78.9 |
| dc-003 | consistent | consistent | yes | n/a | $0.0670 | 58.8 |
| dc-004 | consistent | consistent | yes | n/a | $0.0906 | 36.8 |
| dc-005 | consistent | consistent | yes | n/a | $0.1030 | 50.6 |
| dc-006 | consistent | consistent | yes | n/a | $0.0676 | 39.1 |
| dc-007 | inconsistent | inconsistent | yes | 4 / 4 | $0.1154 | 55.8 |
| dc-008 | inconsistent | not_settled | yes | 4 / 4 | $0.1184 | 58.9 |
| dc-009 | not_settled | not_settled | yes | 3 / 3 | $0.1040 | 46.6 |
| dc-010 | not_settled | not_settled | yes | 4 / 4 | $0.1152 | 53.0 |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 |
| dc-012 | inconsistent | inconsistent | yes | 4 / 4 | $0.1488 | 62.3 |
| dc-013 | inconsistent | inconsistent | yes | 5 / 5 | $0.1086 | 54.9 |
| dc-014 | not_settled | not_settled | yes | 4 / 4 | $0.0994 | 49.3 |
| dc-015 | inconsistent | inconsistent | yes | 2 / 2 | $0.0813 | 39.0 |
| dc-016 | consistent | consistent | yes | n/a | $0.0600 | 25.4 |
| dc-017 | not_settled | inconsistent | no | 4 / 4 | $0.1022 | 46.2 |
| dc-018 | inconsistent | inconsistent | yes | 5 / 5 | $0.1100 | 46.8 |
| dc-019 | consistent | consistent | yes | n/a | $0.0739 | 27.9 |
| dc-020 | not_settled | not_settled | yes | 4 / 4 | $0.1142 | 58.7 |
| dc-021 | inconsistent | inconsistent | yes | 5 / 5 | $0.1287 | 58.8 |
| dc-022 | inconsistent | inconsistent | yes | 5 / 5 | $0.0974 | 53.4 |
| dc-023 | inconsistent | inconsistent | yes | 6 / 6 | $0.1048 | 56.2 |
| dc-024 | consistent | consistent | yes | n/a | $0.0649 | 29.7 |
| dc-025 | consistent | consistent | yes | n/a | $0.0821 | 32.1 |
| dc-026 | inconsistent | not_settled | no | 2 / 2 | $0.0969 | 46.1 |
| dc-027 | inconsistent | not_settled | no | 4 / 4 | $0.1052 | 47.5 |
| dc-028 | inconsistent | inconsistent | yes | 4 / 4 | $0.1208 | 53.4 |
| dc-029 | consistent | consistent | yes | n/a | $0.0708 | 28.1 |
| dc-030 | not_settled | not_settled | yes | 2 / 2 | $0.1383 | 50.7 |

Wrong cases:

- dc-002: intended consistent, got inconsistent
- dc-017: intended not_settled, got inconsistent
- dc-026: intended inconsistent, got not_settled
- dc-027: intended inconsistent, got not_settled

Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):

| Case | Intended | Got | Stage | Why |
|---|---|---|---|---|
| dc-002 | consistent | inconsistent | verdict | the hinge page fl-04 p4 was quoted (f3); the model proposed inconsistent, decisive fact "Florida Medicaid covers private duty nursing up to 24 hours per day without an adult-specific exclusion, and MMA plans must not apply more stringent limits" (documents); exceptions: f5 unchecked |
| dc-017 | not_settled | inconsistent | verdict | the hinge page fl-27 p31 was quoted (f1, f3, f4, f6); the model proposed inconsistent, decisive fact "The prescriber specified "dispense as written" on the brand-name prescription." (letter); exceptions: f6 unchecked |
| dc-026 | inconsistent | not_settled | retrieval | no question's passages reached the hinge page fed-10 p14 (5 questions planned, plan from the model) |
| dc-027 | inconsistent | not_settled | verdict | the hinge page fed-10 p41 was quoted (f4); the model proposed not_settled, decisive fact "Whether the prescribed drug is on this plan's formulary list of covered drugs" (outside_documents); exceptions: f3 unchecked, f4 unchecked |

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
