"""配置管理 API —— 完整实现"""

from fastapi import APIRouter, HTTPException
from app.utils.config import config
from app.llm.llm_manager import LLMManager
from app.tts.tts_manager import TTSManager

router = APIRouter(prefix="/config", tags=["配置管理"])


@router.get("")
async def get_config():
    """获取全局配置"""
    return config.get_all()


@router.put("")
async def update_config(data: dict):
    """更新全局配置"""
    if "llm" in data:
        config.update_section("llm", data["llm"])
    if "tts" in data:
        config.update_section("tts", data["tts"])
    if "general" in data:
        config.update_section("general", data["general"])
    return {"status": "ok"}


@router.post("/test-llm")
async def test_llm():
    """测试 LLM 连接"""
    try:
        result = await LLMManager.test_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 连接失败: {str(e)}")


@router.post("/test-tts")
async def test_tts():
    """测试 TTS 连接"""
    try:
        result = await TTSManager.test_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 连接失败: {str(e)}")
