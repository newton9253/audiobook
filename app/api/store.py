"""项目内存存储 —— 简单的字典存储"""

from typing import Dict, Optional
from app.core.project import Project


class ProjectStore:
    """内存中存储所有打开的项目"""

    _instance: Optional["ProjectStore"] = None

    def __new__(cls) -> "ProjectStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._projects: Dict[str, Project] = {}
            cls._instance._current_id: Optional[str] = None
        return cls._instance

    @property
    def projects(self) -> Dict[str, Project]:
        return self._projects

    def add(self, project: Project) -> str:
        self._projects[project.metadata.id] = project
        return project.metadata.id

    def get(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def remove(self, project_id: str):
        self._projects.pop(project_id, None)
        if self._current_id == project_id:
            self._current_id = None

    def list_all(self) -> list[dict]:
        from app.core.serializer import export_project_summary
        return [export_project_summary(p) for p in self._projects.values()]


store = ProjectStore()
