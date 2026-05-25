"""LLM 结构化 API —— 完整实现"""

import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.llm.llm_manager import LLMManager
from app.core.character import Character
from app.core.segment import Segment
from .store import store

router = APIRouter(tags=["LLM 结构化"])


def _compute_delay(seg_type: str, prev_type: str, speaker: str, prev_speaker: str) -> float:
    """根据段落类型和角色切换计算段间延迟（秒）"""
    # 文本结尾有句号/问号/感叹号 → 额外增加
    if seg_type == "narration" and prev_type == "narration":
        return 0.35  # 旁白→旁白：自然呼吸停顿
    elif seg_type == "dialogue" and prev_type == "narration":
        return 0.5   # 旁白→对话：场景转换停顿
    elif seg_type == "narration" and prev_type == "dialogue":
        return 0.5   # 对话→旁白：语气转换停顿
    elif seg_type == "dialogue" and prev_type == "dialogue":
        if speaker != prev_speaker:
            return 0.45  # 不同人对话：角色切换停顿
        else:
            return 0.3   # 同一人继续说话：短停顿
    return 0.4  # 默认


@router.post("/projects/{project_id}/chapters/{chapter_idx}/structure")
async def structure_chapter(project_id: str, chapter_idx: int):
    """对单个章节进行 LLM 结构化处理"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    # 查找章节
    chapter = None
    for c in project.chapters:
        if c.index == chapter_idx:
            chapter = c
            break
    if not chapter:
        raise HTTPException(status_code=404, detail="章节未找到")

    if not chapter.raw_text.strip():
        raise HTTPException(status_code=400, detail="章节文本为空")

    # 收集已有角色信息
    existing_chars = [
        {
            "name": c.name,
            "aliases": c.aliases,
            "gender": c.gender,
            "age": c.age,
            "role": c.role,
        }
        for c in project.characters
    ]

    try:
        result = await LLMManager.structure_chapter(chapter.raw_text, existing_chars)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 请求失败: {str(e)}")

    # 处理返回的角色
    new_characters = []
    if "characters" in result:
        for char_data in result["characters"]:
            char = Character.from_dict({
                "name": char_data.get("name", ""),
                "aliases": char_data.get("aliases", []),
                "gender": char_data.get("gender", ""),
                "age": char_data.get("age", ""),
                "personality": char_data.get("personality", ""),
                "role": char_data.get("role", ""),
                "voice_description": char_data.get("voice_description", ""),
            })
            # 默认声音设计 prompt
            if not char.voice.prompt and char.voice_description:
                char.voice.prompt = char.voice_description
            new_characters.append(char)

    # 合并角色
    project.merge_characters(new_characters)

    # 处理 segments
    if "segments" in result:
        segments = []
        for i, seg_data in enumerate(result["segments"]):
            speaker_name = seg_data.get("speaker", "")
            speaker_id = None

            # 匹配角色 ID
            if speaker_name:
                char = project.find_character_by_name(speaker_name)
                if char:
                    speaker_id = char.id

            # 根据类型和上下文计算段间延迟
            delay = _compute_delay(
                seg_data.get("type", "narration"),
                segments[-1].type if segments else "narration",
                speaker_name,
                segments[-1].speaker_name if segments else "",
            )

            segment = Segment(
                index=i + 1,
                text=seg_data.get("text", ""),
                type=seg_data.get("type", "narration"),
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                emotion=seg_data.get("emotion", ""),
                emotion_prompt=seg_data.get("emotion_prompt", ""),
                delay=delay,
            )
            segments.append(segment)

        chapter.segments = segments
        chapter.status = "structured"

    project.touch()

    return {
        "status": "ok",
        "chapter": chapter.to_dict(),
        "new_characters": [c.to_dict() for c in new_characters],
        "segment_count": len(chapter.segments),
    }


@router.post("/projects/{project_id}/chapters/batch-structure")
async def batch_structure(project_id: str, data: dict = None):
    """批量 LLM 结构化"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    indices = (data or {}).get("chapter_indices", [])
    if not indices:
        # 默认处理所有 raw 状态的章节
        indices = [c.index for c in project.chapters if c.status == "raw"]

    results = []
    for idx in indices:
        chapter = None
        for c in project.chapters:
            if c.index == idx:
                chapter = c
                break
        if not chapter or not chapter.raw_text.strip():
            continue

        existing_chars = [
            {"name": c.name, "aliases": c.aliases, "gender": c.gender, "age": c.age, "role": c.role}
            for c in project.characters
        ]

        try:
            result = await LLMManager.structure_chapter(chapter.raw_text, existing_chars)

            # 处理角色和 segments（同上逻辑）
            new_characters = []
            if "characters" in result:
                for char_data in result["characters"]:
                    char = Character.from_dict({
                        "name": char_data.get("name", ""),
                        "aliases": char_data.get("aliases", []),
                        "gender": char_data.get("gender", ""),
                        "age": char_data.get("age", ""),
                        "personality": char_data.get("personality", ""),
                        "role": char_data.get("role", ""),
                        "voice_description": char_data.get("voice_description", ""),
                    })
                    if not char.voice.prompt and char.voice_description:
                        char.voice.prompt = char.voice_description
                    new_characters.append(char)

            project.merge_characters(new_characters)

            if "segments" in result:
                segments = []
                for i, seg_data in enumerate(result["segments"]):
                    speaker_name = seg_data.get("speaker", "")
                    speaker_id = None
                    if speaker_name:
                        char = project.find_character_by_name(speaker_name)
                        if char:
                            speaker_id = char.id

                    delay = _compute_delay(
                        seg_data.get("type", "narration"),
                        segments[-1].type if segments else "narration",
                        speaker_name,
                        segments[-1].speaker_name if segments else "",
                    )

                    segments.append(Segment(
                        index=i + 1,
                        text=seg_data.get("text", ""),
                        type=seg_data.get("type", "narration"),
                        speaker_id=speaker_id,
                        speaker_name=speaker_name,
                        emotion=seg_data.get("emotion", ""),
                        emotion_prompt=seg_data.get("emotion_prompt", ""),
                        delay=delay,
                    ))

                chapter.segments = segments
                chapter.status = "structured"

            results.append({"chapter_index": idx, "status": "ok"})
        except Exception as e:
            results.append({"chapter_index": idx, "status": "error", "error": str(e)})

        # 避免请求过快
        await asyncio.sleep(1)

    project.touch()

    return {"results": results}
