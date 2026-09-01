# Android / Termux downstream

OpenAI Codex is authoritative. This repository carries only compatibility
changes that a current OpenAI release demonstrably needs to run natively in
Termux on the qualified Pixel environment.

The update harness is ordinary Python 3 and shell tooling. It does not call an
LLM, Codex, ChatGPT, or Agent Control. Agent Control, cron, CI, or a human may
invoke it, but none is part of its correctness boundary.

Current recorded state:

- last inspected base: OpenAI `0.152.0-alpha.4`, SHA `7ac2dff554323b17d5f622b7aca236ca75c93259`;
- downstream candidate: `0.152.0-alpha.4-loz.android.1`;
- candidate verdict: `PARTIALLY_QUALIFIED`, not a stable release;
- active Pixel fallback: Codex `0.146.0`, preserved unchanged;
- target: Pixel 8 Pro, Termux, `aarch64-linux-android`.

Run `./scripts/android/update-codex-android status` for the live upstream and
manifest comparison. See [UPGRADING.md](UPGRADING.md) for the governed update
procedure.

No downstream feature is accepted without a demonstrated requirement that
current OpenAI Codex does not adequately satisfy.
