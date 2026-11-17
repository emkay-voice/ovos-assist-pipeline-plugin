"""Try the pipeline stage against a Home Assistant, through ovos-phal-plugin-ha-link:

    ovos-messagebus &
    HA_URL=http://127.0.0.1:8123 HA_TOKEN=... python tests/try_assist.py "turn on the kitchen lights" "who was niels bohr"

For each sentence: does the stage take it (HA recognizes it), and if so,
what HA says when it carries it out.
"""
import os
import sys
import time

from ovos_bus_client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_phal_plugin_ha_link import HALinkPlugin

from ovos_assist_pipeline import HANDLE, AssistPipeline

bus = MessageBusClient()
bus.run_in_thread()
bus.connected_event.wait(10)
said = []
bus.on("speak", lambda m: said.append(m.data.get("utterance")))

link = HALinkPlugin(bus=bus, config={"url": os.environ["HA_URL"], "token": os.environ["HA_TOKEN"],
                                     "name": "OVOS link test", "device_id": "ovos-link-test-0001",
                                     "panel_url": False})
stage = AssistPipeline(bus=bus, config={})
for _ in range(50):
    if stage.available:
        break
    time.sleep(0.2)
print("Home Assistant there:", stage.available)

for sentence in sys.argv[1:] or ["turn on the kitchen lights", "who was niels bohr"]:
    t = time.monotonic()
    match = stage.match([sentence], "en-us", Message("recognizer_loop:utterance", {"utterances": [sentence]}))
    took = time.monotonic() - t
    if match is None:
        print(f"{sentence!r}: not Home Assistant's ({took:.2f} s) -> on down the pipeline")
        continue
    print(f"{sentence!r}: Home Assistant's, {match.match_data['intent']} ({took:.2f} s)")
    said.clear()
    bus.emit(Message(HANDLE, match.match_data))
    for _ in range(50):
        if said:
            break
        time.sleep(0.2)
    print("   Home Assistant says:", said[0] if said else None)
link.shutdown()
