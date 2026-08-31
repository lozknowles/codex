# Semantic rebase register: Rebroad 0.149 to OpenAI 0.152

This register compares the Rebroad `alpha` snapshot at
`a1428ff0f813d508a22c505aa01310515c434116` (`0.149.0-alpha.7.2`) with
OpenAI `latest-alpha-cli` at `7ac2dff554323b17d5f622b7aca236ca75c93259`
(`0.152.0-alpha.4`). It is a source comparison. Runtime parity is not claimed.

## Capability matrix

| Capability | Rebroad state / files | OpenAI state / files | Classification | Needed by us? | Port difficulty | Estimated LOC | Dependencies |
|---|---|---|---|---|---|---:|---|
| Android / Termux | Android TLS helpers, Android sandbox/build paths, Termux scripts | no equivalent TLS helper; different platform/build paths | FORWARD_PORT | Yes, if Android remains supported | EASY for TLS; HARD for full build | 23 prototype; 1k–3k full | Android target, toolchain |
| TLS / certificate behavior | Android TLS-segment alignment helper | no current equivalent found | FORWARD_PORT | Yes | EASY | 23 actual | Android target |
| Remote control | `app-server-transport/.../remote_control`, CLI command | remote-control architecture exists, but differs in transport details | REDESIGN | Yes | HARD | 500–1,500 | pairing, reconnect |
| Pairing | pairing tests and enrollment/recovery changes | related account/remote APIs exist | PARTLY_UPSTREAM | Maybe | MODERATE | 300–800 | remote control |
| App-server reconnection | reconnect handoff and stale-socket recovery | current lifecycle/session code differs | BEHAVIOUR_DIFFERENT | Yes | HARD | 300–1,000 | remote control, TUI |
| Providers/models | provider overrides, Bedrock/model metadata changes | substantial native provider/model framework | REDESIGN | Yes | MODERATE–HARD | 200–800 | model metadata |
| Effective model attribution | response usage/model metadata paths | current protocol has equivalent usage/model metadata | FULLY_UPSTREAM | Yes | DO_NOT_PORT | 0 | none |
| Token accounting | usage replay and response usage paths | current usage protocol and workers cover the core path | UPSTREAM_NOW | Yes | DO_NOT_PORT | 0 | none |
| Cost accounting | Rebroad turn-cost worker and pricing documentation | current accounting differs in details | REDESIGN | Yes | MODERATE–HARD | 200–700 | token accounting |
| Account usage/rate limits | account protocol, processor, and TUI displays | current OpenAI has account/rate-limit equivalents | UPSTREAM_NOW | Yes | DO_NOT_PORT | 0 | none |
| Cache behaviour | model/plugin/prompt cache changes and tests | current cache managers and prompt-cache tests exist | UPSTREAM_NOW | Yes | DO_NOT_PORT | 0 | providers, prompts |
| Prompt changes | guardian, goals, skills, and prompt-cache assets | current prompt system is materially different | REDESIGN | Maybe | MODERATE–HARD | 100–600 | cache, runtime |
| TUI changes | wake, resume, takeover, reconnect, and Android UI changes | native current TUI has overlapping but different flows | PARTLY_UPSTREAM | Yes | HARD | 500–2,000 | app-server |
| Sandbox/runtime | Android fallback and sandbox hardening | current sandbox architecture differs | REDESIGN | Yes | HARD | 300–1,200 | platform targets |
| Cancellation/recovery | duplicate-rollout repair, stale state, turn recovery | some equivalents are upstream; exact semantics differ | UNKNOWN | Yes | MODERATE–HARD | 200–700 | state, TUI |
| Installer/update | fork release aliases and PATH/npm behavior | OpenAI has its own release/update paths | REDESIGN | Yes | MODERATE | 300–1,000 | release metadata |
| Release/package workflows | fork-specific workflows, package assembly, candidate stamping | not reusable as-is for our distribution | REDESIGN | Yes | HARD | 500–2,000 | installer, CI |
| Rusty V8/toolchain | forked artifacts, checksums, Android/ARMv7 resolver | upstream toolchain assumptions differ | REDESIGN | Android only | HARD | 500–2,000 | build/release |
| Build reproducibility | cache isolation, artifact reuse, target scripts | current build graph differs | REDESIGN | Yes | MODERATE | 300–1,000 | toolchain |
| Test infrastructure | Android/ARMv7 tests, remote traffic capture, quarantines | current tests cover overlapping behavior differently | FORWARD_PORT | Yes | MODERATE | 300–1,200 | every port |
| Qualification/recovery tooling | rollout inspection, health checks, recovery scripts | no direct one-for-one equivalent | FORWARD_PORT | Yes | MODERATE | 1,874 actual | release process |

