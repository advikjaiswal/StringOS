# StringOS Reliability Benchmark

Deterministic evaluation over 2500 total trials per policy (500 trials for each of 5 seeds) with a 35% transient failure probability per attempt and seeds 11, 17, 23, 29, 31.

| Policy | Task success | Recovery after first failure | Average attempts |
| --- | ---: | ---: | ---: |
| retry_budget_0 | 64.7% | 0.0% | 1.00 |
| retry_budget_1 | 88.4% | 67.0% | 1.35 |
| retry_budget_2 | 95.6% | 87.5% | 1.47 |
| retry_budget_3 | 98.4% | 95.6% | 1.51 |

## Plan validation

Detected 4 of 4 invalid plans before tool execution (100.0%).

This benchmark uses deterministic synthetic failures. It measures runtime behaviour, not language-model planning quality or production reliability.
