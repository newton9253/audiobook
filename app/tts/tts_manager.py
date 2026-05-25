"""TTS 管理器"""

import random
from typing import Optional, AsyncGenerator
import asyncio

from .base import TTSAdapter
from .voxcpm2_adapter import VoxCPM2Adapter
from .http_adapter import HttpTTSAdapter
from app.utils.config import config as global_config

# 随机风格微调词库（与 tts_api.py 保持一致）
_RANDOM_STYLE_MODIFIERS = [
    "语气坚定", "语气柔和", "语气平淡", "语气生动",
    "声音明亮", "声音沉稳", "声音清亮", "声音浑厚",
    "自然流畅", "略微低沉", "略微高昂", "吐字清晰",
    "节奏分明", "收放自如",
]


class TTSManager:
    """TTS 管理器"""

    _adapter: Optional[TTSAdapter] = None
    _provider: str = ""

    @classmethod
    def get_adapter(cls) -> TTSAdapter:
        """获取当前配置的 TTS 适配器"""
        provider = global_config.get("tts", "provider", default="voxcpm2")
        tts_config = global_config.get_tts_config()

        if cls._adapter is None or cls._provider != provider:
            if provider == "voxcpm2":
                cls._adapter = VoxCPM2Adapter(
                    base_url=tts_config.get("base_url", "http://localhost:5022")
                )
            elif provider == "http":
                cls._adapter = HttpTTSAdapter(
                    base_url=tts_config.get("base_url", ""),
                    api_key=tts_config.get("api_key", ""),
                )
            else:
                raise ValueError(f"未知的 TTS 提供者: {provider}")
            cls._provider = provider

        return cls._adapter

    @classmethod
    async def synthesize(
        cls, text: str, prompt: str = "",
        reference_audio: Optional[bytes] = None,
    ) -> dict:
        """单次合成"""
        adapter = cls.get_adapter()
        return await adapter.synthesize(text, prompt, reference_audio)

    @classmethod
    async def voice_design(cls, text: str, description: str) -> dict:
        """声音设计"""
        adapter = cls.get_adapter()
        return await adapter.voice_design(text, description)

    @classmethod
    async def test_connection(cls) -> dict:
        """测试 TTS 连接"""
        adapter = cls.get_adapter()
        ok = await adapter.test_connection()
        if ok:
            return {"status": "ok", "provider": cls._provider}
        else:
            raise RuntimeError(f"{cls._provider} 连接失败")

    @classmethod
    async def synthesize_chapter_segments(
        cls, segments: list, narrator_prompt: str, chars_map: dict,
        output_dir: str, project_id: str,
        narrator_ref_audio_paths: list = None,
        text_replacements: list = None,
    ) -> AsyncGenerator[dict, None]:
        """
        逐段合成章节

        Args:
            narrator_ref_audio_paths: 旁白参考音频候选列表（依次尝试）
            text_replacements: 文字替换规则列表 [{from, to}, ...]

        Yields:
            {"segment_index": int, "status": "ok"|"skip"|"error", "audio_path": str|None}
        """
        import os
        import base64

        adapter = cls.get_adapter()
        os.makedirs(output_dir, exist_ok=True)
        narrator_ref_paths = narrator_ref_audio_paths or []
        repl_rules = text_replacements or []

        for idx, segment in enumerate(segments):
            # ---- 跳过已有音频 ----
            if segment.audio_path:
                # 验证文件存在
                audio_path_abs = os.path.join(output_dir, os.path.basename(segment.audio_path))
                if os.path.isfile(audio_path_abs):
                    yield {
                        "segment_index": idx,
                        "status": "skip",
                        "audio_path": segment.audio_path,
                    }
                    continue

            try:
                # ---- 加载参考音频 ----
                reference_audio = None

                if segment.type == "narration":
                    # 旁白：优先 chars_map 中自定义"旁白"角色 → narrator 参考音频
                    narration_char = None
                    for c in chars_map.values():
                        if c.name == "旁白":
                            narration_char = c
                            break

                    candidate_paths = []
                    if narration_char:
                        candidate_paths.extend([
                            narration_char.voice.reference_audio,
                            narration_char.voice.sample_audio,
                        ])
                    candidate_paths.extend(narrator_ref_paths)

                    for ref_path in candidate_paths:
                        if ref_path and os.path.isfile(ref_path):
                            try:
                                with open(ref_path, "rb") as f:
                                    reference_audio = f.read()
                                break
                            except Exception:
                                continue

                elif segment.type == "dialogue":
                    char = chars_map.get(segment.speaker_id)
                    if char:
                        for attr in ("reference_audio", "sample_audio"):
                            ref_path = getattr(char.voice, attr, None)
                            if ref_path and os.path.isfile(ref_path):
                                try:
                                    with open(ref_path, "rb") as f:
                                        reference_audio = f.read()
                                    break
                                except Exception:
                                    continue

                # ---- 确定 prompt ----
                if segment.type == "narration":
                    base_prompt = narrator_prompt or "专业播音员，沉稳大气"
                    emotion_prompt = segment.emotion_prompt or segment.emotion or ""

                    if reference_audio:
                        # 可控克隆模式: text + audio + prompt
                        prompt = emotion_prompt if emotion_prompt else base_prompt
                    else:
                        # 声音设计模式
                        parts = [base_prompt]
                        if emotion_prompt:
                            parts.append(emotion_prompt)
                        prompt = "，".join(parts)
                else:
                    char = chars_map.get(segment.speaker_id)
                    base_prompt = char.voice.prompt if char else ""
                    emotion_prompt = segment.emotion_prompt or segment.emotion or ""

                    if reference_audio:
                        # 可控克隆模式
                        prompt = emotion_prompt if emotion_prompt else (base_prompt or "自然语速，情感适中")
                    else:
                        # 声音设计模式
                        if base_prompt or emotion_prompt:
                            prompt = f"{base_prompt}，{emotion_prompt}" if base_prompt and emotion_prompt else (base_prompt or emotion_prompt)
                        else:
                            prompt = "专业播音员，沉稳大气"

                # ---- 合成 ----
                text = segment.text
                for rule in repl_rules:
                    if rule.get("from") and rule["from"] != rule.get("to", ""):
                        text = text.replace(rule["from"], rule["to"])

                result = await adapter.synthesize(
                    text=text,
                    prompt=prompt,
                    reference_audio=reference_audio,
                )

                # 保存音频
                audio_filename = f"ch{segment._chapter_idx if hasattr(segment, '_chapter_idx') else 'x'}_seg{idx:04d}.wav"
                audio_path_abs = os.path.join(output_dir, f"seg_{idx:04d}.wav")
                with open(audio_path_abs, "wb") as f:
                    f.write(base64.b64decode(result["audio"]))

                # 更新 segment
                segment.audio_path = f"{project_id}/seg_{idx:04d}.wav"

                yield {
                    "segment_index": idx,
                    "status": "ok",
                    "audio_path": segment.audio_path,
                }

            except Exception as e:
                yield {
                    "segment_index": idx,
                    "status": "error",
                    "error": str(e),
                }

            # 避免过热
            await asyncio.sleep(0.3)
