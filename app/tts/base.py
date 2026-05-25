"""TTS 适配器抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional


class TTSAdapter(ABC):
    """TTS 适配器基类"""

    @abstractmethod
    async def synthesize(
        self, text: str, prompt: str = "",
        reference_audio: Optional[bytes] = None,
    ) -> dict:
        """
        语音合成

        Args:
            text: 要合成的文本
            prompt: 声音设计/风格 prompt
            reference_audio: 参考音频 bytes（可选）

        Returns:
            {"audio": "<base64 wav>", "sample_rate": 48000}
        """
        ...

    @abstractmethod
    async def voice_design(self, text: str, description: str) -> dict:
        """声音设计：通过描述创建音色"""
        ...

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        ...
