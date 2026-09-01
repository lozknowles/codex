# Architecture

```text
        OpenAI Codex
             |
      latest rust-v tag
             |
             v
     deterministic checker
             |
       +-----+-----+
       |           |
 upstream fixed   patch needed
       |           |
       +-----+-----+
             v
       Android build
             |
             v
      Pixel qualification
             |
       +-----+-----+
      FAIL         PASS
       |            |
 keep old       install/rollback
       |            |
       +-----+------+
             v
        evidence/tag
```

Each release starts in an isolated worktree at the exact peeled OpenAI tag
SHA. The harness evaluates every patch independently with forward and reverse
applicability checks. A conflict becomes `REVIEW_REQUIRED`; it is never treated
as proof that a patch is obsolete. Human semantic review remains required when
the upstream subsystem changed.

The compatibility layer is stored as auditable `git format-patch` files and
metadata. Application uses `git am --3way`, preserving authorship and commit
boundaries. Features unrelated to Android compatibility do not belong in this
stack.

State and evidence live under `evidence/android/<version>/`. Resume logic
rechecks source and artifact identities instead of trusting stage names alone.
Install, rollback, promotion, stable tags, and publication remain distinct
operations.
