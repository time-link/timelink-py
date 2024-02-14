# flake8: noqa: B008

"""
FastAPI app for timelink

Following the tutorial at https://fastapi.tiangolo.com/tutorial/

Finished: Query Parameters and String Validations
* https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#__tabbed_7_3

... jumped a few chapters
Currently doing with: https://fastapi.tiangolo.com/tutorial/sql-databases/
* √ test TimelinkDatabase create database and mappings
* √ currently at tests/test_api_models_db.py refactoring to use TimelinkDatabase

Next:
* √ implement import from file and from url kleio_server with token
* implement do translations
* implement get sources
* implement clear translations
* get dirs
* √ implement interface in fastApi for kleio_server

To Run
    source .venv/bin/activate; cd timelink/api/; uvicorn main:app --reload

To Test
* http://127.0.0.1:8000/docs
* http://127.0.0.1:8000/redoc

To debug
* https://fastapi.tiangolo.com/tutorial/debugging/
"""
import os
from enum import Enum
from typing import List, Annotated, Optional
from datetime import date
from jinja2 import PackageLoader, Environment

import uvicorn  # pylint: disable=import-error
from fastapi import FastAPI
from fastapi import Request
from fastapi import Query
from fastapi import Depends  # pylint: disable=unused-import, import-error
from fastapi.templating import Jinja2Templates

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy.orm import Session  # pylint: disable=import-error
from timelink.api import models, crud, schemas
from timelink.api.database import TimelinkDatabase
from timelink.api.database import is_valid_postgres_db_name

from timelink.kleio.importer import import_from_xml
from timelink.kleio import kleio_server as kserver
from timelink.kleio.kleio_server import KleioServer
from timelink.kleio.schemas import KleioFile, ApiPermissions, TokenInfo
from timelink.kleio import api_permissions_normal, token_info_normal

from timelink.api.schemas import ImportStats
from timelink.api.schemas import EntityAttrRelSchema
from timelink import version


# Dependency to get a connection to the database
def get_db(
    project_name: Optional[str] = None,
    project_home: Optional[str] = None,
    sqlite_dir: str = None,
    db_name: str = None,
    db_type: str = None,
    db_url: str = None,
    db_user: str = None,
    db_pwd: str = None,
    db_path: str = None,
    kleio_server=None,
    kleio_home=None,
    kleio_image=None,
    kleio_version=None,
    kleio_token=None,
    kleio_update=None,
    postgres_image=None,
    postgres_version=None,
    stop_duplicates=True,
    **connect_args
):
    """Get a connection to the database

    Uses timelink.api.database.TimelinkDatabase to get a connection to the database."""

    project_name = project_name
    project_home = project_home
    db_type = db_type
    db_name = db_name
    sqlite_dir = sqlite_dir
    kleio_image = kleio_image
    kleio_version = kleio_version
    postgres_image = postgres_image
    postgres_version = postgres_version

    if project_home is None:
        project_home = KleioServer.find_local_kleio_home()
    if project_name is None:
        project_name = os.path.basename(os.path.dirname(os.getcwd()))
    if db_type is None:
        db_type = "sqlite"
    if db_name is None:
        db_name = project_name.replace("-", "_").replace(" ", "_")
    if kleio_image is None:
        kleio_image = "timelinkserver/kleio-server"
    if kleio_version is None:
        kleio_version = "latest"
    if sqlite_dir is None:
        sqlite_dir = os.path.join(project_home, "database", "sqlite")
        # create the directory if it does not exist
        if not os.path.exists(sqlite_dir):
            os.makedirs(sqlite_dir)
    if postgres_image is None:
        postgres_image = "postgres"
    if postgres_version is None:
        postgres_version = "latest"

    if db_type == "postgres":
        if not is_valid_postgres_db_name(db_name):
            raise ValueError(f"Invalid database name: {db_name}")

    database = TimelinkDatabase(
        dba_name=db_name,
        db_type=db_type,
        db_url=db_url,
        db_user=db_user,
        db_pwd=db_pwd,
        db_path=db_path,
        kleio_server=kleio_server,
        kleio_home=kleio_home,
        kleio_image=kleio_image,
        kleio_version=kleio_version,
        kleio_token=kleio_token,
        kleio_update=kleio_update,
        postgres_image=postgres_image,
        postgres_version=postgres_version,
        stop_duplicates=stop_duplicates,
        **connect_args
        )
    db = database.session()
    try:
        yield db
    finally:
        db.close()


# dependency to get a connection to the kleio server
def get_kleio_server():
    """Get a connection to the kleio server

    Uses timelink.kleio.kleio_server.KleioServer to get a connection to the kleio server.
    """

    kleio_home = kserver.find_kleio_home()
    if not kserver.is_kserver_running():
        kserver.start_kleio_server(kleio_home=kleio_home)
    token = kserver.get_kserver_token()
    url = kserver.kleio_get_url()
    return KleioServer(url=url, token=token)

app = FastAPI()

app.mount("/static", StaticFiles(packages=[('timelink','api/static')]), name="static")

# this is how to load the templates from inside the package
env = Environment(loader=PackageLoader("timelink", "api/templates"))
templates = Jinja2Templates(env=env)


@app.get("/")
async def root(request: Request):
    """Timelink API end point. Check URL/docs for API documentation."""
    return {"message": f"Welcome to Timelink API {version}", "host": request.headers["host"]}

@app.get("/web/show/{id}", response_class=HTMLResponse)
async def read_item(request: Request, id: str):
    current_dir = os.getcwd()
    return templates.TemplateResponse(
        request=request, name="item.html", context={"id": id}
    )

@app.post("/search/", response_model=List[schemas.SearchResults])
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
    q: list[str]
    | None = Query(
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
    nlines: int
    | None = Query(
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
