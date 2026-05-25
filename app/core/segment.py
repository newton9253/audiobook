"""片段数据模型"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Segment:
    """文本片段 —— 旁白或对话"""
    index: int = 0
    text: str = ""
    type: str = "narration"  # "narration" | "dialogue"
    speaker_id: Optional[str] = None   # 角色 ID，旁白为 None
    speaker_name: str = ""             # 角色名（冗余，方便显示）
    emotion: str = ""                  # 情感分类
    emotion_prompt: str = ""           # TTS 情感 prompt
    audio_path: Optional[str] = None   # 合成后的音频路径
    delay: float = 0.4                 # 段间延迟（秒），默认 0.4s

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "text": self.text,
            "type": self.type,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "emotion": self.emotion,
            "emotion_prompt": self.emotion_prompt,
            "audio_path": self.audio_path,
            "delay": self.delay,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Segment":
        return cls(
            index=data.get("index", 0),
            text=data.get("text", ""),
            type=data.get("type", "narration"),
            speaker_id=data.get("speaker_id"),
            speaker_name=data.get("speaker_name", ""),
            emotion=data.get("emotion", ""),
            emotion_prompt=data.get("emotion_prompt", ""),
            audio_path=data.get("audio_path"),
            delay=data.get("delay", 0.4),
        )
