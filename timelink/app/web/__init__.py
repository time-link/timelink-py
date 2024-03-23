# noqa B008
"""
FastAPI routers for the web interface of Timelink.

This is the main switch board of the FastUI web interface.

All the top level routers are defined here, and also
the subrouters, like the /auth router, that handles
the login and logout pages.

To add future pages:

1. Write a new function in a separate file that produces the
   components for the new tab: see :mod:`webapp_info` for
   inspiration.
2. Here import the page and add a new router that calls
   the new function to collect the components and call
   :func:`home_page` to wrap the components in a page.
3. If the new page handles subpaths, like /auth/login,
   it is better to create a new router in the new page
   and include it here, like the /auth router is included.
"""

import uuid

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, Request, Response, Query
from fastapi.responses import RedirectResponse

from fastui import FastUI, AnyComponent, components as c
from fastui.events import GoToEvent

# from timelink.app.backend import settings
from timelink.api.database import TimelinkDatabase
from timelink.app.backend.timelink_webapp import TimelinkWebApp
from timelink.app.models.project import Project, ProjectAccess
from timelink.app.schemas.user import UserSchema
from timelink.app.services.auth import fief, auth, FiefUserInfo
from timelink.app.services.auth import (
    get_memory_userinfo_cache,
    MemoryUserInfoCache,
    SESSION_COOKIE_NAME,
)
from .home_page import home_page
from .webapp_info import webapp_info
from .projects_page import projects_info

# deprecated we dont handle logins anymore
from timelink.app.dependencies import get_current_user

# --------------

router = APIRouter(tags=["fastui"], responses={404: {"description": "Not found"}})

# deprecated we dont handle logins anymore see fiefUserDep
UserDep = Annotated[UserSchema, Depends(get_current_user)]


@router.get("/login", name="login")
async def login(
    request: Request, user: FiefUserInfo = Depends(auth.current_user(optional=False))):  # noqa B008
    """We require the user to be logged in to access this page

    So the Dependency will forward the user to the fief login page
    """
    RedirectResponse(request.url_for("/"))


@router.get("/auth-callback", name="auth_callback")
async def auth_callback(
    request: Request,
    response: Response,
    code: str = Query(...),  # noqa B008
    memory_userinfo_cache: MemoryUserInfoCache = Depends(get_memory_userinfo_cache),  # noqa B008
):
    """Callback for the Fief authentication

    From the fief docs:

    "We implement an /auth-callback route

    This is the route that'll take care of exchanging the
    authorization code with a fresh access token and save it in a cookie.

    Notice that we set its name parameter: this is how we can generate
    its URL automatically with the request.url_for method.
    "

    After the user authenticates in Fief and authorizes the application,
    Fief will redirect the user to this endpoint.

    Here we get the tokens and userinfo from Fief and store the userinfo,
    then we redirect to the main page.
    """
    redirect_uri = request.url_for(
        "auth_callback"
    )  # the arg is the name of the function
    # docs:
    # We generate an access token
    #
    # We finish the OAuth2 flow by exchanging the
    # authorization code with a fresh access token.
    #
    tokens, userinfo = await fief.auth_callback(code, redirect_uri)
    # this redirects to after login
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    response = RedirectResponse(base_url)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        # access token includes permissions and scope
        # these can be accessed with
        # t = await fief.validate_access_token(tokens["access_token"])
        # t["permissions"]
        tokens["access_token"],
        max_age=tokens["expires_in"],
        # docs:
        #
        # Set the cookie as HTTPOnly
        # For such sensitive values, it's strongly recommended
        # to set the cookie as HTTPOnly. It means that it won't
        # be possible to read its value from JavaScript,
        # reducing potential attacks.
        httponly=True,
        # docs:
        #
        # Set the cookie as secure in production
        # For such sensitive values, it's strongly recommended
        # to set the cookie as Secure. It tells the browser to
        # send the cookie only on HTTPS (SSL) connection, reducing
        # the risk of the access token to be stolen by a attacker
        # between the client and the server.
        # However, in a local environment, you usually don't serve your
        # application with SSL. That's why we set it to False in this example.
        # A common approach to handle this is to have an environment variable to
        # control this parameter, so you can disable it in local and enable it in production.
        secure=False,
    )
    # save userinfo in memory cache
    await memory_userinfo_cache.set(uuid.UUID(userinfo["sub"]), userinfo)
    # redirect to the main page
    return response


