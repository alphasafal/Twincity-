# MCP Failure and Recovery Tests

Matrix: `mcp-failure-matrix.csv` · Summary: all **8/8** passed in this remediation run.

| Case | Expected | Actual | Fallback | Unsafe actuator |
|------|----------|--------|----------|-----------------|
| 1 Server unavailable | hard fail start | RuntimeError on spawn | LLM loop uses deterministic_fallback | no |
| 2 Terminated mid-request | call fails | ok=False ClosedResourceError | caller fallback | no |
| 3 Timeout / dead server | call fails | ok=False | deterministic_fallback | no |
| 4 Malformed tool args | call fails | ok=False validation error | fallback | no |
| 5 Unknown tool | call fails | ok=False Unknown tool | fallback | no |
| 6 Schema-invalid args | call fails | ok=False JSON error | fallback | no |
| 7 Server restart | new session ok | new server PID ≠ client | none | no |
| 8 Clean shutdown | closed cleanly | closed=true | none | n/a |

**Rule enforced:** the client never reports `ok=True` for a tool call when the server is unavailable or returns a tool error payload.
