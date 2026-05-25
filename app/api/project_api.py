"""项目管理 API —— 完整实现"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from app.core.project import Project, ProjectMetadata, ProjectSettings
from app.parsers.txt_parser import parse_txt
from app.core.serializer import (
    serialize_project,
    deserialize_project,
    export_project_summary,
)
from app.utils.constants import PROJECTS_DIR
from .store import store

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.get("")
async def list_projects():
    """列出所有已打开项目"""
    return {"projects": store.list_all()}


@router.post("")
async def create_project(file: UploadFile = File(...), output_dir: str = Form(default="")):
    """新建项目：上传 TXT 文件，自动分章"""
    # 保存上传的文件
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    filename = file.filename or "untitled.txt"
    base_name = os.path.splitext(filename)[0]
    upload_path = os.path.join(PROJECTS_DIR, filename)

    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    # 解析 TXT
    try:
        title, author, chapters = parse_txt(upload_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"TXT 解析失败: {str(e)}")

    # 创建项目
    project = Project(
        metadata=ProjectMetadata(
            title=title or base_name,
            author=author,
            source_path=upload_path,
            output_dir=output_dir if output_dir else "",
        ),
        chapters=chapters,
        settings=ProjectSettings(),
    )

    # 自动保存 .awb
    awb_path = os.path.join(PROJECTS_DIR, f"{base_name}.awb")
    serialize_project(project, awb_path)

    store.add(project)

    return {
        "project": export_project_summary(project),
        "chapter_count": len(chapters),
    }


@router.post("/open")
async def open_project(file: UploadFile = File(...)):
    """打开 .awb 项目文件"""
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    filename = file.filename or "project.awb"
    upload_path = os.path.join(PROJECTS_DIR, filename)

    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        project = deserialize_project(upload_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f".awb 文件解析失败: {str(e)}")

    store.add(project)

    return {
        "project": export_project_summary(project),
        "chapter_count": len(project.chapters),
        "character_count": len(project.characters),
    }


@router.get("/{project_id}")
async def get_project(project_id: str):
    """获取项目完整详情"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    return project.to_dict()


@router.put("/{project_id}")
async def update_project(project_id: str, data: dict):
    """更新项目元数据"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    if "title" in data:
        project.metadata.title = data["title"]
    if "author" in data:
        project.metadata.author = data["author"]
    project.touch()

    return {"status": "ok"}


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    store.remove(project_id)
    return {"status": "ok"}


@router.post("/{project_id}/save")
async def save_project(project_id: str):
    """保存项目为 .awb 文件并返回下载"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    os.makedirs(PROJECTS_DIR, exist_ok=True)
    safe_name = project.metadata.title.replace("/", "_").replace("\\", "_")
    awb_path = os.path.join(PROJECTS_DIR, f"{safe_name}.awb")

    serialize_project(project, awb_path)

    # 更新 project_path 记录
    project.metadata.project_path = awb_path

    return FileResponse(
        awb_path,
        media_type="application/json",
        filename=f"{safe_name}.awb",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.awb"'},
    )


@router.get("/{project_id}/export")
async def export_project(project_id: str):
    """导出完整有声书（合并所有章节音频）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")

    # 检查是否有已合成的音频
    output_dir = project.output_dir
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=400, detail="没有已生成的音频文件")

    # 打包为 ZIP
    zip_path = os.path.join(output_dir, f"{project.metadata.title}.zip")
    shutil.make_archive(
        os.path.splitext(zip_path)[0],
        "zip",
        output_dir,
    )

    if os.path.exists(zip_path):
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{project.metadata.title}.zip",
        )

    raise HTTPException(status_code=500, detail="导出失败")


@router.post("/{project_id}/autosave")
async def autosave_project(project_id: str):
    """自动保存项目（静默保存到 projects 目录，不触发下载）"""
    project = store.get(project_id)
    if not project:
        return {"status": "skipped"}

    os.makedirs(PROJECTS_DIR, exist_ok=True)
    safe_name = project.metadata.title.replace("/", "_").replace("\\", "_")
    awb_path = os.path.join(PROJECTS_DIR, f"{safe_name}.awb")

    serialize_project(project, awb_path)

    # 更新 project_path 记录
    project.metadata.project_path = awb_path

    return {"status": "ok", "path": awb_path}


# ========== 文字替换规则 ==========

@router.get("/{project_id}/text-replacements")
async def get_text_replacements(project_id: str):
    """获取文字替换规则列表"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    return {"replacements": project.text_replacements}


@router.put("/{project_id}/text-replacements")
async def save_text_replacements(project_id: str, data: dict):
    """保存文字替换规则（全量覆盖）"""
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目未找到")
    project.text_replacements = data.get("replacements", [])
    project.touch()
    return {"status": "ok", "count": len(project.text_replacements)}
