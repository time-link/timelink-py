# flake8: noqa: B008

"""
FastAPI app for timelink

Next

* Authentication

    * startup Fief docker container, try to add first user
    * add first admin user to database

To Run

    * source .venv/bin/activate; cd timelink/app; uvicorn main:app --reload

To Test

* http://127.0.0.1:8008/docs
* http://127.0.0.1:8008/redoc

To debug

* https://fastapi.tiangolo.com/tutorial/debugging/

"""
# Standard library imports
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

from fastui import FastUI, AnyComponent, prebuilt_html, components as c
from fastui.components.display import DisplayMode, DisplayLookup
from fastui.events import GoToEvent, BackEvent

# import realted with starlette admin app
from starlette_admin import EnumField

from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.views import Link


# imports related to authentication with fief
from fastapi.security import OAuth2AuthorizationCodeBearer
from fief_client import FiefAccessTokenInfo, FiefAsync
from fief_client.integrations.fastapi import FiefAuth

from pydantic import BaseModel, Field

from jinja2 import Environment, PackageLoader
from sqlalchemy.orm import Session
import uvicorn

# Local application/library specific imports
from timelink import version
from timelink.api import crud, models, schemas
from timelink.api.database import TimelinkDatabase, is_valid_postgres_db_name
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
from timelink.app.services.auth import auth

from timelink.app.web import router as fastui_router

# Get Pydantic-based settings defined in timelink.app.backend.settings
settings = Settings(timelink_admin_pwd="admin")

# Move to settings?
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
app.include_router(fastui_router, prefix="/fastui")


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

admin = Admin(webapp.users_db.engine,
              title="timelink admin",
              )
admin.add_view(ModelView(User))
admin.add_view(ModelView(UserProperty))
admin.add_view(ModelView(ProjectAccess))
admin.add_view(ModelView(Project))
admin.add_view(Link(label="Timelink web", icon="fa fa-link", url="/"))

admin.mount_to(app)

app.mount("/static", StaticFiles(packages=[("timelink", "app/static")]), name="static")

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
    syspar: models.SysParSchema, db: Annotated[Session, Depends(get_db)]
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
    q: list[str] | None = Query(
        default=None,
        title="Name of system parameter",
        description="Multiple values allowed," "if empty return all",
    ),
    db: Session = Depends(get_db),
):
    """Get system parameters

    Args:
        q: query string, multiple values allowed, if empty return all

    """

    return crud.get_syspar(db, q)


@app.post("/syslog", response_model=models.SysLogSchema)
async def set_syslog(syslog: models.SysLogCreateSchema, db: Session = Depends(get_db)):
    """Set a system log entry"""
    return crud.set_syslog(db, syslog)


@app.get("/syslog", response_model=list[models.SysLogSchema])
async def get_syslog(
    nlines: int | None = Query(
        default=10,
        title="Get last N lines of log",
        description="If number of lines not specified" "return last 10",
    ),
    db: Session = Depends(get_db),
):
    """Get log lines

    Args:
        nlines: number of most recent lines to return

    TODO: add fitler since (minutes, seconds)
    """
    result = crud.get_syslog(db, nlines)
    return result


@app.get("/sources/import-file/{file_path:path}", response_model=ImportStats)
async def import_file(file_path: str, db: Session = Depends(get_db)):
    """Import kleio data from xml file"""
    result = import_from_xml(file_path, db, {"return_stats": True, "mode": "TL"})
    response = ImportStats(**result)

    return response


@app.get("/get/{id}", response_model=EntityAttrRelSchema)
async def get(id: str, db: Session = Depends(get_db)):
    """Get entity by id"""
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
    return kserver.translation_status(path, recurse, status)


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
@app.get("/web")
async def root(request: Request,
               user: UserSchema = Depends(get_current_user)
               ):
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


@app.get("/web/templates/{template_name}")
async def get_template(request: Request, template_name: str):
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


# This is the main entry point for the fastUI interface
# Must come last as it matches all paths
@app.get("/{path:path}")
async def html_landing() -> HTMLResponse:
    """Simple HTML page which serves the React app, comes last as it matches all paths."""
    return HTMLResponse(prebuilt_html(title="Timelink", api_root_url="/fastui"))


# Tutorial
class ModelName(str, Enum):
    """Enum for model names"""

    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]


@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    """Example of path parameters with enum validation"""
    if model_name == ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}

    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}


@app.get("/files/{file_path:path}")
async def read_file(file_path: str):
    """Example of path parameters"""
    return {"file_path": file_path}


@app.get("/items/")
async def read_item(skip: int = 0, limit: int = 10):
    """Example of query parameters"""
    return fake_items_db[skip : skip + limit]


@app.get("/items2/{item_id}")
async def read_item2(item_id: str, q: str | None = None):
    """Example of query parameters with optional
    http://127.0.0.1:8000/items2/foo?q=somequery
    http://127.0.0.1:8000/items2/foo
    """
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}


# Sandbox
# testing specifying the database in the path
@app.get("/{dbname}/id/{id}", response_model=dict)
async def get_id(eid: str, dbname: str, db: Session = Depends(get_db)):  # noqa: B008
    """get entity with id from database

    This will pass the name of the database in the path
    to the get_db() function
    """
    result = {
        "database": dbname,
        "id": f"info for id {eid}",
        "url": repr(db.get_bind().url),
    }
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)
    app.state.status = "Running"
