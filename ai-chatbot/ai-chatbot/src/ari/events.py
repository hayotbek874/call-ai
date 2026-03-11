from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class ARICallerID(BaseModel):
    number: str = ""
    name: str = ""

class ARIDialplan(BaseModel):
    context: str = ""
    exten: str = ""
    priority: int = 0
    app_name: str = Field("", alias="app_name")
    app_data: str = Field("", alias="app_data")

    model_config = {"populate_by_name": True}

class ARIChannel(BaseModel):
    id: str
    name: str = ""
    state: str = ""
    caller: ARICallerID = Field(default_factory=ARICallerID)
    connected: ARICallerID = Field(default_factory=ARICallerID)
    accountcode: str = ""
    dialplan: ARIDialplan = Field(default_factory=ARIDialplan)
    creationtime: str = ""
    language: str = "en"

class ARIBridge(BaseModel):
    id: str
    technology: str = ""
    bridge_type: str = ""
    bridge_class: str = ""
    channels: list[str] = Field(default_factory=list)
    name: str = ""

class ARIPlayback(BaseModel):
    id: str
    media_uri: str = ""
    target_uri: str = ""
    language: str = "en"
    state: str = ""

class ARIEvent(BaseModel):
    type: str
    application: str = ""
    timestamp: str = ""
    asterisk_id: str = ""

    channel: ARIChannel | None = None
    bridge: ARIBridge | None = None
    playback: ARIPlayback | None = None

    raw: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

class StasisStartEvent(ARIEvent):
    type: Literal["StasisStart"] = "StasisStart"
    args: list[str] = Field(default_factory=list)
    channel: ARIChannel

class StasisEndEvent(ARIEvent):
    type: Literal["StasisEnd"] = "StasisEnd"
    channel: ARIChannel

class ChannelDestroyedEvent(ARIEvent):
    type: Literal["ChannelDestroyed"] = "ChannelDestroyed"
    cause: int = 0
    cause_txt: str = ""
    channel: ARIChannel

class PlaybackFinishedEvent(ARIEvent):
    type: Literal["PlaybackFinished"] = "PlaybackFinished"
    playback: ARIPlayback

class ChannelStateChangeEvent(ARIEvent):
    type: Literal["ChannelStateChange"] = "ChannelStateChange"
    channel: ARIChannel

class ChannelDtmfReceivedEvent(ARIEvent):
    type: Literal["ChannelDtmfReceived"] = "ChannelDtmfReceived"
    digit: str = ""
    duration_ms: int = 0
    channel: ARIChannel

class BridgeCreatedEvent(ARIEvent):
    type: Literal["BridgeCreated"] = "BridgeCreated"
    bridge: ARIBridge

class ChannelEnteredBridgeEvent(ARIEvent):
    type: Literal["ChannelEnteredBridge"] = "ChannelEnteredBridge"
    bridge: ARIBridge
    channel: ARIChannel

class ChannelLeftBridgeEvent(ARIEvent):
    type: Literal["ChannelLeftBridge"] = "ChannelLeftBridge"
    bridge: ARIBridge
    channel: ARIChannel

EVENT_TYPE_MAP: dict[str, type[ARIEvent]] = {
    "StasisStart": StasisStartEvent,
    "StasisEnd": StasisEndEvent,
    "ChannelDestroyed": ChannelDestroyedEvent,
    "PlaybackFinished": PlaybackFinishedEvent,
    "ChannelStateChange": ChannelStateChangeEvent,
    "ChannelDtmfReceived": ChannelDtmfReceivedEvent,
    "BridgeCreated": BridgeCreatedEvent,
    "ChannelEnteredBridge": ChannelEnteredBridgeEvent,
    "ChannelLeftBridge": ChannelLeftBridgeEvent,
}

def parse_ari_event(data: dict[str, Any]) -> ARIEvent:
    event_type = data.get("type", "")
    model_cls = EVENT_TYPE_MAP.get(event_type, ARIEvent)
    event = model_cls.model_validate(data)
    event.raw = data
    return event
