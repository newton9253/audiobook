"""角色管理 API —— 完整实现"""

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.core.character import Character
from .store import store

router = APIRouter(tags=["角色管理"])


@router.get("/projects/{project_id}/characters")
async def list_characters(project_id: str):
    """获取角色列表（含旁白）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    chars = [c.to_dict() for c in project.characters]

    # 旁白作为特殊"角色"始终显示在第一位
    narrator = {
        "id": "__narrator__",
        "name": "旁白",
        "aliases": [],
        "gender": project.narrator_gender,
        "age": project.narrator_age,
        "personality": project.narrator_personality,
        "role": project.narrator_role,
        "voice_description": project.narrator.prompt or "专业播音员，沉稳大气，语速适中，声音清晰富有磁性",
        "voice": {
            "mode": project.narrator.mode,
            "prompt": project.narrator.prompt,
            "reference_audio": project.narrator.reference_audio,
            "sample_audio": project.narrator.sample_audio,
        },
        "is_narrator": True,
    }

    return {"characters": [narrator] + chars}


@router.post("/projects/{project_id}/characters")
async def add_character(project_id: str, data: dict):
    """手动添加角色"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    char = Character.from_dict(data)
    project.characters.append(char)
    project.touch()

    return char.to_dict()


@router.put("/projects/{project_id}/characters/{char_id}")
async def update_character(project_id: str, char_id: str, data: dict):
    """更新角色信息（支持旁白）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    # 旁白特殊处理：可更新基本属性 + 声音相关字段
    if char_id == "__narrator__":
        for field in ("gender", "age", "personality", "role"):
            if field in data:
                setattr(project, f"narrator_{field}", data[field])
        if "voice_description" in data:
            project.narrator.prompt = data["voice_description"]
        if "voice" in data:
            voice_data = data["voice"]
            if "mode" in voice_data:
                project.narrator.mode = voice_data["mode"]
            if "prompt" in voice_data:
                project.narrator.prompt = voice_data["prompt"]
            if "reference_audio" in voice_data:
                project.narrator.reference_audio = voice_data["reference_audio"]
            if "sample_audio" in voice_data:
                project.narrator.sample_audio = voice_data["sample_audio"]
        project.touch()
        return {
            "id": "__narrator__",
            "name": "旁白",
            "gender": project.narrator_gender,
            "age": project.narrator_age,
            "personality": project.narrator_personality,
            "role": project.narrator_role,
            "voice_description": project.narrator.prompt,
            "voice": {
                "mode": project.narrator.mode,
                "prompt": project.narrator.prompt,
                "reference_audio": project.narrator.reference_audio,
                "sample_audio": project.narrator.sample_audio,
            },
            "is_narrator": True,
        }

    char = _find_char(project, char_id)

    # 更新基本字段
    for field in ("name", "gender", "age", "personality", "role", "voice_description"):
        if field in data:
            setattr(char, field, data[field])

    if "aliases" in data:
        char.aliases = data["aliases"]

    # 更新声音配置
    if "voice" in data:
        voice_data = data["voice"]
        if "mode" in voice_data:
            char.voice.mode = voice_data["mode"]
        if "prompt" in voice_data:
            char.voice.prompt = voice_data["prompt"]
        if "reference_audio" in voice_data:
            char.voice.reference_audio = voice_data["reference_audio"]
        if "sample_audio" in voice_data:
            char.voice.sample_audio = voice_data["sample_audio"]

    project.touch()
    return char.to_dict()


@router.delete("/projects/{project_id}/characters/{char_id}")
async def delete_character(project_id: str, char_id: str):
    """删除角色"""
    if char_id == "__narrator__":
        raise HTTPException(status_code=400, detail="旁白不可删除")

    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    project.characters = [c for c in project.characters if c.id != char_id]
    project.touch()

    return {"status": "ok"}


@router.post("/projects/{project_id}/characters/{char_id}/voice-design")
async def voice_design(project_id: str, char_id: str, data: dict):
    """声音设计：调用 TTS 生成试听音频（支持旁白）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    # 旁白特殊处理
    if char_id == "__narrator__":
        voice_config = project.narrator
        voice_description = project.narrator.prompt or "专业播音员，沉稳大气"
        # 旁白属性用于构建提示词
        char_attrs = {
            "gender": project.narrator_gender,
            "age": project.narrator_age,
            "personality": project.narrator_personality,
            "role": project.narrator_role,
        }
    else:
        char = _find_char(project, char_id)
        voice_config = char.voice
        voice_description = char.voice_description or ""
        char_attrs = {
            "gender": char.gender,
            "age": char.age,
            "personality": char.personality,
            "role": char.role,
        }

    text = data.get("text", "这是一段用于声音设计的试听文本，用来展示角色的音色特点。")
    prompt = data.get("prompt", voice_config.prompt or voice_description)

    # 拼接角色属性到提示词
    attr_parts = []
    if char_attrs.get("gender"):
        attr_parts.append(char_attrs["gender"])
    if char_attrs.get("age"):
        attr_parts.append(char_attrs["age"])
    if char_attrs.get("personality"):
        attr_parts.append(char_attrs["personality"])
    if char_attrs.get("role"):
        attr_parts.append(char_attrs["role"])

    if attr_parts:
        attr_str = "，".join(attr_parts)
        prompt = f"{attr_str}。{prompt}" if prompt else attr_str

    if not prompt:
        raise HTTPException(status_code=400, detail="请提供声音描述 prompt")

    # 调用 TTS 管理器
    from app.tts.tts_manager import TTSManager

    try:
        result = await TTSManager.voice_design(text, prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 请求失败: {str(e)}")

    # 保存试听音频
    import os
    import base64

    output_dir = project.output_dir
    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, f"voice_design_{char_id}.wav")

    with open(audio_path, "wb") as f:
        f.write(base64.b64decode(result["audio"]))

    # 更新声音配置
    voice_config.prompt = prompt
    voice_config.sample_audio = f"{project_id}/voice_design_{char_id}.wav"
    voice_config.reference_audio = audio_path
    project.touch()

    # 对于角色，同步更新 voice_description
    if char_id != "__narrator__":
        char.voice_description = prompt

    return {
        "status": "ok",
        "audio_path": f"{project_id}/voice_design_{char_id}.wav",
        "sample_rate": result.get("sample_rate", 48000),
    }


