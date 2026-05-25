# 🎙 AI声工坊

有声书制作工具 —— TXT导入 → LLM结构化 → TTS语音合成 → 合并导出

## 功能

- **TXT 解析** — 自动分章，支持常规章节标题匹配
- **LLM 结构化** — 角色识别 + 对话/旁白分类 + 情感标注 + 段间延迟
- **语音合成** — 可控克隆 + 声音设计双模式
- **角色管理** — 上传音色、声音设计、试听预览
- **语速控制** — 播放速度滑块 + 合并时时间拉伸
- **文字替换** — TTS 合成前自动替换文本
- **段间停顿** — 根据上下文自动插入静音间隔

## 环境要求

| 依赖 | 说明 |
|------|------|
| Python 3.10+ | 运行框架 |
| LLM 服务 | OpenAI / 通义千问 / 智谱 GLM |
| TTS 引擎 | VoxCPM2（本地）或兼容 HTTP 接口 |

## 快速开始

### 1. 克隆项目

```bash
git clone git@github.com:newton9253/audiobook.git
cd audiobook
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动 LLM 和 TTS 服务

**LLM**：确保 OpenAI 兼容接口可用（可用 localhost:3000 或在线 API）

**TTS**：启动 VoxCPM2 服务（默认 localhost:5022）或配置其他 TTS HTTP 接口

### 4. 启动应用

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

或 Windows 上直接双击 `start.bat`

浏览器打开 http://localhost:8080

### 5. 配置

在页面中点击 **⚙ 配置** 设置 LLM 和 TTS 的 API 地址及密钥。

配置保存在 `~/.ai_audiobook/config.json`

## 技术架构

```
main.py (FastAPI)          —— 路由入口
├── app/api/               —— REST API 端点
├── app/core/              —— 数据模型 (Project → Chapter → Segment)
├── app/llm/               —— LLM 适配器 (OpenAI/通义/智谱)
├── app/tts/               —— TTS 适配器 (VoxCPM2/HTTP/Mock)
├── app/parsers/           —— TXT 解析器
├── app/utils/             —— 配置管理 & 常量
└── static/                —— 前端 (原生 HTML/CSS/JS)
```

数据流：`TXT → 分章 → LLM结构化 → Segment列表 → TTS合成 → WAV合并`

## 项目结构

```
audiobook/
├── main.py            # 入口
├── requirements.txt   # Python 依赖
├── start.bat          # Windows 一键启动
├── app/               # 后端代码
├── static/            # 前端资源
└── test_novel.txt     # 测试用小说
```

## License

MIT
