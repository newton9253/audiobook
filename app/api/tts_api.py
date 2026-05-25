"""TTS 合成 API —— 完整实现"""

import os
import json
import base64
import random
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from app.tts.tts_manager import TTSManager
from app.core.project import Project
from .store import store

router = APIRouter(tags=["TTS 合成"])

# ---- 随机风格微调词库 ----
# VoxCPM2 无 seed 参数，可控克隆模式下 CFG=3.0 导致结果高度确定性。
# 通过注入随机风格微调词来引入变化，每次重新生成都会产生不同效果。
_RANDOM_STYLE_MODIFIERS = [
    # 语气变化
    "语气坚定", "语气柔和", "语气平淡", "语气生动",
    # 音质微调
    "声音明亮", "声音沉稳", "声音清亮", "声音浑厚",
    # 表现力
    "自然流畅", "略微低沉", "略微高昂", "吐字清晰",
    "节奏分明", "收放自如",
]


@router.post("/projects/{project_id}/chapters/{chapter_idx}/synthesize")
async def synthesize_chapter(project_id: str, chapter_idx: int):
    """TTS 合成单个章节（SSE 流式，跳过已生成条目）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chapter = None
    for c in project.chapters:
        if c.index == chapter_idx:
            chapter = c
            break
    if not chapter:
        raise HTTPException(status_code=404, detail="章节未找到")

    if not chapter.segments:
        raise HTTPException(status_code=400, detail="章节尚未结构化，请先进行 LLM 结构化处理")

    # 构建角色映射
    chars_map = {c.id: c for c in project.characters}

    # 输出目录
    output_dir = project.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # 旁白参考音频候选列表（传给 tts_manager 用于可控克隆）
    narrator_ref_paths = [
        project.narrator.reference_audio,
        project.narrator.sample_audio,
    ]

    async def generate_events():
        results = []
        async for progress in TTSManager.synthesize_chapter_segments(
            segments=chapter.segments,
            narrator_prompt=project.narrator.prompt,
            chars_map=chars_map,
            output_dir=output_dir,
            project_id=project_id,
            narrator_ref_audio_paths=narrator_ref_paths,
            text_replacements=project.text_replacements,
        ):
            results.append(progress)
            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

        # 检查是否全部成功
        errors = [r for r in results if r["status"] == "error"]
        if not errors:
            chapter.status = "synthesized"
        project.touch()

        # 发送完成事件
        yield f"data: {json.dumps({'status': 'done', 'total': len(results), 'errors': len(errors)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_events(), media_type="text/event-stream")


@router.post("/projects/{project_id}/chapters/batch-synthesize")
async def batch_synthesize(project_id: str, data: dict = None):
    """批量 TTS 合成"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    indices = (data or {}).get("chapter_indices", [])
    if not indices:
        # 默认合成所有已结构化但未合成的章节
        indices = [
            c.index for c in project.chapters
            if c.status == "structured" and c.segments
        ]

    all_results = []
    for idx in indices:
        chapter = None
        for c in project.chapters:
            if c.index == idx:
                chapter = c
                break
        if not chapter or not chapter.segments:
            continue

        chars_map = {c.id: c for c in project.characters}
        output_dir = project.output_dir
        os.makedirs(output_dir, exist_ok=True)

        chapter_results = []
        async for progress in TTSManager.synthesize_chapter_segments(
            segments=chapter.segments,
            narrator_prompt=project.narrator.prompt,
            chars_map=chars_map,
            output_dir=output_dir,
            project_id=project_id,
            text_replacements=project.text_replacements,
        ):
            chapter_results.append(progress)

        errors = [r for r in chapter_results if r["status"] == "error"]
        if not errors:
            chapter.status = "synthesized"

        all_results.append({
            "chapter_index": idx,
            "total": len(chapter_results),
            "errors": len(errors),
        })

    project.touch()

    return {"results": all_results}


# ========== 单条 Segment 合成 ==========

