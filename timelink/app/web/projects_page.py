from typing import List, Optional
from pydantic import BaseModel
from fastapi import Request
from fastui import components as c

from timelink.app.backend.timelink_webapp import TimelinkWebApp
from ..schemas import ProjectSchema
from ..services.auth import FiefUserInfo
from .home_page import home_page


class ProjectInfoSchema(BaseModel):
    """Classe to hold the relevant project info for display."""
    id: int
    name: str
    description: Optional[str] = None
    databaseURL: Optional[str] = None
    kleioServerURL: Optional[str] = None


async def projects_info(webapp: TimelinkWebApp, request: Request, user: FiefUserInfo) -> c.Page:

    user_fields = user.get("fields", {})
    user_projects = [proj.strip() for proj in user_fields.get("user_projects", '').split(",")]
    projects: List[ProjectSchema] = [proj for proj in webapp.projects if proj.name in user_projects]

    return await home_page(
        c.Page(
            components=[
                c.Table(data=projects, data_model=ProjectSchema, no_data_message="No projects found"),
            ]
        ),
        request=request,
        title="Project list",
        user=user
    )
