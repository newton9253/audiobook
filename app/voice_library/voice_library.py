"""音色库管理"""

import os
import json
from datetime import datetime
from typing import List, Dict

from app.utils.constants import VOICE_LIBRARY_PATH, APP_DIR


class VoiceLibrary:
    """音色库管理"""

    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(APP_DIR, exist_ok=True)
        if not os.path.exists(VOICE_LIBRARY_PATH):
            with open(VOICE_LIBRARY_PATH, "w", encoding="utf-8") as f:
                json.dump({"voices": []}, f, ensure_ascii=False, indent=2)

    def _load(self) -> dict:
        with open(VOICE_LIBRARY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict):
        with open(VOICE_LIBRARY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_voices(self) -> list:
        """列出所有音色"""
        return self._load().get("voices", [])

    def get_voice(self, name: str) -> dict | None:
        """获取单个音色"""
        data = self._load()
        for v in data.get("voices", []):
            if v["name"] == name:
                return v
        return None

    def import_from_folder(self, folder_path: str) -> dict:
        """
        从文件夹导入音色

        规则：以第一级子文件夹名作为音色名称，递归扫描所有 .wav 文件
        """
        if not os.path.isdir(folder_path):
            raise ValueError("路径不是有效的文件夹")

        data = self._load()
        imported = []

        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if not os.path.isdir(item_path):
                continue

            # 以第一级子文件夹名作为音色名称
            voice_name = item

            # 递归扫描所有 .wav 文件
            wav_files = []
            for root, dirs, files in os.walk(item_path):
                for f in files:
                    if f.lower().endswith(".wav"):
                        rel_path = os.path.relpath(
                            os.path.join(root, f), item_path
                        )
                        wav_files.append(rel_path)

            if not wav_files:
                continue

            # 去重：检查是否已存在同名音色
            existing = [v for v in data["voices"] if v["name"] == voice_name]
            if existing:
                # 合并 wav 文件（去重）
                existing_files = set(existing[0].get("wav_files", []))
                for wf in wav_files:
                    if wf not in existing_files:
                        existing_files.add(wf)
                existing[0]["wav_files"] = sorted(existing_files)
                existing[0]["updated_at"] = datetime.now().isoformat()
                imported.append(voice_name)
            else:
                voice_entry = {
                    "name": voice_name,
                    "source_path": os.path.abspath(item_path),
                    "description": "",
                    "tags": self._extract_tags(voice_name),
                    "wav_files": sorted(wav_files),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                data["voices"].append(voice_entry)
                imported.append(voice_name)

        self._save(data)
        return {"imported_count": len(imported), "names": imported}

    def delete_voice(self, name: str):
        """删除音色"""
        data = self._load()
        data["voices"] = [v for v in data["voices"] if v["name"] != name]
        self._save(data)

    def _extract_tags(self, name: str) -> list:
        """从音色名称中提取标签"""
        tags = []
        # 常见标签词
        tag_keywords = [
            "男", "女", "青年", "中年", "老年", "少年", "儿童",
            "磁性", "温柔", "甜美", "刚毅", "沉稳", "活泼", "威严",
            "主角", "配角", "反派", "旁白", "爆发", "中性", "萝莉",
            "御姐", "大叔", "正太",
        ]
        for kw in tag_keywords:
            if kw in name:
                tags.append(kw)
        return tags
