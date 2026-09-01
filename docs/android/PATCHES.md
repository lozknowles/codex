# Android compatibility patches

Machine-readable metadata is in `android/patches.json`; lossless patch files
are in `android/patches/`.

| Patch | Original failure | Preserved semantics | Removal condition |
|---|---|---|---|
| Android TLS alignment | Native Android executable TLS alignment risk | Android-only aligned `.tdata`; other targets unchanged | Upstream/toolchain guarantees and tests required alignment |
| Termux protoc | Vendored protoc has no Android/aarch64 binary | `PROTOC` override, Termux PATH on Android, vendored desktop fallback | Upstream provides an Android protoc path or removes the build-time need |
| Lazy protoc selection | Unsupported vendored path evaluated eagerly | Only selected provider is evaluated | Upstream selection is lazy and Android-capable |
| App-server startup flock | `lock() not supported` before app-server startup | Blocking advisory exclusion, EINTR retry, close releases lock | Rust std lock works on Android or upstream supplies equivalent tests |
| Installation-ID flock | installation-ID initialization lock unsupported | Cross-process blocking coordination; non-Unix unchanged | Same as above for installation identity |
| Thread-store flock | persistence/resume failed at lock/try_lock | Blocking coordination; `LOCK_NB` maps contention to `WouldBlock` | Upstream supplies equivalent Android writer-lock behavior |

For every new OpenAI tag, `classify` reports one of:

- `REQUIRED_UNCHANGED`
- `UPSTREAM_FIXED`
- `REVIEW_REQUIRED`

`REQUIRED_ADAPTED` and `NO_LONGER_APPLICABLE` are human review outcomes that
must be entered by updating metadata and replacing the patch with a separately
reviewable commit. A clean cherry-pick alone is not semantic proof.
