# Alpha English stock-voice contract

This document reconciles the immutable asset evidence owned here with Race
Engineer’s installed English stock voices. It is a review record, not a runtime
catalog or a replacement for Race Engineer’s closed
`build/alpha-models.lock.json`. The installer generates its local
`model-pack.json`; it must never query this document or `manifest.json` at
runtime.

## Runtime boundary

Race Engineer owns runtime voice selection. Its current stock set is Charles,
Michael, and Eve; Charles is the default. Those are catalog labels only. They
make no claim about a person’s identity or attributes beyond the upstream VCTK
file mapping.

## Required stock voices — release blocked

Race Engineer currently pins these files from the immutable Kyutai
`tts-voices` revision `323332d33f997de8394f24a193e1a76df720e01a`. The exact
URLs contain that revision, so they are not a mutable branch or tag. Each file
is VCTK material under CC-BY-4.0, attributed to Kyutai and the VCTK source
dataset.

| Race Engineer ID | Default | Immutable source | Installed target | Bytes | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| `pocket-voice-charles` | yes | `https://huggingface.co/kyutai/tts-voices/resolve/323332d33f997de8394f24a193e1a76df720e01a/vctk/p254_023_enhanced.wav` | `pocket/voice/charles.wav` | 639272 | `6b681a429198f16e378d53bccb08d06939da7b00144a7696111d4f8f76be7756` |
| `pocket-voice-michael` | no | `https://huggingface.co/kyutai/tts-voices/resolve/323332d33f997de8394f24a193e1a76df720e01a/vctk/p360_023_enhanced.wav` | `pocket/voice/michael.wav` | 751140 | `b6743e9195e5e3fd34fe9d1633ae93f7ffab787b249e45f6467d7d6f7a6ee6ad` |
| `pocket-voice-eve` | no | `https://huggingface.co/kyutai/tts-voices/resolve/323332d33f997de8394f24a193e1a76df720e01a/vctk/p361_023_enhanced.wav` | `pocket/voice/eve.wav` | 671872 | `396e7cbd066b0f3fb6d67fa26e7904076958239d736d4390f15b5fe88feb14cd` |

### Release and offline-build rule

As verified against the Forgejo releases on 2026-08-19, no immutable Forgejo
release asset exists for Charles, Michael, or Eve. A clean private/offline
Alpha installer build is consequently **not release-ready**: it relies on the
upstream download path when its verified local input cache is absent. This is a
deliberate fail-closed release blocker, not permission to substitute Alba or to
download a different voice at runtime.

Before this blocker can be removed, a reviewed change must publish one immutable
Forgejo asset for each voice with its SHA-256, byte size, source revision,
CC-BY-4.0 licence text/attribution, and installer target. The Race Engineer
lock and its installed notices must then be updated in the same reviewed
release. Do not alter the historical `manifest.json` to represent these voices.

## Natural Radio inputs — experimental and not Alpha eligible

The current Race Engineer lock also lists these optional installer-owned local
inputs. They are immutable Forgejo assets, are never runtime downloads or a
model picker, and do not alter the deterministic safety path. The attached
release records Windows VM execution and Gold Eval as pending; no complete
licence/attribution record is retained in this repository for the assembled
runtime/model. They are therefore **not Alpha eligible** and cannot turn a
release green until both evidence gaps are resolved.

| Race Engineer ID | Immutable Forgejo asset | Bytes | SHA-256 | Status |
| --- | --- | ---: | --- | --- |
| `natural-radio-runtime` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/natural-radio-qwen3-0.6b-dev.1/natural-radio-runtime.zip` | 18990303 | `810d5c228c2de848ed8df4f509676d79974eb0a13c64b88696dc997beaf51f5a` | Experimental; release blocked |
| `natural-radio-model` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/natural-radio-qwen3-0.6b-dev.1/race-engineer-qwen3-0.6b-q4_k_m.gguf` | 396705632 | `3a627f406fff3e6e1c5fe2d6104f28ef760a6599b4cab31c4bc1c03ae2bf95ff` | Experimental; release blocked |

The historical Pocket R3 `pocket-alba` entry remains immutable provenance for
its already published asset. It is not the stock-voice authority and must not
be selected as a silent fallback for Charles, Michael, or Eve.
