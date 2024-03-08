"""FastAPI routers for the web interface of Timelink.

This is the main switch board of the FastUI web interface.

All the top level routers are defined here, and also
the subrouters, like the /auth router, that handles
the login and logout pages.

To add future pages:

1. Write a new function in a separate file that produces the
    components for the new tab: see webapp_info.py for
   inspiration
2. Here import the page and add a new router that calls
    the new function to collect the components and call
    home_page to wrap the components in a page.
3. If the new page handles subpaths, like /auth/login,
   it is better to create a new router in the new page
   and include it here, like the /auth router is included
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastui import FastUI, AnyComponent, components as c

from timelink.app.backend.timelink_webapp import TimelinkWebApp
from timelink.app.dependencies import get_current_user
from timelink.app.schemas.user import UserSchema
from .home_page import home_page
from .webapp_info import webapp_info
from .login_page import router as login_router
from .projects_page import projects_info

router = APIRouter(tags=["fastui"], responses={404: {"description": "Not found"}})
router.include_router(login_router, prefix="/auth")

UserDep = Annotated[UserSchema, Depends(get_current_user)]


@router.get("/projects", response_model=FastUI, response_model_exclude_none=True)
async def projects(request: Request, user: UserDep) -> list[AnyComponent]:
    webapp: TimelinkWebApp = (
        request.app.state.webapp
    )  # collect the info from TimelinkWebApp
    return projects_info(webapp, request=request, user=user)


@router.get("/info", response_model=FastUI, response_model_exclude_none=True)
async def info(request: Request, user: UserDep) -> list[AnyComponent]:
    webapp: TimelinkWebApp = (
        request.app.state.webapp
    )  # collect the info from TimelinkWebApp
    return webapp_info(webapp, request=request, user=user)


@router.get("/explore", response_model=FastUI, response_model_exclude_none=True)
async def explore(request: Request, user: UserDep) -> list[AnyComponent]:
    markdown = """\
* See list of attributes
* See list of relations
* See list of events
"""
    return home_page(c.Markdown(text=markdown), request=request, title="Explore", user=user)


@router.get("/sources", response_model=FastUI, response_model_exclude_none=True)
async def sources(request: Request, user: UserDep) -> list[AnyComponent]:
    markdown = """\
* View sources
* Translate sources
* Import souces

"""
    return home_page(c.Markdown(text=markdown),
                     request=request,
                     title="Sources",
                     user=user)


@router.get("/", response_model=FastUI, response_model_exclude_none=True)
async def home(request: Request, user: UserDep) -> list[AnyComponent]:
    markdown = """\

Timelink provides:

* a notation (kleio) for textual transcription of historical sources,
  capable of capturing complex information about people and their
  relations in any type of historical documents.
* a text processor that extracts information from the
  kleio transcriptions, infers personal attributes and
  relations from agent roles in historical events and generates
   data in formats suitable for database import.
* a database management system capable of processing time
   varying attributes and relations, assist in reconstructing
biographies and networks from fragmentary information.

---

    """
    return home_page(c.Markdown(text=markdown),
                     request=request,
                     title="Welcome to Timelink",
                     user=user)