@router.post("/projects/{project_id}/chapters/{chapter_idx}/segment/{segment_idx}/synthesize")
async def synthesize_segment(
    project_id: str, chapter_idx: int, segment_idx: int,
):
    """
    单条 segment TTS 合成

    有参考音频时走可控克隆模式，无参考音频时走声音设计模式。
    随机风格微调词注入 prompt 确保每次结果有差异。
    """
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

    if segment_idx < 0 or segment_idx >= len(chapter.segments):
        raise HTTPException(status_code=404, detail="Segment 未找到")

    segment = chapter.segments[segment_idx]

    # ---- 加载参考音频 ----
    reference_audio = None
    voice_prompt = ""
    audio_source = "none"

    if segment.type == "narration":
        # 旁白：优先查找自定义角色（用户手动添加的"旁白"角色），
        # 其次使用系统 narrator 的参考音频
        narration_char = project.find_character_by_name("旁白")
        if narration_char:
            # 优先使用自定义角色的参考音频
            ref_paths = [
                narration_char.voice.reference_audio,
                narration_char.voice.sample_audio,
                project.narrator.reference_audio,
                project.narrator.sample_audio,
            ]
            voice_prompt = narration_char.voice.prompt or narration_char.voice_description or project.narrator.prompt
        else:
            ref_paths = [
                project.narrator.reference_audio,
                project.narrator.sample_audio,
            ]
            voice_prompt = project.narrator.prompt
    else:
        char = project.find_character_by_name(segment.speaker_name)
        if char:
            ref_paths = [
                char.voice.reference_audio,
                char.voice.sample_audio,
            ]
            voice_prompt = char.voice.prompt or char.voice_description or ""
        else:
            ref_paths = [None, None]
            voice_prompt = ""

    # 逐个尝试候选路径
    for i, ref_path in enumerate(ref_paths):
        if ref_path and os.path.isfile(ref_path):
            try:
                with open(ref_path, "rb") as f:
                    reference_audio = f.read()
                # 根据路径内容推断来源（简化标记）
                if "upload_" in str(ref_path):
                    audio_source = "本地上传音色"
                elif "voice_design" in ref_path:
                    audio_source = "角色管理-声音设计"
                elif "sample" in str(ref_path).lower():
                    audio_source = "试听音频"
                else:
                    audio_source = "参考音频"
                break
            except Exception:
                continue

    # ---- 校验音色来源 ----
    # 实时检查：有上传音色用上传，有设计音色用设计，都没有则提示
    if reference_audio is None:
        sources_available = [rp for rp in ref_paths if rp is not None]
        if not sources_available:
            if segment.type == "narration":
                raise HTTPException(status_code=400, detail="旁白缺少参考音色，请先在角色管理中上传音色或进行声音设计")
            else:
                speaker = segment.speaker_name or "未知角色"
                raise HTTPException(status_code=400, detail=f"角色「{speaker}」缺少参考音色，请先上传音色或进行声音设计")

    # ---- 确定合成模式 ----
    # 有参考音频 → 可控克隆；无参考音频 → 声音设计
    if reference_audio:
        actual_mode = "controllable_clone"
    else:
        actual_mode = "voice_design"

    # ---- 情感 prompt ----
    emotion = segment.emotion_prompt or segment.emotion or ""

    # ---- 构建 prompt ----
    if reference_audio:
        # 🔧 可控克隆：text + audio + prompt
        if emotion:
            prompt = emotion
        else:
            prompt = voice_prompt if voice_prompt else "自然语速，情感适中"
    else:
        # 🎨 声音设计：text + prompt
        #    prompt 需完整描述音色 + 风格 + 情感
        prompt_parts = []
        if voice_prompt:
            prompt_parts.append(voice_prompt)
        if emotion:
            prompt_parts.append(emotion)
        prompt = "，".join(prompt_parts) if prompt_parts else "专业播音员，沉稳大气"

    # ---- 随机风格微调 ----
    random_modifier = random.choice(_RANDOM_STYLE_MODIFIERS)
    if random_modifier not in prompt:
        prompt = f"{prompt}，{random_modifier}" if prompt else random_modifier

    # ---- 文字替换 ----
    text = segment.text
    for rule in project.text_replacements:
        if rule.get("from") and rule["from"] != rule.get("to", ""):
            text = text.replace(rule["from"], rule["to"])

    # ---- 调用 TTS ----
    try:
        result = await TTSManager.synthesize(
            text=text,
            prompt=prompt,
            reference_audio=reference_audio,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 合成失败: {str(e)}")

    # ---- 保存音频 ----
    output_dir = project.output_dir
    os.makedirs(output_dir, exist_ok=True)

    audio_filename = f"ch{chapter_idx}_seg{segment_idx}.wav"
    audio_path = os.path.join(output_dir, audio_filename)
    with open(audio_path, "wb") as f:
        f.write(base64.b64decode(result["audio"]))

    # 更新 segment 记录
    segment.audio_path = f"{project_id}/{audio_filename}"
    project.touch()

    return {
        "status": "ok",
        "segment_index": segment_idx,
        "audio_path": segment.audio_path,
        "mode": actual_mode,
        "prompt_used": prompt,
        "random_modifier": random_modifier,
        "audio_source": audio_source,
        "segment_type": segment.type,
        "speaker_name": segment.speaker_name if segment.type == "dialogue" else "旁白",
    }


@router.post("/projects/{project_id}/chapters/{chapter_idx}/merge")
async def merge_chapter_audio(project_id: str, chapter_idx: int, speed: float = 1.0):
    """合并章节所有 segment 音频为一个 WAV 文件，支持变速

    Query params:
        speed: 播放速度倍率，默认 1.0（原速），<1.0 变慢，>1.0 变快
    """
    import soundfile as sf
    import numpy as np

    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chapter = None
    for c in project.chapters:
        if c.index == chapter_idx:
            chapter = c
            break
    if not chapter:
        raise HTTPException(status_code=404, detail="章节未找到")

    if not chapter.segments:
        raise HTTPException(status_code=400, detail="章节无 segments")

    output_dir = project.output_dir

    # 收集所有有音频的 segment（同时记录延迟）
    audio_files = []
    delays = []
    for seg in chapter.segments:
        if seg.audio_path:
            full_path = os.path.join(output_dir, os.path.basename(seg.audio_path))
            if os.path.isfile(full_path):
                audio_files.append(full_path)
                delays.append(getattr(seg, 'delay', 0.4))

    if not audio_files:
        raise HTTPException(status_code=400, detail="没有已生成的音频文件")

    # 读取第一个文件获取采样率等参数
    first_data, sr = sf.read(audio_files[0])
    channels = 1 if first_data.ndim == 1 else first_data.shape[1]
    total_duration = 0.0
    all_chunks = []

    for idx, fpath in enumerate(audio_files):
        data, file_sr = sf.read(fpath)
        # 确保单声道一致
        if data.ndim == 1 and channels > 1:
            data = np.column_stack([data] * channels)
        elif data.ndim > 1 and channels == 1:
            data = data.mean(axis=1)

        if speed != 1.0:
            # 线性插值时间拉伸
            orig_len = data.shape[0]
            new_len = int(orig_len / speed)
            if data.ndim == 1:
                stretched = np.interp(
                    np.linspace(0, orig_len - 1, new_len),
                    np.arange(orig_len),
                    data
                )
            else:
                stretched = np.zeros((new_len, data.shape[1]))
                for ch in range(data.shape[1]):
                    stretched[:, ch] = np.interp(
                        np.linspace(0, orig_len - 1, new_len),
                        np.arange(orig_len),
                        data[:, ch]
                    )
            all_chunks.append(stretched)
            total_duration += new_len / sr
        else:
            all_chunks.append(data)
            total_duration += data.shape[0] / sr

        # 段间插入静音间隔（最后一段后不加）
        if idx < len(audio_files) - 1 and delays[idx] > 0:
            delay_samples = int(delays[idx] * sr)
            if channels == 1:
                silence = np.zeros(delay_samples)
            else:
                silence = np.zeros((delay_samples, channels))
            all_chunks.append(silence)
            total_duration += delays[idx]

    # 拼接
    merged = np.concatenate(all_chunks, axis=0)

    # 写入合并文件
    merge_path = os.path.join(output_dir, f"ch{chapter_idx}_merged.wav")
    sf.write(merge_path, merged, sr)

    return {
        "status": "ok",
        "audio_path": f"{project_id}/ch{chapter_idx}_merged.wav",
        "segment_count": len(audio_files),
        "speed": speed,
        "duration_seconds": round(total_duration, 1),
    }


# ========== 播放速度设置（全局） ==========

@router.get("/projects/{project_id}/playback-speed")
async def get_playback_speed(project_id: str):
    """获取当前播放速度倍率"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    return {"speed": project.playback_speed}


@router.put("/projects/{project_id}/playback-speed")
async def set_playback_speed(project_id: str, data: dict):
    """更新播放速度倍率
    Body: {"speed": 0.7}  范围 0.5 ~ 1.5
    """
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    speed = float(data.get("speed", 1.0))
    speed = max(0.5, min(1.5, speed))  # 限制范围

    project.playback_speed = speed
    project.touch()
    return {"speed": project.playback_speed}
