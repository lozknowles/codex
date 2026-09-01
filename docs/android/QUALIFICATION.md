# Qualification gates

The candidate is not qualified until all mandatory gates pass against the
exact recorded source and binary hashes.

| Gate | PASS criterion |
|---|---|
| Q1 Provenance | Exact upstream tag/SHA, downstream SHA, expected clean source |
| Q2 Build | Native ARM64 `codex` and code-mode host, architecture/version/help and hashes |
| Q3 App-server | Genuine candidate execution crosses app-server startup |
| Q4 Authenticated execution | Real bounded Codex interaction performs a shell marker action |
| Q5 Android TLS | Q4 succeeds through the real provider HTTPS/authentication path |
| Q6 Persistence | Persistent thread is created and its ID recorded |
| Q7 Resume | Exact thread resumes and performs a second marker action |
| Q8 SSH reconnect | Q7 is performed through a new SSH process/connection |
| Q9 Locking | Focused Rust lock tests and real runtime lock paths pass, including `WouldBlock` |
| Q10 Install | Existing binary is backed up; candidate is atomically installed and rehashed |
| Q11 Rollback | Exact backup is atomically restored and reverified |
| Q12 Promotion | Separate approval reinstalls the proven candidate; final smoke passes |

`qualify` deliberately uses separate SSH invocations for initial execution and
resume. It does not substitute `curl` for authenticated Codex execution.

A blocked or missing gate remains `NOT_RUN`/`BLOCKED`; it is never converted to
PASS. Stable tagging is intentionally absent from the harness and remains a
separate reviewed repository action.
