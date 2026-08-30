# Pixel/Termux migration record

The prior Pixel/Termux work is preserved in the local and origin references:

- `origin/agent/termux-phone` = `893dc78ec627b6f1b20df9ccd787d728ef320274`
- `origin/agent/termux-phone-v150` = `8b364ca371d2b3c82093806c7e72a8c53f6d90c6`

Those branches were not merged wholesale. OpenAI 0.152 already supplies the
remote-control, pairing, enrollment persistence, local control transport, and
reconnectable-session primitives. The only accepted runtime port in this
candidate is Android TLS alignment:

```text
capability/android-termux-0.152
commit 6bc17b2fb
4 files, 23 insertions, 0 deletions
```

Pixel/Termux status for this candidate: `PRESERVED_NOT_RETESTED`. No native
ARM64 build, pairing session, reconnect, PTY, or startup run was performed in
the available environments. This is not evidence of a regression.
