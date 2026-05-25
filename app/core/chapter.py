"""章节数据模型"""

from dataclasses import dataclass, field

from .segment import Segment


@dataclass
class Chapter:
    """小说章节"""
    index: int = 0
    title: str = ""
    raw_text: str = ""     # 原始文本
    status: str = "raw"    # "raw" | "structured" | "synthesized"
    segments: list[Segment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "raw_text": self.raw_text,
            "status": self.status,
            "segments": [s.to_dict() for s in self.segments],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chapter":
        segments = [Segment.from_dict(s) for s in data.get("segments", [])]
        return cls(
            index=data.get("index", 0),
            title=data.get("title", ""),
            raw_text=data.get("raw_text", ""),
            status=data.get("status", "raw"),
            segments=segments,
        )

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    @property
    def synthesized_count(self) -> int:
        return sum(1 for s in self.segments if s.audio_path)
