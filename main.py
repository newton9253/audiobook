"""AI声工坊 - 有声书生成软件 主入口"""

import os
import sys
import time
import logging

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.constants import API_PREFIX, OUTPUT_DIR
from app.api.project_api import router as project_router
from app.api.chapter_api import router as chapter_router
from app.api.character_api import router as character_router
from app.api.llm_api import router as llm_router
from app.api.tts_api import router as tts_router
from app.api.voice_library_api import router as voice_library_router
from app.api.config_api import router as config_router

# ---- 日志配置 ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AI声工坊")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(
    title="AI声工坊",
    description="有声书制作工具 —— TXT导入 → LLM结构化 → TTS合成",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 请求日志中间件 ----
class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        status = response.status_code
        method = request.method
        path = request.url.path
        # 用颜色标记状态码
        if status < 300:
            icon = "✓"
        elif status < 400:
            icon = "→"
        else:
            icon = "✗"
        logger.info(f"{icon} {method:6s} {status}  {duration:6.0f}ms  {path}")
        return response


app.add_middleware(RequestLogMiddleware)

# 注册 API 路由
app.include_router(project_router, prefix=API_PREFIX)
app.include_router(chapter_router, prefix=API_PREFIX)
app.include_router(character_router, prefix=API_PREFIX)
app.include_router(llm_router, prefix=API_PREFIX)
app.include_router(tts_router, prefix=API_PREFIX)
app.include_router(voice_library_router, prefix=API_PREFIX)
app.include_router(config_router, prefix=API_PREFIX)

# 挂载静态文件
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 挂载输出目录（音频文件访问）—— 动态路由，支持项目自定义目录
@app.get("/output/{project_id}/{filename:path}")
async def serve_project_file(project_id: str, filename: str):
    """根据项目输出目录服务音频文件"""
    from app.api.store import store
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404)
    file_path = os.path.join(project.output_dir, filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404)


@app.get("/api/v1/browse")
async def browse_directory(path: str = Query(default="")):
    """浏览本地文件夹（供前端文件夹选择器使用）"""
    if not path:
        # 返回驱动器列表（Windows）
        import string
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append({"name": drive, "path": drive})
        return {"path": "", "entries": drives}

    # 规范化路径
    path = os.path.normpath(path)
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="路径不存在或不是文件夹")

    parent = os.path.dirname(path)
    if parent == path:
        parent = ""  # 根目录

    entries = []
    try:
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            if os.path.isdir(full) and not entry.startswith('.') and not entry.startswith('$'):
                entries.append({"name": entry, "path": full})
    except PermissionError:
        pass

    return {"path": path, "parent": parent, "entries": entries}


@app.get("/")
async def root():
    """重定向到前端页面"""
    from fastapi.responses import FileResponse
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)


@app.get("/api/v1/pick-folder")
async def pick_folder():
    """打开原生 Windows 文件夹选择对话框，返回所选路径"""
    import subprocess

    ps_script = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        '$d=New-Object System.Windows.Forms.FolderBrowserDialog; '
        '$d.Description="选择项目输出文件夹"; '
        '$d.ShowNewFolderButton=$true; '
        'if($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){$d.SelectedPath}'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=60,
        )
        path = result.stdout.strip()
        if path and os.path.isdir(path):
            return {"path": path}
        return {"path": None, "cancelled": True}
    except subprocess.TimeoutExpired:
        return {"path": None, "cancelled": True}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "AI声工坊"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
