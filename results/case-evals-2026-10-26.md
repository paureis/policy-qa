# Denial-case evaluation, 2026-10-26

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 368.4 s.

| Measure | Value |
|---|---|
| Accuracy | 22 / 30 (73.3%) |
| Intended consistent | 9 / 10 (90.0%) |
| Intended inconsistent | 10 / 13 (76.9%) |
| Intended not_settled | 2 / 6 (33.3%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 61 / 61 (100.0%) over 16 letters |
| Letter claims struck | 0 / 61 (0.0%) |
| Critic revisions accepted | 9 of 16 reviewed |
| Cost per case | mean $0.0835, p50 $0.0882, total $2.5041 |
| Seconds per case | mean 34.1, p50 38.3 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |

| Program | Correct |
|---|---|
| florida_kidcare | 2 / 3 (66.7%) |
| florida_medicaid_ltc | 2 / 3 (66.7%) |
| florida_medicaid_mma | 9 / 11 (81.8%) |
| medicare_a | 2 / 2 (100.0%) |
| medicare_advantage | 3 / 3 (100.0%) |
| medicare_b | 2 / 4 (50.0%) |
| medicare_part_d | 2 / 3 (66.7%) |
| unknown | 0 / 1 (0.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 9 / 12 (75.0%) |
| Florida | 12 / 16 (75.0%) |
| both | 1 / 2 (50.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds |
|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 4 / 4 | $0.0998 | 50.7 |
| dc-002 | consistent | not_settled | no | 5 / 5 | $0.0981 | 47.9 |
| dc-003 | consistent | consistent | yes | n/a | $0.0851 | 36.2 |
| dc-004 | consistent | consistent | yes | n/a | $0.0776 | 24.1 |
| dc-005 | consistent | consistent | yes | n/a | $0.1059 | 37.4 |
| dc-006 | consistent | consistent | yes | n/a | $0.0823 | 27.5 |
| dc-007 | inconsistent | inconsistent | yes | 5 / 5 | $0.0997 | 40.1 |
| dc-008 | inconsistent | not_settled | yes | 4 / 4 | $0.0968 | 40.1 |
| dc-009 | not_settled | consistent | no | n/a | $0.0598 | 23.8 |
| dc-010 | not_settled | not_settled | yes | 3 / 3 | $0.0954 | 40.3 |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 |
| dc-012 | inconsistent | inconsistent | yes | 4 / 4 | $0.1177 | 44.4 |
| dc-013 | inconsistent | inconsistent | yes | 5 / 5 | $0.0929 | 42.7 |
| dc-014 | not_settled | consistent | no | n/a | $0.0635 | 24.4 |
| dc-015 | inconsistent | inconsistent | yes | 2 / 2 | $0.0745 | 35.9 |
| dc-016 | consistent | consistent | yes | n/a | $0.0594 | 23.2 |
| dc-017 | not_settled | inconsistent | no | 3 / 3 | $0.0948 | 41.4 |
| dc-018 | inconsistent | not_settled | no | 3 / 3 | $0.0999 | 43.2 |
| dc-019 | consistent | consistent | yes | n/a | $0.0645 | 25.2 |
| dc-020 | not_settled | consistent | yes | n/a | $0.0716 | 26.0 |
| dc-021 | inconsistent | not_settled | no | 3 / 3 | $0.1019 | 43.8 |
| dc-022 | inconsistent | inconsistent | yes | 2 / 2 | $0.0856 | 39.4 |
| dc-023 | inconsistent | inconsistent | yes | 6 / 6 | $0.0909 | 41.5 |
| dc-024 | consistent | consistent | yes | n/a | $0.0624 | 21.2 |
| dc-025 | consistent | consistent | yes | n/a | $0.0610 | 26.2 |
| dc-026 | inconsistent | consistent | no | n/a | $0.0660 | 23.5 |
| dc-027 | inconsistent | inconsistent | yes | 4 / 4 | $0.0969 | 39.9 |
| dc-028 | inconsistent | inconsistent | yes | 4 / 4 | $0.0994 | 39.3 |
| dc-029 | consistent | consistent | yes | n/a | $0.0736 | 26.6 |
| dc-030 | not_settled | inconsistent | no | 4 / 4 | $0.1273 | 48.5 |

Wrong cases:

- dc-002: intended consistent, got not_settled
- dc-009: intended not_settled, got consistent
- dc-014: intended not_settled, got consistent
- dc-017: intended not_settled, got inconsistent
- dc-018: intended inconsistent, got not_settled
- dc-021: intended inconsistent, got not_settled
- dc-026: intended inconsistent, got consistent
- dc-030: intended not_settled, got inconsistent

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
