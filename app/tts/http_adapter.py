"""通用 HTTP TTS 适配器"""

import base64
import httpx
from typing import Optional

from .base import TTSAdapter


class HttpTTSAdapter(TTSAdapter):
    """通用 HTTP TTS 接口适配器"""

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def test_connection(self) -> bool:
        return bool(self.base_url)

    async def synthesize(
        self, text: str, prompt: str = "",
        reference_audio: Optional[bytes] = None,
    ) -> dict:
        if not self.base_url:
            raise RuntimeError("TTS Base URL 未配置")

        client = await self._get_client()

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"text": text}
        if prompt:
            payload["prompt"] = prompt
        if reference_audio:
            payload["audio"] = base64.b64encode(reference_audio).decode("utf-8")

        resp = await client.post(
            f"{self.base_url}/api/tts",
            headers=headers,
            json=payload,
        )

        data = resp.json()

        if data.get("status") != "success":
            raise RuntimeError(data.get("message", "TTS 合成失败"))

        return {
            "audio": data["audio"],
            "sample_rate": data.get("sample_rate", 48000),
            "status": "success",
        }

    async def voice_design(self, text: str, description: str) -> dict:
        return await self.synthesize(text, prompt=description)