The classifications are deliberately conservative. “Fully upstream” means no
Rebroad code should be carried. “Partly upstream” means only a behavior-level
gap should be recreated. The unusually large path diff is not itself evidence
that all those paths remain needed: the two releases have moved considerably,
and many Rebroad paths are older or structurally incompatible with current
OpenAI.

## Historical delta

The prior ancestry audit measured the Rebroad branch from merge-base
`4f38432d8709bb5f46eca72e9f372cbe2967fefc` as:

```text
378 commits
440 files
18,432 insertions
2,564 deletions
20,996 touched lines
```

Comparing Rebroad directly with OpenAI 0.152 produces a gross
`2,015-file` comparison with `42,588` additions and `149,392` deletions. That
number is not a porting estimate; it includes release divergence, removed or
renamed upstream material, and incompatible historical structure.

## Surviving semantic delta

The practical survivorship estimate is:

```text
Upstream now:          4 capability groups
Forward-port:          4 capability groups
Redesign:              12 capability groups
Drop:                  0 capability groups selected
Unknown:               1 capability group
```

For a practical controlled distribution, expect approximately 7–10 owned
capability groups, 40–80 existing OpenAI files affected, 8–15 new files, and
roughly 2,000–6,000 added or changed LOC. This is a range, not a measured
patch. The largest uncertainty is remote-control/reconnection behavior and
whether Android/Termux remains a product requirement.

## Port profiles

| Profile | Scope | Files | LOC | Risk | Future rebase burden |
|---|---|---:|---:|---|---|
| A — Minimal | Android TLS alignment, essential provider metadata, cost display, qualification checks | 10–25 | 300–1,200 | Moderate | Moderate |
| B — Practical | Profile A plus selected remote control/recovery, caching, and reproducible packaging | 40–80 | 2,000–6,000 | Moderate–high | Moderate–high |
| C — Full surviving behavior | All material Rebroad differences, including release/toolchain and TUI behavior | 100+ | 8,000–20,000 | High | High |

Recommendation: Profile B only after Profile A is qualified. Do not attempt
Profile C until the remote-control and release boundaries are separately
owned and tested.

## Prototype result

A disposable branch, `capability/android-termux-0.152`, was created from the
OpenAI 0.152 target and committed at
`6bc17b2fb` (`experiment: forward-port Android TLS alignment`). It adds the
Android-only TLS alignment behavior to the current CLI and code-mode-host
entrypoints:

```text
4 files
23 added LOC
0 deleted LOC
```

`git diff --check` passed. A Cargo build could not be run because Cargo is not
available in the supplied workspace runtime. Android runtime/linker parity is
therefore unverified. The prototype is structurally successful but not
qualified; it remains disposable and has not been merged into `ours/base`.

The second selected capability is on
`capability/qualification-rollout-inspector-0.152`, committed at
`80dcb05cba48b2f877c23508a485e523d772f667`:

```text
10 files
1,874 added LOC
0 deleted LOC
git diff --check: PASS
```

It is a standalone Node-based qualification/rollout inspection tool. Its
browser workflow was not run in this phase. Both branches therefore have
`IMPLEMENTATION: PASS`, `BUILD: NOT_RUN`, `UNIT TESTS: NOT_RUN`,
`INTEGRATION TESTS: NOT_RUN`, `RUNTIME/SMOKE: NOT_RUN`, and
`QUALIFICATION: IMPLEMENTED_UNQUALIFIED`.

