"""角色数据模型"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4


@dataclass
class VoiceConfig:
    """声音配置"""
    mode: str = "design"  # "design" | "clone"
    prompt: str = ""      # 声音设计 prompt
    reference_audio: Optional[str] = None  # 参考音频路径
    sample_audio: Optional[str] = None     # 试听音频路径


@dataclass
class Character:
    """小说角色"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    aliases: list[str] = field(default_factory=list)
    gender: str = ""         # 男/女/未知
    age: str = ""            # 年龄描述
    personality: str = ""    # 性格描述
    role: str = ""           # 角色定位：主角/配角/反派等
    voice_description: str = ""  # 音色描述（给 TTS 用）
    voice: VoiceConfig = field(default_factory=VoiceConfig)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": self.aliases,
            "gender": self.gender,
            "age": self.age,
            "personality": self.personality,
            "role": self.role,
            "voice_description": self.voice_description,
            "voice": {
                "mode": self.voice.mode,
                "prompt": self.voice.prompt,
                "reference_audio": self.voice.reference_audio,
                "sample_audio": self.voice.sample_audio,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        voice_data = data.get("voice", {})
        voice = VoiceConfig(
            mode=voice_data.get("mode", "design"),
            prompt=voice_data.get("prompt", ""),
            reference_audio=voice_data.get("reference_audio"),
            sample_audio=voice_data.get("sample_audio"),
        )
        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            aliases=data.get("aliases", []),
            gender=data.get("gender", ""),
            age=data.get("age", ""),
            personality=data.get("personality", ""),
            role=data.get("role", ""),
            voice_description=data.get("voice_description", ""),
            voice=voice,
        )