@router.post("/projects/{project_id}/characters/{char_id}/upload-audio")
async def upload_character_audio(project_id: str, char_id: str, file: UploadFile = File(...)):
    """上传角色本地参考音色（支持 mp3/wav/flac/ogg/m4a 等）"""
    import os
    import shutil

    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    # 校验扩展名
    ext = os.path.splitext(file.filename or "audio.wav")[1].lower()
    allowed = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus'}
    if not ext:
        ext = '.wav'
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的音频格式: {ext}，支持: {', '.join(sorted(allowed))}")

    # 保存上传文件
    output_dir = project.output_dir
    os.makedirs(output_dir, exist_ok=True)
    upload_path = os.path.join(output_dir, f"upload_{char_id}{ext}")

    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 尝试转换为 WAV（soundfile 原生支持 wav/flac/ogg）
    wav_path = os.path.join(output_dir, f"upload_{char_id}.wav")
    converted = False
    try:
        import soundfile as sf
        data, sr = sf.read(upload_path)
        sf.write(wav_path, data, sr)
        ref_path_abs = wav_path
        ref_path_rel = f"{project_id}/upload_{char_id}.wav"
        converted = True
    except Exception:
        # 转换失败（如 mp3 无 ffmpeg），保留原文件
        ref_path_abs = upload_path
        ref_path_rel = f"{project_id}/upload_{char_id}{ext}"

    # 更新角色或旁白
    if char_id == "__narrator__":
        project.narrator.reference_audio = ref_path_abs
    else:
        char = _find_char(project, char_id)
        char.voice.reference_audio = ref_path_abs

    project.touch()

    return {
        "status": "ok",
        "audio_path": ref_path_rel,
        "filename": file.filename,
        "converted_to_wav": converted,
    }


def _find_char(project, char_id: str) -> Character:
    for c in project.characters:
        if c.id == char_id:
            return c
    raise HTTPException(status_code=404, detail="角色未找到")
