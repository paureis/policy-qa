# Denial-case evaluation, 2026-10-28

Model: meta-models/muse-spark-open-1026 (reasoning effort: low). Critic rounds: 1. Cases: 30. Wall time: 262.3 s.

| Measure | Value |
|---|---|
| Accuracy | 27 / 30 (90.0%) |
| Intended consistent | 9 / 10 (90.0%) |
| Intended inconsistent | 12 / 13 (92.3%) |
| Intended not_settled | 5 / 6 (83.3%) |
| Intended out_of_scope | 1 / 1 (100.0%) |
| Refusal on the medical question (dc-011) | correct |
| Letter claims verified | 71 / 71 (100.0%) over 19 letters |
| Letter claims struck | 0 / 71 (0.0%) |
| Critic revisions accepted | 12 of 19 reviewed |
| Cost per case | mean $0.0680, p50 $0.0721, total $2.0405 |
| Seconds per case | mean 24.7, p50 25.6 |
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
| medicare_b | 3 / 4 (75.0%) |
| medicare_part_d | 3 / 3 (100.0%) |
| unknown | 1 / 1 (100.0%) |

| Jurisdiction | Correct |
|---|---|
| Federal | 12 / 12 (100.0%) |
| Florida | 14 / 16 (87.5%) |
| both | 1 / 2 (50.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds |
|---|---|---|---|---|---|---|
| dc-001 | inconsistent | inconsistent | yes | 4 / 4 | $0.0794 | 41.1 |
| dc-002 | consistent | inconsistent | no | 5 / 5 | $0.0917 | 45.1 |
| dc-003 | consistent | consistent | yes | n/a | $0.0571 | 32.0 |
| dc-004 | consistent | consistent | yes | n/a | $0.0542 | 17.7 |
| dc-005 | consistent | consistent | yes | n/a | $0.0615 | 20.1 |
| dc-006 | consistent | consistent | yes | n/a | $0.0562 | 19.8 |
| dc-007 | inconsistent | inconsistent | yes | 3 / 3 | $0.0752 | 25.0 |
| dc-008 | inconsistent | inconsistent | yes | 3 / 3 | $0.0829 | 28.8 |
| dc-009 | not_settled | not_settled | yes | 3 / 3 | $0.0754 | 27.7 |
| dc-010 | not_settled | not_settled | yes | 5 / 5 | $0.0875 | 30.5 |
| dc-011 | out_of_scope | refused (out_of_scope) | yes | n/a | $0.0000 | 0.0 |
| dc-012 | inconsistent | inconsistent | yes | 4 / 4 | $0.1141 | 34.4 |
| dc-013 | inconsistent | inconsistent | yes | 5 / 5 | $0.0745 | 28.1 |
| dc-014 | not_settled | not_settled | yes | 5 / 5 | $0.0814 | 27.7 |
| dc-015 | inconsistent | inconsistent | yes | 2 / 2 | $0.0591 | 23.2 |
| dc-016 | consistent | consistent | yes | n/a | $0.0627 | 18.3 |
| dc-017 | not_settled | inconsistent | no | 4 / 4 | $0.0651 | 23.5 |
| dc-018 | inconsistent | inconsistent | yes | 3 / 3 | $0.0748 | 26.4 |
| dc-019 | consistent | consistent | yes | n/a | $0.0509 | 18.9 |
| dc-020 | not_settled | not_settled | yes | 5 / 5 | $0.0739 | 24.9 |
| dc-021 | inconsistent | refused (not_a_denial_letter) | no | n/a | $0.0000 | 4.8 |
| dc-022 | inconsistent | inconsistent | yes | 3 / 3 | $0.0666 | 25.3 |
| dc-023 | inconsistent | inconsistent | yes | 3 / 3 | $0.0812 | 30.1 |
| dc-024 | consistent | consistent | yes | n/a | $0.0555 | 16.6 |
| dc-025 | consistent | consistent | yes | n/a | $0.0507 | 18.0 |
| dc-026 | inconsistent | inconsistent | yes | 3 / 3 | $0.0702 | 25.9 |
| dc-027 | inconsistent | inconsistent | yes | 4 / 4 | $0.0911 | 31.6 |
| dc-028 | inconsistent | inconsistent | yes | 4 / 4 | $0.0842 | 27.3 |
| dc-029 | consistent | consistent | yes | n/a | $0.0588 | 18.0 |
| dc-030 | not_settled | not_settled | yes | 3 / 3 | $0.1045 | 31.1 |

Wrong cases:

- dc-002: intended consistent, got inconsistent
- dc-017: intended not_settled, got inconsistent
- dc-021: intended inconsistent, refused (not_a_denial_letter)

Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):

| Case | Intended | Got | Stage | Why |
|---|---|---|---|---|
| dc-002 | consistent | inconsistent | answer | the hinge page fl-04 p4 reached the model (f3) but no verified quote came from it |
| dc-017 | not_settled | inconsistent | verdict | the hinge page fl-27 p31 was quoted (f1, f2, f3, f4); the model proposed inconsistent, decisive fact "whether the prescriber wrote "dispense as written" on the prescription for the brand-name drug" (letter); exceptions: f4 unchecked |
| dc-021 | inconsistent | none | intake | intake refused the letter (not_a_denial_letter) |

dc-030 route: program unknown (unknown, as expected outside the corpus; the router said no corpus document governs it). Reason given: The letter is from Sample Employer Health Plan, a plan outside the public programs in the corpus (Florida Medicaid, KidCare, Medicare). No document in the corpus governs it; the Florida Medicaid and federal Medicare rules are checked for reference only.

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
