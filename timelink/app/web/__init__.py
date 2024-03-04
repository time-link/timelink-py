from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastui import FastUI, AnyComponent, components as c

from timelink.app.backend.timelink_webapp import TimelinkWebApp
from timelink.app.dependencies import get_current_user
from timelink.app.schemas.user import UserSchema
from .home_page import home_page
from .webapp_info import webapp_info
from .login_page import router as login_router

router = APIRouter(tags=["fastui"], responses={404: {"description": "Not found"}})
router.include_router(login_router, prefix="/auth")


@router.get("/info", response_model=FastUI, response_model_exclude_none=True)
async def info(request: Request) -> list[AnyComponent]:
    webapp: TimelinkWebApp = (
        request.app.state.webapp
    )  # collect the info from TimelinkWebApp
    return webapp_info(webapp, request=request)


@router.get("/explore", response_model=FastUI, response_model_exclude_none=True)
async def explore(request: Request, user: Annotated[UserSchema, Depends(get_current_user)]) -> list[AnyComponent]:
    markdown = """\
* See list of attributes
* See list of relations
* See list of events
"""
    return home_page(c.Markdown(text=markdown), request=request, title="Explore", user=user)


@router.get("/sources", response_model=FastUI, response_model_exclude_none=True)
async def sources(request: Request) -> list[AnyComponent]:
    markdown = """\
* View sources
* Translate sources
* Import souces

"""
    return home_page(c.Markdown(text=markdown), request=request, title="Sources")


@router.get("/", response_model=FastUI, response_model_exclude_none=True)
async def home(request: Request) -> list[AnyComponent]:
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
    return home_page(c.Markdown(text=markdown), request=request, title="Welcome to Timelink")
