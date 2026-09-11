# 1.7.0 acceptance

Verified on 2026-09-11 with the supported Hermes 0.21.0 core revision `b499ab11fe8b081470e269f2fb27abae03000da5`, Python 3.11 and Telegram, using an independent xAI OAuth / grok-4.6 test installation.

## Automated checks

- 130 regression tests passed, with no failures, errors or skipped tests.
- Native plugin discovery, prompt and tool registration, and OpenAI Codex / xAI request middleware passed.
- Both downloadable editions passed archive integrity, installation, repeat installation and uninstall restoration checks.
- Release manifest, Python syntax, whitespace and the release privacy scan passed.

## Telegram checks

| Scenario | Observed result |
|---|---|
| Chinese greeting | Immediate “在呢 👋”, followed by the model's final reply; temporary bubble removed. |
| Chinese multi-step task | The intake message became the live progress bubble, including a fitting emoji. |
| Mid-task update | A seven-day inventory request was changed to ten days while the source was running. Only the requested final CSV was delivered. |
| Independent file verification | Five gaps matched the fixture: 14, 14, 10, 7 and 2, sorted descending and including incoming stock. |
| Chinese stop | “停一下” stopped an executing foreground test. Its started marker existed; its completion marker did not appear after the original deadline. |
| Context compression | A lowered native test threshold triggered real pre-turn compression. The chat showed the summary-in-progress state; Hermes continued the answer and later adopted the summary. Original settings were restored. |
| Compression deferral | A second real run confirmed the Chinese notice that Hermes continues with the original conversation while its summary is pending, without reporting a failure. Original settings were restored. |
| English menu | The welcome text and visible buttons rendered in English in the Telegram client. Native callback authorization and menu navigation also have automated coverage. |
| English execution and delivery | English model reply and generated file delivered the correct sum, 5050. |
| English waiting and stop | The acknowledgement, model action update, long-wait text and “Stop requested” receipt appeared in English. The executing test was stopped before its completion marker. |

Four Chinese intake samples took 0.582–0.588 seconds to receive Telegram's send acknowledgement; the first two English samples took 0.610 and 0.662 seconds. These timings start at plugin intake, not at the user's send button, and are observations rather than a latency guarantee.

The client was operated through its native UI for messages and inspected through accessibility text and screenshots. Coordinate clicking was unavailable in this desktop session, so menu button execution is covered by native callback tests rather than claimed as a completed mouse-click check. No model or Telegram credentials are used in CI.

The in-turn compression callback and exceptional outcomes have automated coverage against the native core; the real compression runs above exercised the pre-turn path. Group/topic isolation has regression coverage; these live scenarios used a private chat. Model-generated wording remains dependent on the selected model and task instructions.