These branches target OpenAI directly because `ours/base` already contains the
Rebroad implementations; branching from `ours/base` would not test the
forward-port. The controlled baseline remains unchanged.

## Future maintenance estimate

For OpenAI `0.152 -> 0.153`, the traditional model would require re-evaluating
hundreds of historical Rebroad commits and their ancestry. The semantic model
would revalidate 7–10 owned capability groups, with recurrent conflicts
concentrated in roughly 10–20 files for Profile A/B and substantially more for
Profile C.

| Strategy | Assessment | Reason |
|---|---|---|
| Traditional Rebroad replay | VERY DIFFICULT | mixed history, large structural drift, repeated conflict resolution |
| Semantic capability ownership | MODERATE | smaller explicit surface, but remote-control and release work remain coupled |

## Remote-control and reconnection viability

### Behavioural contract

The Rebroad behavior is: a logged-in primary Codex starts or reuses a managed
app-server; a secondary ChatGPT/Codex device pairs using a short-lived manual
code; enrollment and credentials are persisted per account/server; the remote
transport is authenticated; the client can observe and control an allowed
session; transient transport or app-server loss retries and reconstructs the
logical session; stale enrollment or sockets fail closed and can be recovered;
disconnect, cancellation, completion, and duplicate reconnects do not create a
second logical session.

### OpenAI overlap

OpenAI 0.152 already contains the core contract: `remote_control` transport
modules, authenticated enrollment and pairing, persisted enrollment migrations,
`remote-control start/stop/pair` CLI commands, private Unix-socket control
transport, app-server daemon lifecycle, reconnectable code-mode sessions,
generation IDs, and dedicated pairing/reconnect tests. These are therefore
`ALREADY_UPSTREAM` and should not be carried from Rebroad.

The remaining Rebroad-specific changes are `PARTIALLY_UPSTREAM`: stale socket
and expired-enrollment recovery, manual-pairing retry/backoff policy, Android
startup handling, profile/helper scripts, and optional WebSocket traffic
capture. The direct Rebroad-vs-OpenAI comparison is 22 files, 1,932 additions,
and 212 deletions, but that is not a proposed port size; much of it is already
represented by newer OpenAI architecture.

### Minimal semantic architecture

Keep OpenAI's existing authenticated remote-control transport and persistence.
If required by our product, add recovery policy at the daemon/CLI boundary,
with bounded retries and explicit stale-state invalidation. Keep pairing
isolated from the core runtime. Add traffic capture only as an opt-in,
loopback/local diagnostic feature with secret redaction enabled by default.
Do not expose a new LAN listener, alter sandbox policy, or copy the old remote
session subsystem.

Provisional implementation estimate for the remaining behavior is 8–20
existing files, 2–8 new files, 500–1,500 runtime LOC, and 300–900 test LOC.
That is coupled enough to defer until a real product requirement is recorded.

### Prototype result

`experiment/remote-reconnect-semantic-0.152` was created at the OpenAI 0.152
SHA and deliberately contains no product-code changes. The experiment is
`STOPPED` at the design gate: the core vertical slice is already upstream, and
the remaining changes are security/lifecycle work rather than a low-risk
isolated port. No remote listener, public exposure, firewall, or network
configuration was changed.

### Reconnection test matrix

| Scenario | Result | Evidence or boundary |
|---|---|---|
| Clean connection | NOT_RUN | existing OpenAI tests inspected, not executed |
| Remote disconnect | NOT_RUN | no live paired device in scope |
| Server-side disconnect | NOT_RUN | no live server run |
| Brief network interruption | NOT_RUN | no network fault injection |
| Reconnect existing session | NOT_RUN | upstream reconnect code inspected |
| Invalid/stale credential | NOT_RUN | upstream enrollment tests inspected |
| Duplicate reconnect | NOT_RUN | generation/session code inspected |
| Server restart | NOT_RUN | no daemon execution |
| Client restart | NOT_RUN | no paired client execution |
| Completed session | NOT_RUN | no live session |
| Cancellation during disconnect | NOT_RUN | no live session |

