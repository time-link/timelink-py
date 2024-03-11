from typing import Optional
from fastapi import Request
from fastui import components as c
from pydantic import BaseModel, Field

from timelink.app.backend.timelink_webapp import TimelinkWebApp
from timelink.app.schemas.user import UserSchema
from .home_page import home_page


# class to hold the Webapp info
class WebAppInfo(BaseModel):
    """Classe to holf the WebApp info."""

    info_label: str = Field(title="Label")
    info_value: Optional[str] = Field(title="Value", default="<NA>")


async def webapp_info(
    webapp: TimelinkWebApp,
    request: Request,
    user: UserSchema,
    token_access: dict = False,
) -> c.Page:
    info_list = [
        WebAppInfo(info_label=label, info_value=value)
        for (label, value) in webapp.get_info().items()
    ]

    return await home_page(
        c.Page(components=[c.Table(data=info_list)]),
        request=request,
        title="Server info",
        user=user,
    )
