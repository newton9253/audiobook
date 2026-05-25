"""项目数据模型"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .chapter import Chapter
from .character import Character, VoiceConfig


@dataclass
class ProjectMetadata:
    """项目元数据"""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = "未命名项目"
    author: str = ""
    source_path: str = ""         # 原始 TXT 路径
    project_path: str = ""        # .awb 文件路径
    output_dir: str = ""          # 项目输出目录（音频文件存放处），空则用默认 OUTPUT_DIR
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProjectSettings:
    """项目级设置"""
    llm_provider: str = "openai"
    tts_provider: str = "voxcpm2"
    tts_base_url: str = "http://localhost:5022"


@dataclass
class Project:
    """有声书项目"""
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    chapters: list[Chapter] = field(default_factory=list)
    characters: list[Character] = field(default_factory=list)
    narrator: VoiceConfig = field(default_factory=lambda: VoiceConfig(
        prompt="专业播音员，沉稳大气，语速适中，声音清晰富有磁性"
    ))
    narrator_gender: str = "中性"
    narrator_age: str = "成年"
    narrator_personality: str = "客观中立，娓娓道来，富有感染力"
    narrator_role: str = "旁白/叙述者"
    playback_speed: float = 1.0  # 播放速度倍率，1.0=原速，0.5~1.5 范围，播放和打包共用
    text_replacements: list[dict] = field(default_factory=list)  # 文字替换规则 [{from, to}, ...]
    settings: ProjectSettings = field(default_factory=ProjectSettings)

    def to_dict(self) -> dict:
        return {
            "metadata": {
                "id": self.metadata.id,
                "title": self.metadata.title,
                "author": self.metadata.author,
                "source_path": self.metadata.source_path,
                "project_path": self.metadata.project_path,
                "output_dir": self.metadata.output_dir,
                "created_at": self.metadata.created_at,
                "modified_at": self.metadata.modified_at,
            },
            "chapters": [c.to_dict() for c in self.chapters],
            "characters": [c.to_dict() for c in self.characters],
            "narrator": {
                "mode": self.narrator.mode,
                "prompt": self.narrator.prompt,
                "reference_audio": self.narrator.reference_audio,
                "sample_audio": self.narrator.sample_audio,
                "gender": self.narrator_gender,
                "age": self.narrator_age,
                "personality": self.narrator_personality,
                "role": self.narrator_role,
            },
            "playback_speed": self.playback_speed,
            "text_replacements": self.text_replacements,
            "settings": {
                "llm_provider": self.settings.llm_provider,
                "tts_provider": self.settings.tts_provider,
                "tts_base_url": self.settings.tts_base_url,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        meta = data.get("metadata", {})
        metadata = ProjectMetadata(
            id=meta.get("id", str(uuid4())),
            title=meta.get("title", "未命名项目"),
            author=meta.get("author", ""),
            source_path=meta.get("source_path", ""),
            project_path=meta.get("project_path", ""),
            output_dir=meta.get("output_dir", ""),
            created_at=meta.get("created_at", datetime.now().isoformat()),
            modified_at=meta.get("modified_at", datetime.now().isoformat()),
        )

        chapters = [Chapter.from_dict(c) for c in data.get("chapters", [])]
        characters = [Character.from_dict(c) for c in data.get("characters", [])]

        narrator_data = data.get("narrator", {})
        narrator = VoiceConfig(
            mode=narrator_data.get("mode", "design"),
            prompt=narrator_data.get("prompt", "专业播音员，沉稳大气，语速适中，声音清晰富有磁性"),
            reference_audio=narrator_data.get("reference_audio"),
            sample_audio=narrator_data.get("sample_audio"),
        )

        settings_data = data.get("settings", {})
        settings = ProjectSettings(
            llm_provider=settings_data.get("llm_provider", "openai"),
            tts_provider=settings_data.get("tts_provider", "voxcpm2"),
            tts_base_url=settings_data.get("tts_base_url", "http://localhost:5022"),
        )

        # 兼容旧版 tts_speed 字符串格式
        raw_speed = data.get("playback_speed", data.get("tts_speed", 1.0))
        if isinstance(raw_speed, str):
            raw_speed = {"slow": 0.7, "normal": 1.0, "fast": 1.3}.get(raw_speed, 1.0)
        playback_speed = float(raw_speed)

        return cls(
            metadata=metadata,
            chapters=chapters,
            characters=characters,
            narrator=narrator,
            narrator_gender=narrator_data.get("gender", "中性"),
            narrator_age=narrator_data.get("age", "成年"),
            narrator_personality=narrator_data.get("personality", "客观中立，娓娓道来，富有感染力"),
            narrator_role=narrator_data.get("role", "旁白/叙述者"),
            playback_speed=playback_speed,
            text_replacements=data.get("text_replacements", []),
            settings=settings,
        )

    def touch(self):
        """更新修改时间"""
        self.metadata.modified_at = datetime.now().isoformat()

    @property
    def output_dir(self) -> str:
        """获取项目输出目录（用户选择的或默认的）"""
        from app.utils.constants import OUTPUT_DIR
        od = self.metadata.output_dir
        if not od:
            od = os.path.join(OUTPUT_DIR, self.metadata.id)
        return od

    def find_character_by_name(self, name: str) -> Optional[Character]:
        """按姓名或别名查找角色"""
        for char in self.characters:
            if char.name == name or name in char.aliases:
                return char
        return None

    def merge_characters(self, new_characters: list[Character]) -> list[Character]:
        """合并新角色到项目角色列表（去重）"""
        existing_names = {c.name for c in self.characters}
        existing_aliases = set()
        for c in self.characters:
            existing_aliases.update(c.aliases)

        for new_char in new_characters:
            if new_char.name not in existing_names:
                # 检查别名冲突
                if not any(a in existing_aliases for a in new_char.aliases):
                    self.characters.append(new_char)
                    existing_names.add(new_char.name)
                    existing_aliases.update(new_char.aliases)

        return self.characters
