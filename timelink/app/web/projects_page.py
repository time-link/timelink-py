import enum
from typing import List, Optional
from pydantic import BaseModel, Field, create_model
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


async def projects_info(
    webapp: TimelinkWebApp, request: Request, user: UserSchema
) -> c.Page:
    if user is not None:
        user_projects: List[UserProjectSchema] = user.projects
    else:
        user_projects = []

    ProjectEnumDynamic = enum.Enum(
        "ProjectEnum", [(p.project_name, p.project_name.lower()) for p in user_projects]
    )

    SelectFormDynamic = create_model(
        "SelectFormDynamic",
        project_name=(ProjectEnumDynamic, Field(title="Select project")),
    )
    # selectList: List[str] = enum.Enum('selectEnum', [name for name in user_projects])
    post_url = request.url_for("project_select")
    current_project = user.current_project_name
    if current_project is None:
        current_project = "None"
    if user is None:
        user_name = "guest"
    else:
        user_name = user.name
        if user_name == "":
            user_name = user.email.split("@")[0]
    return await home_page(
        c.Page(
            components=[
                c.Heading(level=6, text=f"{user_name}; current project: {current_project}"),
                c.Table(
                    data=user_projects,
                    data_model=UserProjectSchema,
                    no_data_message="No projects found. Associate users with projects in the admin page.",
                ),
                c.Div(
                    components=[
                        c.ModelForm(
                            model=SelectFormDynamic,
                            display_mode="page",
                            submit_url=str(post_url),
                            class_name="text-align: left"
                        )
                    ],
                    class_name='text-align: left'
                ),
            ]
        ),
        request=request,
        title="Project list",
        user=user,
    )
