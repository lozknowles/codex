# Controlled downstream distribution

This checkout is the local control point for a maintained distribution derived
from OpenAI Codex. OpenAI is authoritative; Rebroad is a reference
implementation only.

> No downstream feature without a demonstrated requirement that current
> OpenAI Codex does not adequately satisfy.

## Lineage snapshot

- OpenAI upstream: `https://github.com/openai/codex`, inspected at
  `openai/latest-alpha-cli` = `7ac2dff554323b17d5f622b7aca236ca75c93259`
  (`0.152.0-alpha.4`). This is an upstream reference, not the current base.
- Rebroad reference: `https://github.com/rebroad/codex`, branch `alpha`, at
  `a1428ff0f813d508a22c505aa01310515c434116`
  (`0.149.0-alpha.7.2`). It is not the integration base.
- Historical OpenAI merge-base used for the Rebroad audit:
  `4f38432d8709bb5f46eca72e9f372cbe2967fefc`.

The immutable local refs under `audit/` preserve the observed remote tips.
`rebroad-track/20260830-alpha` and `ours/base` preserve the prior audit.
`semantic/integration-0.152` is the clean OpenAI-based integration branch.

## Maintenance model

```text
OpenAI release/reference
        |
        v
semantic/integration-0.152 + reviewed downstream changes
        |
        v
build -> tests -> smoke -> qualification -> release/YYYYMMDD
```

Keep OpenAI and Rebroad remotes fetch-only during audit and integration work.
Do not rewrite either upstream history. Preserve the exact Rebroad tracking
ref, then replay only reviewed downstream commits on `ours/*` or a future
release branch.

## Qualification state

`RELEASE CANDIDATE / NOT FULLY QUALIFIED`: the branch is based directly on
OpenAI 0.152 and contains only the Android TLS prototype, rollout-inspector
tooling, and downstream documentation. Rust/Cargo qualification and Pixel
runtime retesting remain incomplete. No package publication or system
installation has been performed.

## Upgrade procedure

For a future OpenAI release: create a clean baseline, review every owned
semantic capability, drop anything now upstream, forward-port only still-
required behavior, build/test, qualify, and release. Do not replay the
historical Rebroad commit stack.

## Candidate publication

The candidate branch is `semantic/integration-0.152`, based directly on
OpenAI `7ac2dff554323b17d5f622b7aca236ca75c93259`. Its accepted semantic
commits are the 23-line Android TLS alignment and the standalone rollout
inspector. The candidate is not a fully qualified release because Rust/Cargo
build verification and Pixel/Termux runtime retesting were unavailable.
