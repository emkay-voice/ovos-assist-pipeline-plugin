"""ovos-assist-pipeline-plugin: what Home Assistant's Assist recognizes goes
to Home Assistant.

An OVOS intent pipeline stage. Put it after OVOS' sure matches and before
common query, persona and fallback:

    "intents": {"pipeline": ["converse", "stop", "ocp_high", "padatious_high",
                             "adapt_high", "ovos-assist-pipeline-plugin",
                             "common_qa", ...]}

For each utterance it asks Home Assistant whether its own sentence matching
(the built-in agent: its sentences, areas, devices, in the user's language)
recognizes it -- recognising only, nothing is done. Only then does the
plugin take the utterance, and Home Assistant carries it out ("turn on the
light in the kitchen", "what's the temperature in the bedroom"). Everything
else goes on down the pipeline as before, so a solver never gets "turn on
the light", and Home Assistant never gets "who was Niels Bohr".

OVOS style: the plugin only sends bus messages. The device's link to Home
Assistant does the talking -- in Emkay the page, on an ordinary OVOS
ovos-phal-plugin-ha-link -- so there is no token and no address here:

    ovos.assist.available     the link says it is there (or not), also as
                              the answer to ovos.assist.ping
    ovos.assist.recognize     {utterance, lang} -> .response {match, intent}
    ovos.assist.process       {utterance, lang} -> .response {speech, ...}
"""
from __future__ import annotations

from typing import Dict, List, Optional, Union

from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch, PipelinePlugin
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG

PLUGIN_ID = "ovos-assist-pipeline-plugin"
HANDLE = "ovos.assist.handle"


class AssistPipeline(PipelinePlugin):
    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        super().__init__(bus, config)
        # how long to wait for Home Assistant, per utterance (it is in the house)
        self.recognize_timeout = float(self.config.get("recognize_timeout", 2))
        self.process_timeout = float(self.config.get("process_timeout", 10))
        self.available = False
        self.bus.on("ovos.assist.available", self._on_available)
        self.bus.on(HANDLE, self.handle)
        self.bus.emit(Message("ovos.assist.ping"))

    def _on_available(self, message: Message) -> None:
        available = bool(message.data.get("available", True))
        if available != self.available:
            LOG.info(f"{PLUGIN_ID}: Home Assistant {'is' if available else 'is not'} there")
        self.available = available

    # --- matching: only what Home Assistant itself recognizes -------------------

    def match(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        if not self.available:
            return None
        for utterance in utterances:
            if isinstance(utterance, (list, tuple)):     # old style (utterance, normalized)
                utterance = utterance[0]
            answer = self.bus.wait_for_response(
                message.forward("ovos.assist.recognize", {"utterance": utterance, "lang": lang}),
                "ovos.assist.recognize.response", timeout=self.recognize_timeout)
            if answer is None:
                LOG.debug(f"{PLUGIN_ID}: no answer from the link")
                continue
            if answer.data.get("match"):
                return IntentHandlerMatch(
                    match_type=HANDLE, skill_id=PLUGIN_ID, utterance=utterance,
                    match_data={"utterance": utterance, "lang": lang,
                                "intent": answer.data.get("intent")})
        return None

    # --- handling: Home Assistant carries it out ------------------------------

    def handle(self, message: Message) -> None:
        utterance = message.data.get("utterance")
        lang = message.data.get("lang")
        answer = self.bus.wait_for_response(
            message.forward("ovos.assist.process", {"utterance": utterance, "lang": lang}),
            "ovos.assist.process.response", timeout=self.process_timeout)
        speech = answer.data.get("speech") if answer else None
        if speech:
            self.bus.emit(message.forward("speak", {"utterance": speech, "lang": lang,
                                                    "meta": {"skill": PLUGIN_ID}}))
        elif answer is None:
            LOG.warning(f"{PLUGIN_ID}: Home Assistant did not answer: {utterance}")
        self.bus.emit(message.forward("ovos.utterance.handled", {"name": PLUGIN_ID}))