### Security review

The proposed design preserves OpenAI's trust boundary: authenticated
enrollment, persisted scoped credentials, private local control transport, and
no new public listener. Rebroad's traffic capture is security-sensitive and
must remain opt-in, redacted, and local. It should not be ported before a
separate review of token, cookie, prompt, command, and output leakage.

### Historical compression and decision

The Rebroad-vs-OpenAI remote/reconnect difference is approximately 22 changed
files and 2,144 gross changed lines, while the core user-visible capability is
already upstream. The remaining semantic work is estimated at 500–1,500
runtime LOC plus tests, but is not yet justified or qualified.

**YES_WITH_REDESIGN**: remote control and reconnection can be owned as a
bounded semantic capability, but only by retaining OpenAI's implementation and
adding narrowly scoped recovery/operational behavior. Do not drag Rebroad's
historical remote architecture forward.

## Final decision

**SEMANTIC REBASE PROBABLY BETTER**, provided we choose Profile A first and
only add Profile B capabilities behind focused tests and qualification. The
experiment demonstrates “move the man rather than the mountain” for isolated
behavior: 378 historical commits and about 21k touched lines reduce to a
23-line prototype. It does not yet demonstrate that the entire Rebroad
distribution reduces to 23 lines; the realistic practical estimate is
2k–6k LOC across 40–80 OpenAI files.

## Final controlled integration candidate

`semantic/integration-0.152` is based directly on OpenAI
`7ac2dff554323b17d5f622b7aca236ca75c93259`. It contains only:

- Android TLS alignment: 4 runtime files, 23 insertions, 0 deletions;
- rollout-inspector: 10 qualification-tooling files, 1,874 insertions,
  0 deletions;
- downstream documentation and registers.

The prior Pixel/Termux branches remain preserved and are not merged wholesale.
Their useful operational knowledge is recorded in
`docs/PIXEL-TERMUX-MIGRATION.md`. Pixel status is
`PRESERVED_NOT_RETESTED`; this candidate is not an Android-qualified release.

Candidate version: `0.152.0-alpha.4-loz.1-rc1`.

Qualification status: `RELEASE_CANDIDATE`, not a fully qualified release.
`git diff --check` and Node syntax checks passed. Cargo/rustc were unavailable,
so desktop compilation, Rust tests, artifact generation, startup, and rollback
execution were not run. The candidate must not be presented as an official
OpenAI release.

## Build, release, and Termux viability

### Platform requirements

This is the provisional controlled-distribution matrix, based on the existing
Linux/Windows repository targets and the explicit Android/Termux capability
work. It can be narrowed later if Android is removed from the product scope.

| Platform | Build | Package | Install | Run | Update | Rollback |
|---|---|---|---|---|---|---|
| Linux x86_64 | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| Windows x86_64 | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| Android / Termux arm64 | REQUIRED if retained | REQUIRED if retained | REQUIRED if retained | REQUIRED if retained | REQUIRED if retained | REQUIRED if retained |
| macOS x64/arm64 | OPTIONAL | OPTIONAL | OPTIONAL | OPTIONAL | OPTIONAL | OPTIONAL |

### Infrastructure inventory and OpenAI coverage

