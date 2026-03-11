import asyncio
import uuid as uuid_lib

from src.core.logging import get_logger

logger = get_logger(__name__)

FRAME_HANGUP: int = 0x00
FRAME_UUID: int = 0x01
FRAME_SILENCE: int = 0x02
FRAME_AUDIO: int = 0x10
FRAME_ERROR: int = 0xFF

async def read_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:

    header = await reader.readexactly(3)
    frame_type = header[0]
    length = int.from_bytes(header[1:3], "big")
    payload = await reader.readexactly(length) if length > 0 else b""
    return frame_type, payload

def build_audio_frame(pcm_data: bytes) -> bytes:

    length = len(pcm_data)
    return bytes([FRAME_AUDIO]) + length.to_bytes(2, "big") + pcm_data

def build_hangup_frame() -> bytes:

    return bytes([FRAME_HANGUP, 0x00, 0x00])

class AudioSocketServer:

    def __init__(
        self,
        host: str,
        port: int,
        on_connection,
    ):
        self._host = host
        self._port = port
        self._on_connection = on_connection
        self._server: asyncio.Server | None = None

    async def start(self) -> None:

        self._server = await asyncio.start_server(
            self._handle_client,
            self._host,
            self._port,
        )
        addr = self._server.sockets[0].getsockname()
        await logger.info("audiosocket_server_started", host=addr[0], port=addr[1])

    async def stop(self) -> None:

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            await logger.info("audiosocket_server_stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:

        peer = writer.get_extra_info("peername")
        await logger.info("audiosocket_tcp_connect", peer=str(peer))

        try:

            frame_type, payload = await asyncio.wait_for(
                read_frame(reader), timeout=5.0,
            )
            if frame_type != FRAME_UUID:
                await logger.warning(
                    "audiosocket_bad_first_frame",
                    type=hex(frame_type),
                    peer=str(peer),
                )
                writer.close()
                return

            raw = payload
            if len(raw) == 16:
                hex_str = raw.hex()

                uuid_str = (
                    f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}"
                    f"-{hex_str[16:20]}-{hex_str[20:]}"
                )
                phone_hex = hex_str[20:]
                phone = phone_hex.lstrip("0") or "0"
            else:
                uuid_str = raw.decode("utf-8", errors="replace").strip()
                phone = ""

            session_id = str(uuid_lib.uuid4())

            await logger.info(
                "audiosocket_call_identified",
                uuid=uuid_str,
                session_id=session_id,
                phone=phone,
            )

            await self._on_connection(session_id, phone, reader, writer)

        except asyncio.TimeoutError:
            await logger.warning("audiosocket_uuid_timeout", peer=str(peer))
        except (EOFError, ConnectionResetError, asyncio.IncompleteReadError):
            await logger.info("audiosocket_disconnect", peer=str(peer))
        except Exception as e:
            await logger.error("audiosocket_error", error=str(e), peer=str(peer))
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
