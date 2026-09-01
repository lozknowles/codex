# Downstream architecture

OpenAI Codex is the authoritative product and source history. This fork adds a
narrow Android / Termux compatibility and release-control layer; it does not
fork Codex product behavior.

The evergreen path is:

```text
OpenAI rust-v tag
  -> exact peeled source SHA
  -> per-patch compatibility classification
  -> native aarch64-linux-android build
  -> Pixel runtime and persistence qualification
  -> atomic install
  -> rollback proof
  -> approved promotion
  -> manifest, evidence, tag, and GitHub Release
  -> UP_TO_DATE
```

The harness is deterministic Python and shell tooling. It does not depend on
Agent Control, an LLM, or conversation history. Credentials remain in the
operator and Pixel environments and are not release inputs or evidence.

Detailed boundaries and state transitions are documented in
[docs/android/ARCHITECTURE.md](docs/android/ARCHITECTURE.md). Patch ownership
and removal criteria are in [docs/android/PATCHES.md](docs/android/PATCHES.md).
