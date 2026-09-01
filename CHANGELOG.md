# Changelog

OpenAI's authoritative changelog is available on the
[OpenAI Codex releases page](https://github.com/openai/codex/releases). This
file records only downstream Android / Termux releases.

## 0.153.0-alpha.2-loz.android.1 - 2026-09-01

- Rebased the native Pixel/Termux build on OpenAI `rust-v0.153.0-alpha.2`
  (`73919571da608749b867134722fe3b42c1c6097f`).
- Retained the six compatibility patches still required by Android: executable
  TLS alignment, Termux/lazy protoc selection, and three `flock` lock paths.
- Added the deterministic evergreen detect, prepare, classify, build,
  qualification, install, rollback, promotion, and status harness.
- Added release manifests, exact artifact hashes, Pixel qualification evidence,
  recovery instructions, and a frozen patch-removal baseline.
