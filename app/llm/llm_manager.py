"""LLM 管理器 —— 工厂模式创建适配器"""

from typing import Optional

from .base import LLMAdapter
from .openai_adapter import OpenAIAdapter
from .tongyi_adapter import TongyiAdapter
from .zhipu_adapter import ZhipuAdapter
from app.utils.config import config as global_config


# 结构化处理的系统 Prompt
STRUCTURING_SYSTEM_PROMPT = """你是一位有声书制作的结构化专家。请分析以下小说章节，完成三项任务并以 JSON 格式输出。

## 任务

### 1. 角色识别
列出本章出现的所有说话角色。每个角色包含：
- name: 角色姓名
- aliases: 角色的别名/称呼列表（小说中可能用不同方式称呼）
- gender: 性别（男/女/未知）
- age: 年龄估计描述（如"约30岁"、"中年"、"少年"）
- personality: 性格特征描述
- role: 角色定位（主角/配角/反派/路人等）
- voice_description: 音色描述，用于 TTS 语音合成（如"低沉威严的中年男声，语速沉稳"）

### 2. 文本分段
将原文拆分为独立片段，每段按以下规则分类：
- **narration（旁白）**：叙述性文字、环境描写、心理描写、动作描写
- **dialogue（对话）**：任何角色说出的对话文本（包括直接引号和间接引语）

注意：
- 每个 segment 应该是一个完整的语义单元，不要太碎
- 对话应包含完整的句子，不要只截取半句
- 旁白段落适度拆分，通常一个自然段落为一个 segment

### 3. 情感标注
为每个片段标注朗读时的情感语气：
- emotion: 情感分类（平静/愤怒/悲伤/喜悦/惊讶/恐惧/紧张/温柔/严肃/疑惑/嘲讽/兴奋/无奈）
- emotion_prompt: 用自然语言描述朗读时应有的语气、语速和情感

**旁白（narration）的特殊要求：**
- 旁白的 emotion_prompt **必须**包含"语速平缓"或"语速平稳"的描述
- 旁白整体风格应沉稳、清晰，即使是描写紧张场景也不应语速过快
- 示例："语速平缓，低沉叙述，氛围压抑" / "语速平稳，清晰沉稳，略带紧张"

**对话（dialogue）的要求：**
- 对话的 emotion_prompt 根据角色性格和情感自行判断，可以有丰富的语速变化
- 示例："高昂急促，充满怒火" / "低声细语，温柔缓慢"

## 输出格式

请严格按以下 JSON 格式输出，不要输出任何其他内容：

```json
{
  "characters": [
    {
      "name": "张三",
      "aliases": ["三哥", "张兄"],
      "gender": "男",
      "age": "约35岁",
      "personality": "豪爽直率，重情重义",
      "role": "主角",
      "voice_description": "中年男性，低沉有力，音色磁性"
    }
  ],
  "segments": [
    {
      "type": "narration",
      "text": "夜色如墨，星光暗淡。",
      "speaker": "",
      "emotion": "阴沉",
      "emotion_prompt": "语速平缓，低沉叙述，氛围压抑"
    },
    {
      "type": "dialogue",
      "text": "你终于来了。",
      "speaker": "张三",
      "emotion": "期待",
      "emotion_prompt": "低沉有力，带着期待和一丝紧张"
    }
  ]
}
```

**重要规则：**
- narration 类型的 speaker 字段为空字符串 ""
- dialogue 类型的 speaker 必须是 characters 列表中出现的角色名
- emotion_prompt 要具体，包含语气、语速、情感细节
- 如果文本特别长，可以分批返回，但要保证 JSON 完整
"""


class LLMManager:
    """LLM 管理器"""

    _adapter: Optional[LLMAdapter] = None
    _provider: str = ""

    @classmethod
    def get_adapter(cls) -> LLMAdapter:
        """获取当前配置的 LLM 适配器（惰性创建）"""
        provider = global_config.get("llm", "provider", default="openai")
        config = global_config.get_llm_config()

        if cls._adapter is None or cls._provider != provider:
            if provider == "openai":
                cls._adapter = OpenAIAdapter(config)
            elif provider == "tongyi":
                cls._adapter = TongyiAdapter(config)
            elif provider == "zhipu":
                cls._adapter = ZhipuAdapter(config)
            else:
                raise ValueError(f"未知的 LLM 提供者: {provider}")
            cls._provider = provider

        return cls._adapter

    @classmethod
    async def structure_chapter(cls, chapter_text: str, existing_characters: list[dict]) -> dict:
        """
        对章节进行结构化处理

        Args:
            chapter_text: 章节原始文本
            existing_characters: 项目中已有的角色列表（用于上下文）

        Returns:
            {"characters": [...], "segments": [...]}
        """
        adapter = cls.get_adapter()

        # 构建消息
        char_context = ""
        if existing_characters:
            char_context = "\n## 已出现的角色\n"
            for c in existing_characters:
                char_context += f"- {c['name']}（{c.get('gender','')}，{c.get('age','')}，{c.get('role','')}）\n"

        user_message = f"{char_context}\n## 待处理的章节文本\n\n{chapter_text}"

        messages = [
            {"role": "system", "content": STRUCTURING_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        response = await adapter.chat(messages, temperature=0.3, max_tokens=8192)

        # 解析 JSON
        import json
        import re

        # 提取 JSON 块（处理可能的 markdown 代码块包裹）
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = response.strip()

        try:
            result = json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复常见问题
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"LLM 返回的 JSON 解析失败: {e}\n原始响应: {response[:500]}...")

        return result

    @classmethod
    async def test_connection(cls) -> dict:
        """测试 LLM 连接"""
        adapter = cls.get_adapter()
        messages = [
            {"role": "user", "content": "请回复 'OK'。"},
        ]
        response = await adapter.chat(messages, max_tokens=10)
        return {"status": "ok", "model": adapter.model, "response": response.strip()}
