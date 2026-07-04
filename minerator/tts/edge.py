from __future__ import annotations

import asyncio

import edge_tts


class EdgeTTS:
    def __init__(self, voice: str) -> None:
        self._voice = voice

    def synthesize(self, text: str) -> bytes:
        return asyncio.run(self._synthesize(text))

    async def _synthesize(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(text, self._voice)
        chunks = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.extend(chunk["data"])
        return bytes(chunks)
