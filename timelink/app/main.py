# flake8: noqa: B008

"""
FastAPI app for timelink

To Run

    * source .venv/bin/activate; cd timelink/app; uvicorn main:app --reload

To Test

* http://127.0.0.1:8008/docs
* http://127.0.0.1:8008/redoc

To debug

* https://fastapi.tiangolo.com/tutorial/debugging/

"""
# Standard library imports
import logging
import os
from datetime import date, timedelta
from enum import Enum
from typing import Annotated, List, Optional

# Third-party imports
from fastapi import FastAPI, Depends, Request, status
from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm

# import realted with starlette admin app
from starlette_admin import EnumField

from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.views import Link


from pydantic import BaseModel, Field

from jinja2 import Environment, PackageLoader
from sqlalchemy.orm import Session
import uvicorn

# Local application/library specific imports
from timelink import version
from timelink.api import crud, models, schemas
from timelink.api.database import TimelinkDatabase, TimelinkDatabaseSchema, is_valid_postgres_db_name
from timelink.api.schemas import EntityAttrRelSchema, ImportStats

from timelink.app.backend.settings import Settings
from timelink.app.backend.timelink_webapp import TimelinkWebApp
from timelink.app.dependencies import get_current_user, get_kleio_server
from timelink.app.models.user import User, UserProperty
from timelink.app.models.user_database import UserDatabase
from timelink.app.models.project import Project, ProjectAccess, AccessLevel
from timelink.kleio import (
    KleioServer,
    api_permissions_normal,  # todo: should have kleio prefixed name
    kleio_server as kserver,
    token_info_normal,  # todo: chenge to kleio prefixed names
)
from timelink.kleio.importer import import_from_xml
from timelink.kleio.kleio_server import KleioServer
from timelink.kleio.schemas import ApiPermissions, KleioFile, TokenInfo
from timelink.app.dependencies import get_current_active_user, get_db
from timelink.app.schemas.user import UserSchema


# Get Pydantic-based settings defined in timelink.app.backend.settings
settings = Settings(timelink_admin_pwd="admin")


app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# create TimelinkWebApp instance
if hasattr(app.state, "webapp") is False or app.state.webapp is None:
    initial_users = []
    possible_timelink_home = KleioServer.find_local_kleio_home()
    # End deprecated

    # need to add timelink_home to settings and to webapp
    webapp = TimelinkWebApp(
        app_name=settings.timelink_app_name,
        timelink_home=possible_timelink_home,
        users_db_name=settings.timelink_users_db_name,
        users_db_type=settings.timelink_users_db_type,
        initial_users=initial_users,

    )

    app.state.webapp = webapp
    app.state.status = "Initialized"

# startlette admin app see https://jowilf.github.io/starlette-admin/
admin = Admin(webapp.users_db.engine,
              title="Timelink Admin",
              )
admin.add_view(ModelView(User))
admin.add_view(ModelView(UserProperty, label="User Properties"))
admin.add_view(ModelView(Project))
admin.add_view(ModelView(ProjectAccess, label="Project Access"))
admin.add_view(Link(label="Timelink web", icon="fa fa-link", url="/"))

admin.mount_to(app)

app.mount("/static", StaticFiles(packages=[("timelink")]), name="static")

# this is how to load the templates from inside the package
env = Environment(loader=PackageLoader("timelink", "app/templates"))
templates = Jinja2Templates(env=env)


@app.get("/test_token", response_model=UserSchema)
async def test_token(
    current_user: Annotated[UserSchema, Depends(get_current_active_user)],
):
    return current_user


@app.get("/web/show/{id}", response_class=HTMLResponse)
async def show_item(request: Request, id: str):
    # problem here is that I need the current project
    return templates.TemplateResponse(
        request=request, name="item.html", context={"id": id}
    )


@app.post("/web/search/", response_model=List[schemas.SearchResults])
async def search(search_request: schemas.SearchRequest):
    """Search for items in the database.

    Args:
        search_request: SearchRequest object

    Returns:
        Search results
    """
    result1 = schemas.SearchResults(
        id="jrc",
        the_class="person",
        description="Joaquim Carvalho: " + repr(search_request),
        start_date=date(1958, 5, 24),
        end_date=date(2023, 1, 4),
    )
    result2 = schemas.SearchResults(
        id="mag",
        the_class="person",
        description="Magda Carvalho: " + repr(search_request),
        start_date=date(1960, 1, 1),
        end_date=date(2023, 1, 4),
    )
    if search_request.q == "jrc":
        return [result1]
    if search_request.q == "mag":
        return [result2]
    if search_request.q == "both":
        return [result1, result2]
    return []


@app.post("/syspar/", response_model=models.SysParSchema)
async def set_syspar(
    syspar: models.SysParSchema, db: Annotated[TimelinkDatabaseSchema, Depends(get_db)]
):
    """Set system parameters

    Args:
        syspar: SysPar object

    Returns:
        SysPar object
    """
    return crud.set_syspar(db, syspar)


@app.get("/syspar/", response_model=list[models.SysParSchema])
async def get_syspars(
    db: Annotated[TimelinkDatabaseSchema, Depends(get_db)], # change to get_db
    q: list[str] | None = Query(
        default=None,
        title="Name of system parameter",
        description="Multiple values allowed," "if empty return all",
    ),
):
    """Get system parameters

    Args:
        q: query string, multiple values allowed, if empty return all

    """

    return crud.get_syspar(db, q)


