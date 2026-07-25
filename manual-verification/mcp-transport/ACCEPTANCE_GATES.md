# Final acceptance gates (stdio remediation)

Checked: `2026-07-25T11:31:46.549490+00:00`

- [x] MCP client and server have different PIDs
- [x] MCP initialization is captured
- [x] tools/list is captured
- [x] tools/call is captured
- [x] MCP server response returns over stdio
- [x] Authoritative path does not directly call the handler
- [x] Killing MCP server produces a real detected failure
- [x] No generated results are tracked by Git
- [x] Fresh dashboard begins in an honest no-data state
- [x] Fresh experiments populate the dashboard
- [x] Ollama prerequisite checker works
- [x] Clean clone completes documented workflow
- [x] EnergyPlus actuator proof still passes
- [x] Next-state proof still passes
- [x] Comfort remains zero (deterministic Path A)
- [x] No silent mock fallback returns

Independent score: **95/100** · Status: **PASS**
