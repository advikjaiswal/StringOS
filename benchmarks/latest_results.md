# StringOS Reliability Benchmark

Deterministic evaluation over 200 trials with a 35% transient failure probability per
attempt and seed 7.

| Policy | Task success | Recovery after first failure | Average attempts |
| --- | ---: | ---: | ---: |
| retry_budget_0 | 57.0% | 0.0% | 1.00 |
| retry_budget_1 | 81.0% | 55.8% | 1.43 |
| retry_budget_2 | 91.5% | 80.2% | 1.62 |
| retry_budget_3 | 97.5% | 94.2% | 1.71 |

## Plan validation

Detected 4 of 4 invalid plans before tool execution (100.0%).

## Reproduce

```bash
python -m stringos.benchmark --trials 200 --failure-probability 0.35 --seed 7
```

These are deterministic synthetic failures. The benchmark measures runtime behaviour,
not language-model planning quality or production reliability.
