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

For every case in the retained result, submit one `/v1/chat/completions`
request with temperature `0`, `max_tokens` `80`, one slot, and this system
instruction:

```text
You are an English race-radio renderer. Return exactly one short radio
sentence. This is a closed factual transform: include every named person,
number, unit, state, and reason from the input. Never add, infer, advise, or
command. If a fact says unavailable or stale, preserve both words.
```

The input is the case's `fact` verbatim. A result passes when it finishes
normally, contains each `required_terms` item case-insensitively, and contains
at most 24 whitespace-delimited words. `fuel_shortfall` deliberately requires
only its quantity and unit: D2 retains its typed event identity separately and
must reject any natural response that loses a required fact.

## Recorded Windows result

The retained result in
[`natural-radio-d1-gold-results.json`](natural-radio-d1-gold-results.json) was
run on 2026-08-24 on a Windows x64 host with an AMD Ryzen 7 5800X (16 logical
processors) and 51,480,473,600 bytes of physical RAM. The server loaded the
model in 0.91 seconds. Its observed working set after the requests was
1,189,720,064 bytes and private memory was 863,014,912 bytes. These are one
host's observations, not a minimum requirement or a general performance claim.

All eleven fixed English cases passed. The slowest recorded request was 385.16
ms; this is model-side inference evidence only, not an end-to-end radio-latency
claim. The safety-boundary case confirms that the renderer is told the action
is ineligible; D2 must enforce that exclusion before a request can reach this
model.

Windows VM execution remains pending unless the Alpha owner explicitly accepts
this physical-target Windows run as its substitute. This record also does not
turn the development release into an installer input: Race Engineer must pin
the approved immutable inputs in its closed build lock before D2 can use them.
