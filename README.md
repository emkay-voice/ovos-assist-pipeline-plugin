# ovos-assist-pipeline-plugin

An [OpenVoiceOS](https://openvoiceos.org) intent pipeline plugin: what
[Home Assistant](https://www.home-assistant.io)'s Assist recognizes goes to
Home Assistant.

"Turn on the light in the kitchen", "what's the temperature in the bedroom",
"close the blinds": Home Assistant already understands these, with its own
sentences, its areas and devices, in its users' languages. This plugin lets
OVOS hand them over, and keeps everything else for OVOS.

Made for [Emkay](https://emkay.ai), and works on any OVOS.

## How it decides

It is a stage in OVOS' intent pipeline. Put it after OVOS' sure matches and
before common query, persona and fallback:

```json
{
  "intents": {
    "pipeline": ["converse", "stop", "ocp_high", "padatious_high", "adapt_high",
                 "ovos-assist-pipeline-plugin",
                 "common_qa", "ovos-persona-pipeline-plugin-high", "...", "fallback_low"]
  }
}
```

For each utterance it asks Home Assistant whether its own sentence matching
(the built-in conversation agent) **recognizes** it. That only recognizes and
does nothing. Only then does the plugin take the utterance, and Home
Assistant carries it out and gives the answer, which OVOS speaks. Anything
Home Assistant doesn't recognize goes on down the pipeline as before. So a
question to a solver never ends up switching lights, and "turn on the light"
never ends up with a chatbot.

Home Assistant knows which device asked, so "turn on the light" means the
light in the room the device is in.

## What it needs

The plugin only sends bus messages. The device's **link to Home Assistant**
does the talking:

- in [Emkay](https://emkay.ai), the page, when Emkay is connected to Home Assistant
- on an ordinary OVOS, [ovos-phal-plugin-ha-link](https://github.com/emkay-voice/ovos-phal-plugin-ha-link)

So there is no address or token to set here. Without a link, the plugin
steps aside and the pipeline runs as if it wasn't there.

| Bus message | |
|---|---|
| `ovos.assist.available` | the link says it is there (`{"available": true}`), also as the answer to `ovos.assist.ping` |
| `ovos.assist.recognize` → `.response` | `{utterance, lang}` → `{match, intent}` |
| `ovos.assist.process` → `.response` | `{utterance, lang}` → `{speech, response_type}` |

Another link can answer the same messages.

## Install

```bash
pip install --pre ovos-assist-pipeline-plugin
```

and add `ovos-assist-pipeline-plugin` to `intents.pipeline` as above.

| Setting (under `intents` → `ovos-assist-pipeline-plugin`) | |
|---|---|
| `recognize_timeout` | seconds to wait for Home Assistant per utterance (default 2) |
| `process_timeout` | seconds to wait for its answer (default 10) |

## Good to know

- Recognizing is Home Assistant's sentence matching only. It tells whether
  Home Assistant understands the sentence, not whether the thing exists:
  "what's the temperature in the kitchen" is taken even if the kitchen has
  no thermometer, and then Home Assistant says it couldn't do it.
- It uses Home Assistant's built-in agent (`conversation.home_assistant`), the
  one that recognized the sentence, even if your Assist pipeline has an LLM.

## License

Apache-2.0
