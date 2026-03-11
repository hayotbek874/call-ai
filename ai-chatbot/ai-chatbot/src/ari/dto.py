from dataclasses import dataclass, field
from enum import StrEnum
import time

class ChannelState(StrEnum):
    RING = "Ring"
    RINGING = "Ringing"
    UP = "Up"
    DOWN = "Down"
    BUSY = "Busy"

class BridgeType(StrEnum):
    MIXING = "mixing"
    HOLDING = "holding"
    DTMF_EVENTS = "dtmf_events"
    PROXY_MEDIA = "proxy_media"

class PlaybackState(StrEnum):
    QUEUED = "queued"
    PLAYING = "playing"
    DONE = "done"
    FAILED = "failed"

@dataclass(slots=True)
class ChannelDTO:
    id: str
    name: str
    state: ChannelState
    caller_number: str
    caller_name: str
    connected_number: str = ""
    connected_name: str = ""
    accountcode: str = ""
    dialplan_context: str = ""
    dialplan_exten: str = ""
    dialplan_priority: int = 0
    language: str = "en"
    creation_time: str = ""

    @classmethod
    def from_ari(cls, data: dict) -> "ChannelDTO":
        caller = data.get("caller", {})
        connected = data.get("connected", {})
        dialplan = data.get("dialplan", {})
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            state=ChannelState(data.get("state", "Down")),
            caller_number=caller.get("number", ""),
            caller_name=caller.get("name", ""),
            connected_number=connected.get("number", ""),
            connected_name=connected.get("name", ""),
            accountcode=data.get("accountcode", ""),
            dialplan_context=dialplan.get("context", ""),
            dialplan_exten=dialplan.get("exten", ""),
            dialplan_priority=dialplan.get("priority", 0),
            language=data.get("language", "en"),
            creation_time=data.get("creationtime", ""),
        )

@dataclass(slots=True)
class BridgeDTO:
    id: str
    technology: str
    bridge_type: str
    bridge_class: str
    channels: list[str]
    name: str = ""

    @classmethod
    def from_ari(cls, data: dict) -> "BridgeDTO":
        return cls(
            id=data["id"],
            technology=data.get("technology", ""),
            bridge_type=data.get("bridge_type", ""),
            bridge_class=data.get("bridge_class", ""),
            channels=data.get("channels", []),
            name=data.get("name", ""),
        )

@dataclass(slots=True)
class PlaybackDTO:
    id: str
    media_uri: str
    target_uri: str
    language: str
    state: PlaybackState

    @classmethod
    def from_ari(cls, data: dict) -> "PlaybackDTO":
        return cls(
            id=data["id"],
            media_uri=data.get("media_uri", ""),
            target_uri=data.get("target_uri", ""),
            language=data.get("language", "en"),
            state=PlaybackState(data.get("state", "queued")),
        )

@dataclass(slots=True)
class CallSessionDTO:
    channel_id: str
    caller_number: str
    app_name: str
    bridge_id: str | None = None
    playback_id: str | None = None
    language: str = "en"
    start_time: float = field(default_factory=time.monotonic)
    is_active: bool = True
    metadata: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return time.monotonic() - self.start_time