| Area | Rebroad intent and scope | OpenAI 0.152 status | Semantic verdict |
|---|---|---|---|
| Runtime portability | Android cfgs, TLS alignment, filesystem/process fallbacks | Linux/macOS/Windows native; Android not a supported package target | PARTIALLY_UPSTREAM; small Android runtime fixes only |
| Build system | shared Cargo environments, target isolation, cross-build scripts | Cargo workspace, Bazel, lockfiles, build-info, and platform build scripts exist | PARTIALLY_UPSTREAM; avoid importing Rebroad scripts wholesale |
| Installer/update | fork-scoped npm identity, aliases, PATH and release selection | npm installer/update paths and version checks exist | PARTIALLY_UPSTREAM; use our package identity and immutable artifacts |
| Release/package | multi-platform npm artifacts and release workflows | `codex-cli/scripts/build_npm_package.py`, package workflows, and platform matrix exist | ALREADY_UPSTREAM for Linux/macOS/Windows; Android missing |
| Rusty V8/toolchain | fork artifact resolver, checksums, ARMv7/Android handling | Rusty V8 resolver, patches, workflows, and checks already exist | BUILD_CONFIGURATION_ONLY; Android target remains unproven |
| Reproducibility | lockfiles, checksums, target caches, version stamping | lockfiles and build-info exist; release manifests can carry SHA/checksums | PARTIALLY_UPSTREAM; add process metadata, not a new build system |
| Qualification/CI | smoke, artifact audit, release gates | substantial upstream CI and artifact tests exist | PARTIALLY_UPSTREAM; retain only controlled qualification tooling |

### Android / Termux blockers

| Blocker | Assessment | Required delta |
|---|---|---|
| TLS segment alignment | OpenAI has no equivalent helper; Rebroad has a 23-line semantic port | SMALL SEMANTIC FIX |
| Android ARM64 target/package | no OpenAI npm platform package or completed local target build | BUILD TOOLING ONLY initially; runtime support UNKNOWN |
| Rusty V8 artifact compatibility | upstream has Rusty V8 machinery, but Android artifact compatibility is unproven here | BUILD TOOLING ONLY / UNKNOWN |
| Sandbox and process behavior | OpenAI has platform sandbox paths, Android behavior is not qualified | NEEDS_REDESIGN if required |
| PTY/filesystem/startup | no safe local Android runtime evidence | UNKNOWN |
| Shell/linker/dependency assumptions | Rebroad contains extensive Termux-specific scripts and linker fixes | BUILD TOOLING ONLY; do not port until an Android builder exists |

### Rusty V8 verdict

**BUILD_CONFIGURATION_ONLY.** OpenAI 0.152 already carries the relevant Rusty
V8 component, resolver, patches, and release workflows. Rebroad's additional
artifact and ARMv7/Android handling may still be needed for a real Android
target, but this environment cannot prove that. No Rusty V8 machinery was
copied.

### Minimum distribution architecture

Use OpenAI's existing build and package mechanisms on a controlled builder:

```text
OpenAI SHA + reviewed semantic commits
        -> pinned lockfiles/toolchain
        -> build and tests
        -> immutable versioned artifact
        -> SHA/checksum manifest
        -> explicit install/current pointer
        -> retain previous artifact for rollback
```

For Linux and Windows, reuse upstream package/build outputs and record our
source SHA. For Android/Termux, first qualify a direct versioned binary; only
then decide whether a package channel or installer is worthwhile. No npm
publishing is required for this experiment.

### Footprint and prototype boundary

The historical Rebroad infrastructure includes roughly 6,000 added LOC under
`scripts`, plus extensive CI/workflow and platform changes. The likely owned
semantic footprint is currently:

```text
Runtime portability:       LOW for desktop; LIKELY for Android
Build tooling:             LOW for desktop; LIKELY for Android
Packaging/install/update:  LOW for desktop; LIKELY for Android
CI/test/qualification:     MODERATE
```

No infrastructure prototype was implemented. The isolated branch
`experiment/build-release-termux-semantic-0.152` remains at OpenAI
`7ac2dff554323b17d5f622b7aca236ca75c93259`. A build helper would duplicate
existing OpenAI build-info/package behavior before the Android target is
available, so the correct result is a design stop, not speculative code.

Available verification tools were Node `v24.19.0`, pnpm `11.19.0`, and Python
`3.12.13`; Cargo and rustc were unavailable. Consequently cargo/toolchain,
dependency resolution, compile/check, tests, artifact generation, install,
and startup are all **BLOCKED/NOT_RUN**. No binaries were downloaded or
installed.

