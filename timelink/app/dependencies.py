from typing import Annotated
from fastapi import Request
from fastapi import Depends
from timelink.app.schemas import UserSchema
from timelink.app.models.user import User


async def get_current_user(request: Request):
    return None


async def get_current_active_user(
    request: Request, current_user: Annotated[UserSchema, Depends(get_current_user)]
):
    return None


# Dependency to get a connection to the database
def get_user_db(request: Request):
    """Get the User database request"""

    webapp = request.app.state.webapp
    return webapp.users_db


# dependency to get a connection to the kleio server
def get_kleio_server(request: Request):
    """Get a connection to the kleio server

    Uses timelink.kleio.kleio_server.KleioServer to get a connection to the kleio server.
    """
    webapp = request.app.state.webapp

    return webapp.kleio_server


def get_db(request: Request):
    """Get the database request"""
    webapp = request.app.state.webapp
    user = Annotated[User, Depends(get_current_active_user)]
    # Todo: Determine the user's project
    # project = webapp.projects[user.name]
    # project_db = project.db
    return webapp.get_current_project_db(user)


def get_github_auth(request: Request):
    """Get the github auth request"""
    webapp = request.app.state.webapp
    return webapp
