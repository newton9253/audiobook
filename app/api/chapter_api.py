"""章节操作 API —— 完整实现"""

from fastapi import APIRouter, HTTPException
from app.core.segment import Segment
from .store import store

router = APIRouter(tags=["章节操作"])


@router.get("/projects/{project_id}/chapters")
async def list_chapters(project_id: str):
    """获取章节列表（仅摘要）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chapters_summary = [
        {
            "index": c.index,
            "title": c.title,
            "status": c.status,
            "segment_count": c.segment_count,
            "synthesized_count": c.synthesized_count,
            "text_length": len(c.raw_text),
        }
        for c in project.chapters
    ]
    return {"chapters": chapters_summary}


@router.get("/projects/{project_id}/chapters/{chapter_idx}")
async def get_chapter(project_id: str, chapter_idx: int):
    """获取章节详情（含 segments）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chapter = _find_chapter(project, chapter_idx)
    return chapter.to_dict()


@router.put("/projects/{project_id}/chapters/{chapter_idx}")
async def update_chapter(project_id: str, chapter_idx: int, data: dict):
    """更新章节（segments 编辑）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chapter = _find_chapter(project, chapter_idx)

    if "segments" in data:
        chapter.segments = [Segment.from_dict(s) for s in data["segments"]]
    if "status" in data:
        chapter.status = data["status"]

    project.touch()
    return chapter.to_dict()


@router.put("/projects/{project_id}/chapters/{chapter_idx}/segment/{segment_idx}")
async def update_segment(project_id: str, chapter_idx: int, segment_idx: int, data: dict):
    """更新单个 segment"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chapter = _find_chapter(project, chapter_idx)

    if segment_idx < 0 or segment_idx >= len(chapter.segments):
        raise HTTPException(status_code=404, detail="Segment 未找到")

    segment = chapter.segments[segment_idx]
    for key in ("text", "type", "speaker_id", "speaker_name", "emotion", "emotion_prompt"):
        if key in data:
            setattr(segment, key, data[key])

    project.touch()
    return segment.to_dict()


@router.delete("/projects/{project_id}/chapters/{chapter_idx}/reset")
async def reset_chapter(project_id: str, chapter_idx: int):
    """重置章节到原始状态"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chapter = _find_chapter(project, chapter_idx)
    chapter.segments = []
    chapter.status = "raw"
    project.touch()

    return {"status": "ok"}


def _find_chapter(project, chapter_idx: int):
    """根据 index 查找章节"""
    for c in project.chapters:
        if c.index == chapter_idx:
            return c
    raise HTTPException(status_code=404, detail="章节未找到")
