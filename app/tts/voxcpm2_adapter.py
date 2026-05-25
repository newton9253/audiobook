"""VoxCPM2 TTS 适配器"""

import base64
import httpx
from typing import Optional

from .base import TTSAdapter


class VoxCPM2Adapter(TTSAdapter):
    """VoxCPM2 API 适配器"""

    def __init__(self, base_url: str = "http://localhost:5022"):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def test_connection(self) -> bool:
        """测试 VoxCPM2 连接"""
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/api/tts",
                json={
                    "text": "测试连接",
                    "prompt": "年轻女性",
                },
                timeout=30.0,
            )
            data = resp.json()
            return data.get("status") == "success"
        except Exception:
            return False

    async def synthesize(
        self, text: str, prompt: str = "",
        reference_audio: Optional[bytes] = None,
    ) -> dict:
        """
        调用 VoxCPM2 TTS API

        Returns:
            {"audio": "<base64 wav>", "sample_rate": 48000, "status": "success"}
        """
        client = await self._get_client()

        payload = {
            "text": text,
            "prompt": prompt,
        }

        if reference_audio:
            # 按照 API 文档：参考音频的 Base64 编码，可带 data:audio/wav;base64, 前缀
            audio_b64 = base64.b64encode(reference_audio).decode("utf-8")
            payload["audio"] = f"data:audio/wav;base64,{audio_b64}"

        resp = await client.post(
            f"{self.base_url}/api/tts",
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
        """声音设计模式 —— 纯文字描述创建音色"""
        return await self.synthesize(text, prompt=description)
