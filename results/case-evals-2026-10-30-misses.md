# Denial-case evaluation, 2026-10-30

Model: muse-spark-1.3 (reasoning effort: low). Critic rounds: 1. Cases: 4. Wall time: 126.7 s. Second opinion: meta-models/muse-spark-open-1026, 4 ran.

| Measure | Value |
|---|---|
| Accuracy | 1 / 4 (25.0%) |
| Intended consistent | 0 / 1 (0.0%) |
| Intended inconsistent | 1 / 1 (100.0%) |
| Intended not_settled | 0 / 2 (0.0%) |
| Refusal on the medical question (dc-011) | not run |
| Letter claims verified | 16 / 16 (100.0%) over 3 letters |
| Letter claims struck | 0 / 16 (0.0%) |
| Critic revisions accepted | 1 of 3 reviewed |
| Cost per case | mean $0.1029, p50 $0.1031, total $0.4117 |
| Seconds per case | mean 58.4, p50 56.7 |
| Errors (scored wrong) | 0 |
| Template letters (left out of the rates) | 0 |
| Critic failures (letter kept as drafted) | 0 |
| Dual routes (side by side) | 0 |
| Second opinion agrees with the verdict | 3 / 4 (75.0%) of the cases where both ran |
| Second opinion right, verdict wrong | 1 (dc-009) |
| Verdict right, second opinion wrong | 0 |
| Second opinion cost per case | mean $0.0084 over 4 runs |
| Second opinion failed, timed out, skipped | 0, 0, 0 |

| Program | Correct |
|---|---|
| florida_kidcare | 0 / 1 (0.0%) |
| florida_medicaid_ltc | 1 / 1 (100.0%) |
| florida_medicaid_mma | 0 / 2 (0.0%) |

| Jurisdiction | Correct |
|---|---|
| Florida | 1 / 4 (25.0%) |

| Case | Intended | Got | Correct | Verified / claims | Cost | Seconds | Second opinion |
|---|---|---|---|---|---|---|---|
| dc-002 | consistent | not_settled | no | 5 / 5 | $0.1078 | 70.1 | not_settled (agrees) |
| dc-009 | not_settled | consistent | no | n/a | $0.0874 | 49.9 | not_settled (disagrees) |
| dc-013 | inconsistent | inconsistent | yes | 7 / 7 | $0.1180 | 57.2 | inconsistent (agrees) |
| dc-017 | not_settled | inconsistent | no | 4 / 4 | $0.0985 | 56.2 | inconsistent (agrees) |

Wrong cases:

- dc-002: intended consistent, got not_settled
- dc-009: intended not_settled, got consistent
- dc-017: intended not_settled, got inconsistent

Misses by stage (the stage each wrong case traces to; rule in policyqa/case_evals.py, miss_stage):

| Case | Intended | Got | Stage | Why |
|---|---|---|---|---|
| dc-002 | consistent | not_settled | retrieval | no question's passages reached the hinge page fl-04 p4 (5 questions planned, plan from the model) |
| dc-009 | not_settled | consistent | verdict | the hinge page fl-10 p5 was quoted (f1, f2, f3, f5); the model proposed consistent, decisive fact "The request was for 300 test strips for one month" (letter); exceptions: f5 unchecked |
| dc-017 | not_settled | inconsistent | verdict | the hinge page fl-27 p31 was quoted (f1, f2, f3, f4); the model proposed inconsistent, decisive fact "the prescription specified "dispense as written"" (letter); exceptions: f3 unchecked |

Scoring: correct when the verdict equals the intended outcome or a listed alternate (dc-008 not_settled, dc-020 consistent); dc-011 is correct only when intake refuses it as out_of_scope; errors (a failed stage, a verdict model failure, an investigation with no supported finding) and refusals of other letters count as wrong.
