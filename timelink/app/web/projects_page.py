from typing import Optional
from pydantic import BaseModel
from fastapi import Request
from fastui import components as c

from timelink.app.backend.timelink_webapp import TimelinkWebApp
from timelink.app.schemas.user import UserSchema, UserProjectSchema
from .home_page import home_page


class ProjectInfoSchema(BaseModel):
    """Classe to hold the relevant project info for display."""
    id: int
    name: str
    description: Optional[str] = None
    databaseURL: Optional[str] = None
    kleioServerURL: Optional[str] = None


async def projects_info(webapp: TimelinkWebApp, request: Request, user: UserSchema) -> c.Page:

    user_projects = user.projects

    return await home_page(
        c.Page(
            components=[
                c.Table(data=user_projects, data_model=UserProjectSchema, no_data_message="No projects found"),
            ]
        ),
        request=request,
        title="Project list",
        user=user
    )