### Infrastructure decision

**YES_WITH_REDESIGN.** We can own this family as a bounded semantic layer for
desktop platforms now, and for Android only after a real Android builder and
runtime qualification exist. The immediate owned layer should be source SHA,
lockfile/toolchain recording, immutable artifacts, checksums, explicit install,
and rollback—not Rebroad's full CI, installer, or Rusty V8 infrastructure.

## Pixel-first qualification follow-up

The current candidate remains `af4415ad959df8d87051371ff9cac1993d2d7fed`
(`v0.152.0-alpha.4-loz.1-rc1`) on the pinned OpenAI baseline
`7ac2dff554323b17d5f622b7aca236ca75c93259`. The preserved Pixel architecture
is **NATIVE_TERMUX**, not a newly invented Android subsystem. Historical native
ARM64 workflows remain on `agent/termux-phone` and `agent/termux-phone-v150`;
their successful Actions runs qualify those historical revisions only.

The Pixel is privately reachable over Tailscale at `100.100.97.118`, and the
user-confirmed Termux SSH service responds on port `8022`. Authentication was
not available, so no shell, ADB device, environment inspection, candidate
build, launch, session interaction, reconnect, or rollback test could run.
Android TLS runtime behavior is consequently **UNPROVEN**. Final status is
**PRESERVED_NOT_RETESTED / BLOCKED**, not a regression finding. Full evidence
is in `docs/PIXEL-QUALIFICATION-0.152.md`.

### Execution update

The qualification descendant `393d25d19a91958ee4152fb2770fcee2b231919f`
contains a small Android build configuration fix in
`codex-rs/code-mode-protocol/build.rs`: Termux's trusted PATH `protoc` is used
on Android, while desktop builds retain the vendored resolver. Serial
`cargo check -j1` passed the protocol, core, app-server, transport, and TUI
layers, then stopped at Rusty V8 v150.4.0 because the official
`aarch64-linux-android` prebuilt archive URL returned HTTP 404. Termux lacks
`gn` and `ninja`, so source V8 compilation was not attempted. This remains a
**BUILD_CONFIGURATION_ONLY / UNQUALIFIED** blocker; no Rebroad artifact
infrastructure was imported.

The focused Android `codex-code-mode-protocol` test then passed on the Pixel:
37 tests passed, 0 failed. This is partial qualification of the Android build
configuration and protocol crate only. The complete native distribution is
still unqualified because Rusty V8 cannot obtain its Android/aarch64 artifact.

### Pixel execution update: verified artifact path

Port-`8022` SSH access was restored. The isolated qualification checkout
verified the exact `rebroad/rusty_v8` `rusty-v8-v150.4.0` archive and binding
using the release checksum asset: archive SHA256
`54179034104bee6e68c7a83c304dddbaad797d2c65853318e7551a654a0a2b39`; binding
SHA256 `639421ae6a0d125dde076cdb4c5d5b3afc9e3ce764acad4a772b7182ea77da66`.
Explicit V8 overrides made the full workspace `cargo check -j1` pass through
Rusty V8 and complete; the Android protocol test remained green at 37/37.

The historical Termux target-specific linker configuration was then tested.
The native build exhausted Pixel storage before producing a binary. No runtime,
reconnect, or rollback qualification was possible. This remains
**PARTIALLY_QUALIFIED / BLOCKED**; no stable release tag is justified.

### Pixel execution update: native binaries produced

After removing only generated output from the disposable checkout, the
verified V8 overrides and the proven target-specific Termux linker setup
produced both native targets. `codex` was 669645208 bytes with SHA256
`054818a14695e84c86bec94395764e48d0948e8d7529eae6313c81ab94083b96`; the
code-mode host was 169650064 bytes with SHA256
`1f86892fc6517e606034b4f87a5fa048c1fec6b23b7782b2b4933b7afd8aeac2`.
Version and help smoke checks passed. No installation or live authenticated
session was attempted, so reconnect, TLS runtime, and rollback remain
unqualified and no stable tag is justified.
