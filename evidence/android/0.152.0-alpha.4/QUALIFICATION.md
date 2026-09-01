# Android evergreen harness qualification: OpenAI 0.152.0-alpha.4

Verdict: **HARNESS_READY_QUALIFICATION_PENDING**.

This was a real non-destructive run of the deterministic harness on 2026-09-01.
It used exact OpenAI SHA `7ac2dff554323b17d5f622b7aca236ca75c93259`
for lineage classification and downstream source SHA
`5db8949c1432b85d3b2c67e39e6e7cb98ea8caf9` for the already-built Pixel
candidate. The clean patch-stack dry run produced an equivalent six-commit
candidate ending at `bf837c667e` in the disposable hpubuntu checkout.

The harness detected V8 `150.4.0` with checksum
`42a978ff11f15b24e5c05a7123cf2b68f41e763546699781a924ef4e2cf43a49` as
compatible and classified all six patches `REQUIRED_UNCHANGED`. The patch stack
applied cleanly and in order.

## Runtime evidence

| Gate | Result |
|---|---|
| Provenance | PASS |
| Existing build re-verification | PASS |
| App-server startup | PASS |
| Authenticated execution | PASS |
| Android TLS/provider path | PASS |
| Persistent session | PASS |
| Same-session resume | PASS |
| New SSH connection resume | PASS |
| Runtime locking paths | PASS |
| Focused lock tests | PENDING |
| Install | NOT_RUN |
| Rollback | NOT_RUN |
| Promotion | NOT_RUN |

Session continuity was proven with thread
`01a05b80-8f4d-79d1-b6ec-1e96c1f78ba0`. The active Pixel Codex `0.146.0`
was not modified. Candidate hashes remained:

- `codex`: `06d75b8dcf20ee2a6e1bbc0e3b8096134910646454751086ec30fccc26ab92ba`
- `codex-code-mode-host`: `b9956f2138b5a231ac0ce9a7311a94f2318c1cc302c532ac65468c8ef58dbb79`

Seventeen harness fixture tests passed. During the real run they caught and
forced correction of sequential patch classification, SSH script stdin
consumption, missing resume trust override, and malformed-empty result
handling. No stable tag is justified until focused lock tests and the governed
install/rollback/promotion sequence pass.
