# Denial-case evaluation, 2026-10-27

Model: accounts/fireworks/models/muse-spark-open (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 1778.8 s.

| Measure | Value |
|---|---|
| Accuracy | 23 / 30 (76.7%) |
| Intended consistent | 9 / 10 (90.0%) |
| Intended inconsistent | 9 / 13 (69.2%) |
| Intended not_settled | 4 / 6 (66.7%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 67 / 67 (100.0%) over 19 letters |
| Letter claims struck | 0 / 67 (0.0%) |
| Critic revisions accepted | 5 of 19 reviewed |
| Cost per case | mean $0.0669, p50 $0.0708, total $2.0068 |
| Seconds per case | mean 173.9, p50 145.8 |
| Errors (scored wrong) | 3 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |

| Program | Correct |
|---|---|
| florida_kidcare | 1 / 3 (33.3%) |
| florida_medicaid_ltc | 3 / 3 (100.0%) |
| florida_medicaid_mma | 9 / 11 (81.8%) |
| medicare_a | 2 / 2 (100.0%) |
| medicare_advantage | 2 / 3 (66.7%) |
| medicare_b | 3 / 4 (75.0%) |
| medicare_part_d | 2 / 3 (66.7%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 9 / 12 (75.0%) |
| Florida | 12 / 16 (75.0%) |
| both | 2 / 2 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds |
|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 2 / 2 | $0.0740 | 140.3 |
| dc-002 | consistent | consistent | yes | n/a | $0.0686 | 129.0 |
| dc-003 | consistent | inconsistent | no | 4 / 4 | $0.0679 | 144.7 |
| dc-004 | consistent | consistent | yes | n/a | $0.0490 | 298.3 |
| dc-005 | consistent | consistent | yes | n/a | $0.0490 | 220.3 |
| dc-006 | consistent | consistent | yes | n/a | $0.0622 | 69.0 |
| dc-007 | inconsistent | inconsistent | yes | 3 / 3 | $0.0737 | 283.2 |
| dc-008 | inconsistent | inconsistent | yes | 3 / 3 | $0.0835 | 150.0 |
| dc-009 | not_settled | error (not_settled) | no | 5 / 5 | $0.0750 | 267.2 |
| dc-010 | not_settled | not_settled | yes | 3 / 3 | $0.0738 | 232.9 |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 |
| dc-012 | inconsistent | inconsistent | yes | 5 / 5 | $0.0977 | 378.2 |
| dc-013 | inconsistent | inconsistent | yes | 3 / 3 | $0.0789 | 135.2 |
| dc-014 | not_settled | not_settled | yes | 4 / 4 | $0.0708 | 252.5 |
| dc-015 | inconsistent | not_settled | no | 3 / 3 | $0.0618 | 278.4 |
| dc-016 | consistent | consistent | yes | n/a | $0.0523 | 93.6 |
| dc-017 | not_settled | inconsistent | no | 4 / 4 | $0.0787 | 188.9 |
| dc-018 | inconsistent | error | no | n/a | $0.0000 | 120.4 |
| dc-019 | consistent | consistent | yes | n/a | $0.0550 | 85.3 |
| dc-020 | not_settled | not_settled | yes | 5 / 5 | $0.0736 | 138.8 |
| dc-021 | inconsistent | inconsistent | yes | 3 / 3 | $0.1063 | 147.0 |
| dc-022 | inconsistent | error (not_settled) | no | 3 / 3 | $0.0636 | 240.4 |
| dc-023 | inconsistent | inconsistent | yes | 3 / 3 | $0.0708 | 242.1 |
| dc-024 | consistent | consistent | yes | n/a | $0.0559 | 83.9 |
| dc-025 | consistent | consistent | yes | n/a | $0.0553 | 88.0 |
| dc-026 | inconsistent | not_settled | no | 2 / 2 | $0.0846 | 300.7 |
| dc-027 | inconsistent | inconsistent | yes | 4 / 4 | $0.0730 | 127.2 |
| dc-028 | inconsistent | inconsistent | yes | 4 / 4 | $0.0819 | 156.5 |
| dc-029 | consistent | consistent | yes | n/a | $0.0558 | 92.0 |
| dc-030 | not_settled | not_settled | yes | 4 / 4 | $0.1141 | 131.6 |

Wrong cases:

- dc-003: intended consistent, got inconsistent
- dc-009: intended not_settled, error: verdict: ReadTimeout: The read operation timed out
- dc-015: intended inconsistent, got not_settled
- dc-017: intended not_settled, got inconsistent
- dc-018: intended inconsistent, error: ReadTimeout: The read operation timed out
- dc-022: intended inconsistent, error: verdict: ReadTimeout: The read operation timed out
- dc-026: intended inconsistent, got not_settled

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
