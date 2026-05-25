"""常量定义"""

import os

# ---- 路径常量 ----
APP_DIR = os.path.expanduser("~/.ai_audiobook")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
VOICE_LIBRARY_PATH = os.path.join(APP_DIR, "voice_library.json")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
PROJECTS_DIR = os.path.join(APP_DIR, "projects")

# ---- 章节匹配正则 ----
CHAPTER_PATTERNS = [
    # 优先级1：第X章/第X回
    (r"^第[零一二三四五六七八九十百千万\d]+[章节回卷集篇部](?:\s+.+)?$", 1),
    # 优先级2：Chapter X
    (r"^Chapter\s+\d+.*$", 2),
    # 优先级3：卷X/部X
    (r"^[卷部集][零一二三四五六七八九十百千万\d]+.*$", 3),
    # 优先级4：分隔符
    (r"^\s*[-=*]{3,}\s*$", 4),
    # 优先级5：特殊标识
    (r"^(序言|前言|楔子|尾声|后记|番外|引子|终章)", 5),
]

# ---- LLM 提供者 ----
LLM_PROVIDERS = ["openai", "tongyi", "zhipu"]

# ---- TTS 提供者 ----
TTS_PROVIDERS = ["voxcpm2", "http"]

# ---- 情感分类 ----
EMOTIONS = [
    "平静", "愤怒", "悲伤", "喜悦", "惊讶",
    "恐惧", "紧张", "温柔", "严肃", "疑惑",
    "轻蔑", "兴奋", "无奈", "嘲讽", "焦急",
]

# ---- API 前缀 ----
API_PREFIX = "/api/v1"
