from typing import Optional
from fastapi import Request
from fastui import components as c
from pydantic import BaseModel, Field

from timelink.app.backend.timelink_webapp import TimelinkWebApp
from timelink.app.schemas.user import UserSchema, UserPropertySchema
from .home_page import home_page


# class to hold the Webapp info
class WebAppInfo(BaseModel):
    """Classe to holf the WebApp info."""

    info_label: str = Field(title="Label")
    info_value: Optional[str] = Field(title="Value", default="<NA>")


async def webapp_info(
    webapp: TimelinkWebApp, request: Request, user: UserSchema
) -> c.Page:
    info_list = [
        WebAppInfo(info_label=label, info_value=value)
        for (label, value) in webapp.get_info().items()
    ]
    if user is not None:
        user_properties = user.properties
    else:
        user_properties = []

    return await home_page(
        c.Page(components=[
            c.Heading(text="User Info", level=4),
            c.Table(data=user_properties, data_model=UserPropertySchema),
            c.Heading(text="WebApp Info", level=4),
            c.Table(data=info_list)]),
        request=request,
        title="Info",
        user=user,
    )
