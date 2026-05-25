"""LLM 适配器抽象基类"""

from abc import ABC, abstractmethod
from typing import Iterator


class LLMAdapter(ABC):
    """LLM 适配器基类"""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """非流式对话"""
        ...

    @abstractmethod
    async def chat_stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        """流式对话"""
        ...

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """验证配置是否有效"""
        ...
