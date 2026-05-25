"""音色库 API"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.voice_library.voice_library import VoiceLibrary

router = APIRouter(prefix="/voice-library", tags=["音色库"])

library = VoiceLibrary()


@router.get("")
async def list_voices():
    """获取音色库列表"""
    return {"voices": library.list_voices()}


@router.post("/import")
async def import_voices(data: dict):
    """从文件夹导入音色"""
    folder_path = data.get("folder_path", "")
    if not folder_path or not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="无效的文件夹路径")

    try:
        result = library.import_from_folder(folder_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{voice_name}")
async def delete_voice(voice_name: str):
    """删除音色"""
    library.delete_voice(voice_name)
    return {"status": "ok"}


@router.get("/{voice_name}/preview")
async def preview_voice(voice_name: str):
    """试听音色（返回第一个 wav 文件）"""
    voice = library.get_voice(voice_name)
    if not voice:
        raise HTTPException(status_code=404, detail="音色未找到")

    wav_files = voice.get("wav_files", [])
    if not wav_files:
        raise HTTPException(status_code=404, detail="没有可预览的音频文件")

    # 返回第一个 wav 文件
    source_path = voice.get("source_path", "")
    audio_path = os.path.join(source_path, wav_files[0])

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="音频文件不存在")

    return FileResponse(audio_path, media_type="audio/wav")
