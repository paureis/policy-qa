# Denial-case evaluation, 2026-10-27

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 494.9 s.

| Measure | Value |
|---|---|
| Accuracy | 25 / 30 (83.3%) |
| Intended consistent | 7 / 10 (70.0%) |
| Intended inconsistent | 12 / 13 (92.3%) |
| Intended not_settled | 5 / 6 (83.3%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 81 / 81 (100.0%) over 22 letters |
| Letter claims struck | 0 / 81 (0.0%) |
| Critic revisions accepted | 11 of 22 reviewed |
| Cost per case | mean $0.0948, p50 $0.0983, total $2.8444 |
| Seconds per case | mean 46.7, p50 50.6 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |

| Program | Correct |
|---|---|
| florida_kidcare | 2 / 3 (66.7%) |
| florida_medicaid_ltc | 3 / 3 (100.0%) |
| florida_medicaid_mma | 8 / 11 (72.7%) |
| medicare_a | 2 / 2 (100.0%) |
| medicare_advantage | 3 / 3 (100.0%) |
| medicare_b | 4 / 4 (100.0%) |
| medicare_part_d | 2 / 3 (66.7%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 11 / 12 (91.7%) |
| Florida | 12 / 16 (75.0%) |
| both | 2 / 2 (100.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds |
|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 3 / 3 | $0.0939 | 59.9 |
| dc-002 | consistent | inconsistent | no | 6 / 6 | $0.1011 | 62.3 |
| dc-003 | consistent | inconsistent | no | 4 / 4 | $0.0932 | 65.4 |
| dc-004 | consistent | consistent | yes | n/a | $0.0791 | 36.5 |
| dc-005 | consistent | consistent | yes | n/a | $0.0680 | 31.9 |
| dc-006 | consistent | consistent | yes | n/a | $0.0718 | 32.8 |
| dc-007 | inconsistent | not_settled | no | 3 / 3 | $0.0918 | 50.4 |
| dc-008 | inconsistent | inconsistent | yes | 4 / 4 | $0.1110 | 53.4 |
| dc-009 | not_settled | not_settled | yes | 4 / 4 | $0.1105 | 50.4 |
| dc-010 | not_settled | not_settled | yes | 3 / 3 | $0.1068 | 49.3 |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 |
| dc-012 | inconsistent | inconsistent | yes | 6 / 6 | $0.1644 | 58.7 |
| dc-013 | inconsistent | inconsistent | yes | 3 / 3 | $0.0994 | 50.8 |
| dc-014 | not_settled | not_settled | yes | 3 / 3 | $0.0958 | 46.8 |
| dc-015 | inconsistent | inconsistent | yes | 2 / 2 | $0.0868 | 42.7 |
| dc-016 | consistent | consistent | yes | n/a | $0.0639 | 30.7 |
| dc-017 | not_settled | inconsistent | no | 3 / 3 | $0.1023 | 54.0 |
| dc-018 | inconsistent | inconsistent | yes | 5 / 5 | $0.1072 | 48.1 |
| dc-019 | consistent | consistent | yes | n/a | $0.0772 | 31.2 |
| dc-020 | not_settled | not_settled | yes | 4 / 4 | $0.1080 | 52.9 |
| dc-021 | inconsistent | inconsistent | yes | 2 / 2 | $0.1216 | 56.7 |
| dc-022 | inconsistent | inconsistent | yes | 3 / 3 | $0.1094 | 52.4 |
| dc-023 | inconsistent | inconsistent | yes | 5 / 5 | $0.0972 | 52.5 |
| dc-024 | consistent | consistent | yes | n/a | $0.0644 | 29.7 |
| dc-025 | consistent | not_settled | no | 4 / 4 | $0.0865 | 48.5 |
| dc-026 | inconsistent | inconsistent | yes | 3 / 3 | $0.1083 | 53.5 |
| dc-027 | inconsistent | inconsistent | yes | 3 / 3 | $0.1025 | 54.5 |
| dc-028 | inconsistent | inconsistent | yes | 5 / 5 | $0.1094 | 51.1 |
| dc-029 | consistent | consistent | yes | n/a | $0.0674 | 33.2 |
| dc-030 | not_settled | not_settled | yes | 3 / 3 | $0.1453 | 60.0 |

Wrong cases:

- dc-002: intended consistent, got inconsistent
- dc-003: intended consistent, got inconsistent
- dc-007: intended inconsistent, got not_settled
- dc-017: intended not_settled, got inconsistent
- dc-025: intended consistent, got not_settled

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
