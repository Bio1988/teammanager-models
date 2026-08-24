# Natural Radio D1 Gold evaluation

This is the repeatable model-and-runtime check for the immutable development
inputs below. It is intentionally narrower than the D2 integration Gold suite:
D2 owns `SpeechFrame` validation, closed JSON acceptance, control exclusion,
deadlines, and deterministic fallback. Passing this record does not authorize a
runtime consumer.

## Inputs and command

| Input | Fingerprint |
| --- | --- |
| Model | `race-engineer-qwen3-0.6b-q4_k_m.gguf`, 396,705,632 bytes, SHA-256 `3a627f406fff3e6e1c5fe2d6104f28ef760a6599b4cab31c4bc1c03ae2bf95ff` |
| Runtime | `natural-radio-runtime.zip`, 18,990,303 bytes, SHA-256 `810d5c228cde848ed8df4f509676d79974eb0a13c64b88696dc997beaf51f5a` |
| Server | `Release/llama-server.exe`, SHA-256 `c932a2ac50dbdc5768399723e2e6e6295f7abcdf5243220729022c38ae2c415a` |

Run the server on an unused loopback port only:

```text
Release/llama-server.exe -m race-engineer-qwen3-0.6b-q4_k_m.gguf --host 127.0.0.1 --port <unused-port> --parallel 1 -c 4096 --jinja --no-webui
```

For every case in the retained
[`natural-radio-d1-gold-cases.json`](natural-radio-d1-gold-cases.json), submit
one `/v1/chat/completions` request with temperature `0`, `max_tokens` `80`, one
slot, and this system instruction:

```text
You are an English race-radio renderer. Return exactly one short radio
sentence. The user provides a fact and REQUIRED LITERALS. Include every
required literal exactly, case-insensitively. Never add, infer, advise, or
issue a simulator command.
```

The input contains the case's `fact` and its `required_terms` verbatim. A
result passes only when it finishes normally, contains every required term,
contains no configured control verb, contains at most 24 words, and exactly
matches the case's expected response. The exact-match condition is deliberate:
this fixed Gold record must fail rather than silently permit an added fact,
advice, command, or a dropped state. The model remains free to vary wording in
D2, but D2 has to validate that output independently before it is spoken.

Run the retained evaluator against an already running loopback server:

```powershell
pwsh -NoProfile -File scripts/run-natural-radio-d1-gold.ps1 -ServerUrl http://127.0.0.1:<unused-port> -OutputPath .\natural-radio-d1-gold-rerun.json
```

The script reads the retained cases, rejects any non-loopback `ServerUrl`, sends the exact requests, records the
per-case finish reason and response, and exits non-zero when any requirement
fails. It never starts a process, changes a runtime configuration, or contacts
the network beyond the specified loopback server.

## Recorded Windows result

The retained result in
[`natural-radio-d1-gold-results.json`](natural-radio-d1-gold-results.json) was
run on 2026-08-24 on a Windows x64 host with an AMD Ryzen 7 5800X (16 logical
processors) and 51,480,473,600 bytes of physical RAM. The server loaded the
model in 0.91 seconds. Its observed working set after the requests was
1,189,720,064 bytes and private memory was 863,014,912 bytes. These are one
host's observations, not a minimum requirement or a general performance claim.

The stricter run passed four of eleven fixed English cases. Seven failures are
retained verbatim rather than hidden: several omitted names or state, and none
issued a configured simulator-control verb. The slowest recorded request was
363.92 ms; this is model-side inference evidence only, not an end-to-end
radio-latency claim. The result therefore demonstrates a functioning local
model/runtime pair but does not approve unvalidated Natural Speech output. D2
must enforce its validator and immediate deterministic fallback before any
response can be spoken. The safety-boundary case confirms the model was told
the action is ineligible; D2 must enforce that exclusion before a request can
reach this model.

Windows VM execution remains pending unless the Alpha owner explicitly accepts
this physical-target Windows run as its substitute. This record also does not
turn the development release into an installer input: Race Engineer must pin
the approved immutable inputs in its closed build lock before D2 can use them.

Verify the committed result without starting a model:

```powershell
pwsh -NoProfile -File scripts/test-natural-radio-d1-gold-record.ps1
```