@app.post("/syslog", response_model=models.SysLogSchema)
async def set_syslog(syslog: models.SysLogCreateSchema,
                     db: Annotated[TimelinkDatabaseSchema, Depends(get_db)]):
    """Set a system log entry"""
    return crud.set_syslog(db, syslog)


@app.get("/syslog", response_model=list[models.SysLogSchema])
async def get_syslog(
    db: Annotated[TimelinkDatabaseSchema, Depends(get_db)],
    nlines: int | None = Query(
        default=10,
        title="Get last N lines of log",
        description="If number of lines not specified" "return last 10",
    ),
):
    """Get log lines

    Args:
        nlines: number of most recent lines to return

    TODO: add fitler since (minutes, seconds)
    """
    result = crud.get_syslog(db, nlines)
    return result


@app.get("/sources/import-file/{file_path:path}", response_model=ImportStats)
async def import_file(file_path: str,
                      db: Annotated[TimelinkDatabaseSchema, Depends(get_db)]):
    """Import kleio data from xml file"""
    result = import_from_xml(file_path, db, {"return_stats": True, "mode": "TL"})
    response = ImportStats(**result)

    return response


@app.get("/get/{id}", response_model=EntityAttrRelSchema)
async def get(id: str, db: Annotated[TimelinkDatabaseSchema, Depends(get_db)]):
    """Get entity by id

    TODO: needs to check if id is real entity or normal id
    """
    return crud.get(db, id)


# Kleio server interface
@app.get("/kleio/is-running", response_model=bool)
async def is_kleio_server_running():
    """Check if kleio server is running"""
    return kserver.is_kserver_running()


# invalidate user
@app.get("/kleio/invalidate-user/{user}", response_model=str)
async def invalidate_user(
    user: str, kserver: KleioServer = Depends(get_kleio_server)
):  # noqa: B008
    """Invalidate a user"""
    return kserver.invalidate_user(user)


# generate token for user
@app.get("/kleio/generate-normal-token/{user}", response_model=str)
async def generate_norma_token(
    user: str, kserver: KleioServer = Depends(get_kleio_server)  # noqa: B008
):
    """Generate a token for a user"""
    return kserver.generate_token(user, token_info_normal)


# get translation status
@app.get("/kleio/translation-status/{path:path}", response_model=list[KleioFile])
async def translation_status(
    path: str,
    recurse: str,
    status: str,
    kserver: KleioServer = Depends(get_kleio_server),  # noqa: B008
):
    """Get translations from kleio server

    Args:
        path (str): path to the directory in sources.
        recurse (str): if "yes" recurse in subdirectories.
        status (str): filter by translation status:
                        V = valid translations;
                        T = need translation (source more recent than translation);
                        E = translation with errors;
                        W = translation with warnings;
                        P = translation being processed;
                        Q = file queued for translation;
                        * = all
    """
    if status == "*":
        status = None
    return kserver.get_translations(path, recurse, status)


# translate
@app.get("/kleio/translate/{path:path}", response_model=str)
async def translate(
    path: str,
    recurse: str,
    spawn: str,
    kserver: KleioServer = Depends(get_kleio_server),  # noqa: B008
):
    """Translate sources from kleio server

    Args:
        path (str): path to the file or directory in sources.
        recurse (str): if "yes" recurse in subdirectories.
        spawn (str): if "yes" spawn a translation process for each file.
    """
    return kserver.translate(path, recurse, spawn)


# Web zone

# web prefix uses templates for htmx and tailwind
@app.get("/web", include_in_schema=False)
async def root(request: Request,
               user: UserSchema = Depends(get_current_user)
               )-> HTMLResponse :
    """Timelink API end point. Check URL/docs for API documentation."""
    webapp: TimelinkWebApp = request.app.state.webapp
    context = {
        "welcome_message": "Welcome to Timelink API and Webapp",
        "webapp_info": webapp.get_info(),
        "projects": webapp.projects,
        "user": user,
    }
    return templates.TemplateResponse(
        request=request, name="index.html", context=context
    )


@app.get("/web/templates/{template_name}", include_in_schema=False)
async def get_template(request: Request, template_name: str) -> HTMLResponse:
    """Get a template"""
    webapp: TimelinkWebApp = request.app.state.webapp
    context = {
        "welcome_message": "Welcome to Timelink API and Webapp",
        "webapp_info": webapp.get_info(),
        "webapp_projects": webapp.projects,
    }

    return templates.TemplateResponse(
        request=request, name=template_name, context=context
    )


# Must come last as it matches all paths
@app.get("/{path:path}", include_in_schema=False)
async def html_landing(request: Request, path: str) -> HTMLResponse:
    """Catch all for HTML requests

    Currently we use the path to get the template name.
    """
    webapp: TimelinkWebApp = request.app.state.webapp
    context = {
        "welcome_message": "Welcome to Timelink API and Webapp",
        "webapp_info": webapp.get_info(),
        "webapp_projects": webapp.projects,
    }
    if path == '':
        path = "index.html"
    return templates.TemplateResponse(
        request=request, name=path, context=context
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)
    app.state.status = "Running"
