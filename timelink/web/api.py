"""REST API router for the timelink web app.

Salvaged from the former timelink/app FastAPI stack: kleio server
endpoints, syspar/syslog, entity fetch and file import. Mounted by
``timelink_web.py`` under ``/api``; uses ``app.state.webapp`` (a
``TimelinkAppWrapper``) set up during startup.

The old stack's JWT auth dependencies were stubs (get_current_user
returned None) and were not ported; authentication for these routes
follows the NiceGUI session middleware for now. Treat adding real
token auth here as a roadmap item.
"""
from fastapi import APIRouter, Depends, Query, Request

from timelink.api import crud, models
from timelink.api.schemas import EntityAttrRelSchema, ImportStats
from timelink.kleio.importer import import_from_xml
from timelink.kleio.schemas import KleioFile

router = APIRouter()


def get_webapp(request: Request):
    """The TimelinkAppWrapper set up at startup."""
    return request.app.state.webapp


def get_kleio_server(request: Request):
    webapp = get_webapp(request)
    return webapp.kleio_server


@router.get("/syspar/", response_model=list[models.SysParSchema])
async def get_syspars(
    request: Request,
    q: list[str] | None = Query(
        default=None,
        title="Name of system parameter",
        description="Multiple values allowed, if empty return all",
    ),
):
    """Get system parameters"""
    with get_webapp(request).database.session() as session:
        return crud.get_syspar(session, q)


@router.post("/syspar/", response_model=models.SysParSchema)
async def set_syspar(request: Request, syspar: models.SysParSchema):
    """Set system parameters"""
    with get_webapp(request).database.session() as session:
        return crud.set_syspar(session, syspar)


@router.post("/syslog", response_model=models.SysLogSchema)
async def set_syslog(request: Request, syslog: models.SysLogCreateSchema):
    """Set a system log entry"""
    with get_webapp(request).database.session() as session:
        return crud.set_syslog(session, syslog)


@router.get("/syslog", response_model=list[models.SysLogSchema])
async def get_syslog(
    request: Request,
    nlines: int | None = Query(
        default=10,
        title="Get last N lines of log",
        description="If number of lines not specified return last 10",
    ),
):
    """Get log lines (most recent first)"""
    with get_webapp(request).database.session() as session:
        return crud.get_syslog(session, nlines)


@router.get("/sources/import-file/{file_path:path}", response_model=ImportStats)
async def import_file(request: Request, file_path: str):
    """Import kleio data from an xml file"""
    with get_webapp(request).database.session() as session:
        result = import_from_xml(file_path, session, {"return_stats": True, "mode": "TL"})
    return ImportStats(**result)


@router.get("/get/{id}", response_model=EntityAttrRelSchema)
async def get(request: Request, id: str):
    """Get entity, attributes and relations by id"""
    with get_webapp(request).database.session() as session:
        return crud.get(session, id)


# Kleio server interface


@router.get("/kleio/is-running", response_model=bool)
async def is_kleio_server_running(request: Request):
    """Check if the kleio server is running"""
    return get_kleio_server(request) is not None


@router.get("/kleio/invalidate-user/{user}", response_model=str)
async def invalidate_user(user: str, kserver=Depends(get_kleio_server)):
    """Invalidate a user token"""
    return kserver.invalidate_user(user)


@router.get("/kleio/generate-normal-token/{user}", response_model=str)
async def generate_normal_token(user: str, kserver=Depends(get_kleio_server)):
    """Generate a normal token for a user"""
    from timelink.kleio import token_info_normal

    return kserver.generate_token(user, token_info_normal)


@router.get("/kleio/translation-status/{path:path}", response_model=list[KleioFile])
async def translation_status(
    path: str,
    recurse: str,
    status: str,
    kserver=Depends(get_kleio_server),
):
    """Get translations from kleio server

    Args:
        path: path to the directory in sources.
        recurse: if "yes" recurse in subdirectories.
        status: filter by translation status:
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


@router.get("/kleio/translate/{path:path}", response_model=str)
async def translate(
    path: str,
    recurse: str,
    spawn: str,
    kserver=Depends(get_kleio_server),
):
    """Translate sources in the kleio server

    Args:
        path: path to the file or directory in sources.
        recurse: if "yes" recurse in subdirectories.
        spawn: if "yes" spawn a translation process for each file.
    """
    return kserver.translate(path, recurse, spawn)
