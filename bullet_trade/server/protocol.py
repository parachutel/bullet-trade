from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

HEADER_SIZE = 4
MAX_FRAME_SIZE = 32 * 1024 * 1024  # 32MB


class ProtocolError(Exception):
    """Framing 或 JSON 解析异常"""


def encode_message(message: Dict[str, Any]) -> bytes:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_FRAME_SIZE:
        raise ProtocolError("消息过大")
    header = len(body).to_bytes(HEADER_SIZE, "big")
    return header + body


async def read_message(reader: asyncio.StreamReader) -> Dict[str, Any]:
    header = await reader.readexactly(HEADER_SIZE)
    size = int.from_bytes(header, "big")
    if size > MAX_FRAME_SIZE:
        raise ProtocolError(f"帧大小 {size} 超过限制 {MAX_FRAME_SIZE}")
    payload = await reader.readexactly(size)
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ProtocolError("JSON 解析失败") from exc


async def write_message(writer: asyncio.StreamWriter, message: Dict[str, Any]) -> None:
    frame = encode_message(message)
    writer.write(frame)
    await writer.drain()
