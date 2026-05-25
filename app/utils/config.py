"""全局配置管理"""

import json
import os
from typing import Any, Optional

from .constants import CONFIG_PATH, APP_DIR


DEFAULT_CONFIG = {
    "llm": {
        "provider": "openai",
        "openai": {
            "base_url": "http://localhost:3000/api/v1/chat/completions",
            "api_key": "",
            "model": "gpt-4o",
        },
        "tongyi": {
            "api_key": "",
            "model": "qwen-plus",
        },
        "zhipu": {
            "api_key": "",
            "model": "glm-4",
        },
    },
    "tts": {
        "provider": "voxcpm2",
        "voxcpm2": {
            "base_url": "http://localhost:5022",
        },
        "http": {
            "base_url": "",
            "api_key": "",
        },
    },
    "general": {
        "output_dir": "",
        "language": "zh-CN",
    },
}


class Config:
    """全局配置单例"""

    _instance: Optional["Config"] = None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._load()
        return cls._instance

    def _load(self):
        os.makedirs(APP_DIR, exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = DEFAULT_CONFIG.copy()
            self._save()

    def _save(self):
        os.makedirs(APP_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> dict:
        return self._data

    def get(self, *keys: str, default: Any = None) -> Any:
        """按路径获取配置，如 config.get('llm', 'openai', 'base_url')"""
        value = self._data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys: str, value: Any):
        """按路径设置配置，如 config.set('llm', 'provider', 'zhipu')"""
        target = self._data
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self._save()

    def update_section(self, section: str, data: dict):
        """替换整个配置节"""
        if section in self._data:
            self._data[section] = data
        self._save()

    def get_llm_config(self) -> dict:
        """获取当前 LLM 提供者的配置"""
        provider = self.get("llm", "provider", default="openai")
        return self.get("llm", provider, default={})

    def get_tts_config(self) -> dict:
        """获取当前 TTS 提供者的配置"""
        provider = self.get("tts", "provider", default="voxcpm2")
        return self.get("tts", provider, default={})


# 全局配置单例
config = Config()