@router.get("/logout", name="logout")
async def logout(
    request: Request, response: Response, user: UserSchema = Depends(get_current_user)):  # noqa B008
    """Logout the user
    Remove the cookie and redirect to fief logout, then to the main page
    """
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    logout_url = await fief.logout_url(str(base_url))
    response = RedirectResponse(logout_url)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/projects", response_model=FastUI, response_model_exclude_none=True)
async def projects(
    request: Request,
    user: Optional[UserSchema] = Depends(get_current_user),  # noqa B008
) -> list[AnyComponent]:
    webapp: TimelinkWebApp = request.app.state.webapp
    # collect the info from TimelinkWebApp
    return await projects_info(webapp, request=request, user=user)


@router.post("/projects/select", response_model=FastUI, response_model_exclude_none=True)
async def project_select(
    request: Request,
    project_name: Annotated[str, Form()],
    user: UserSchema = Depends(get_current_user),  # noqa B008
):
    webapp: TimelinkWebApp = request.app.state.webapp
    if project_name is not None:
        user.current_project_name = project_name
        users_db = webapp.users_db
        with users_db.session() as session:
            project: Project = users_db.get_project_by_name(project_name, session=session)
        user.current_project = project
        access_level: ProjectAccess = users_db.get_user_project_access(user.id, project.id, session=session)
        if access_level is None:
            raise ValueError(f"User {user.name} has no access to project {project_name}")

        project_db = TimelinkDatabase(project.databaseURL)
        user.current_project_db = project_db

    return [c.FireEvent(event=GoToEvent(url='/projects'))]


@router.get("/info", response_model=FastUI, response_model_exclude_none=True)
async def info(
    request: Request, user: UserSchema = Depends(get_current_user)  # noqa B008
) -> list[AnyComponent]:
    webapp: TimelinkWebApp = (
        request.app.state.webapp
    )  # collect the info from TimelinkWebApp
    return await webapp_info(webapp, request=request, user=user)


@router.get("/explore", response_model=FastUI, response_model_exclude_none=True)
async def explore(
    request: Request, user: UserSchema = Depends(get_current_user)  # noqa B008
) -> list[AnyComponent]:
    markdown = """\
* See list of attributes
* See list of relations
* See list of events
"""
    return await home_page(
        c.Markdown(text=markdown), request=request, title="Explore", user=user
    )


@router.get("/sources", response_model=FastUI, response_model_exclude_none=True)
async def sources(
    request: Request, user: UserSchema = Depends(get_current_user)  # noqa B008
) -> list[AnyComponent]:
    markdown = """\
* View sources
* Translate sources
* Import souces

"""
    return await home_page(
        c.Markdown(text=markdown), request=request, title="Sources", user=user
    )


@router.get("/adm", response_model=FastUI, response_model_exclude_none=True)
async def admin(
    request: Request,
    user: UserSchema = Depends(get_current_user),  # noqa B008
) -> list[AnyComponent]:
    webapp: TimelinkWebApp = request.app.state.webapp
    markdown = f"""\
### Welcome {user.name} to the admin page

Timelink administration consists of:

* Managing [authentication]({webapp.auth_manager}/admin/)
    * Who can login, with what permissions, passwords, etc.
* Managing [application resources]({webapp.app_manager})
    * Projects, associate users with projects with specific permissions.
    * General application settings, logs, etc.

"""
    return await home_page(
        c.Markdown(text=markdown), request=request, title="Admin", user=user
    )


@router.get("/", name="home", response_model=FastUI, response_model_exclude_none=True)
async def home(
    request: Request,
    user: Optional[UserSchema] = Depends(get_current_user),  # noqa B008
) -> list[AnyComponent]:
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

    return await home_page(
        c.Markdown(text=markdown),
        request=request,
        title="Welcome to Timelink",
        user=user,
    )
