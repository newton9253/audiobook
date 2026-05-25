""".awb 项目文件序列化/反序列化"""

import json
import os
from pathlib import Path

from .project import Project


def serialize_project(project: Project, filepath: str) -> None:
    """将项目序列化为 .awb JSON 文件"""
    project.touch()
    data = project.to_dict()
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    project.metadata.project_path = filepath


def deserialize_project(filepath: str) -> Project:
    """从 .awb JSON 文件反序列化项目"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    project = Project.from_dict(data)
    project.metadata.project_path = filepath
    return project


def export_project_summary(project: Project) -> dict:
    """导出项目摘要信息（用于列表展示）"""
    return {
        "id": project.metadata.id,
        "title": project.metadata.title,
        "author": project.metadata.author,
        "chapter_count": len(project.chapters),
        "character_count": len(project.characters),
        "project_path": project.metadata.project_path,
        "created_at": project.metadata.created_at,
        "modified_at": project.metadata.modified_at,
    }
