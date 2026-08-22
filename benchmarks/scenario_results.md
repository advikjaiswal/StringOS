# StringOS Real-Runtime Scenario Benchmark

This benchmark imports and executes `stringos.runtime.AgentRuntime`. External tools are deterministic local test doubles; the core runtime, validation, approval, retry, idempotency and trace paths are real StringOS code.

| Metric | Value |
| --- | ---: |
| Scenarios | 9 |
| Task completion rate | 44.4% |
| Expected-behaviour correctness rate | 100.0% |
| Safe rejection rate | 22.2% |
| Recovered completion rate | 66.7% |
| Uncontained/unknown outcome rate | 11.1% |
| Postcondition failures | 3 |
| Side-effect failures | 1 |

| Scenario | Terminal state | Task completed | Correct behavior | Recovered | Side effects |
| --- | --- | ---: | ---: | ---: | ---: |
| `normal_completion` | `completed` | yes | yes | no | 0 |
| `tool_timeout_recovery` | `completed` | yes | yes | yes | 0 |
| `retryable_tool_failure` | `completed` | yes | yes | yes | 0 |
| `malformed_tool_response` | `postcondition_failed` | no | yes | no | 0 |
| `permission_denial` | `approval_required` | no | yes | no | 0 |
| `partial_side_effect` | `outcome_unknown` | no | yes | no | 1 |
| `false_success_trap` | `postcondition_failed` | no | yes | no | 0 |
| `non_retryable_failure` | `permanent_failure` | no | yes | no | 0 |
| `duplicate_idempotency` | `completed` | yes | yes | no | 1 |

No retry-policy baseline is reported for these scenarios because the current runtime does not expose a fair single toggle that disables only the reliability layer without changing the production execution path.
