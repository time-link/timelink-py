from typing import Annotated
from fastapi import Request, Header
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException
from jose import JWTError
from timelink.app.models.user_database import UserDatabase
from timelink.app.schemas import UserSchema


from timelink.app.services.auth import fief, auth, FiefUserInfo, SESSION_COOKIE_NAME
from timelink.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_fastui_token(authorization: Annotated[str, Header()] = ''):
    try:
        token = authorization.split(' ', 1)[1]
    except IndexError:
        return None
    return token


async def get_current_user(
    request: Request, user: Annotated[FiefUserInfo, Depends(auth.current_user(optional=True))]
):
    try:
        users_db: UserDatabase = request.app.state.webapp.users_db
        if user is None:
            return None
        else:
            user_schema = users_db.cache.get(user["email"])
            if user_schema is None:
                with users_db.session() as session:
                    cookie = request.cookies.get(SESSION_COOKIE_NAME)
                    token_access = await fief.validate_access_token(cookie)
                    permissions = token_access.get("permissions", [])
                    db_user = users_db.on_board_user(user, permissions=permissions, session=session)
                    user_schema = UserSchema.model_validate(db_user)
                    user_schema.properties = users_db.get_user_properties(db_user.id, session=session)
                    user_schema.projects = users_db.get_user_projects(db_user.id, session=session)
                    users_db.cache[user["email"]] = user_schema
            return user_schema

    except JWTError as jexception:
        raise jexception
        # raise credentials_exception

    return user_schema


async def get_current_active_user(
    request: Request, current_user: Annotated[UserSchema, Depends(get_current_user)]
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Dependency to get a connection to the database
def get_user_db(request: Request):
    """Get the User database request"""

    webapp = request.app.webapp
    return webapp.users_db


# dependency to get a connection to the kleio server
def get_kleio_server(request: Request):
    """Get a connection to the kleio server

    Uses timelink.kleio.kleio_server.KleioServer to get a connection to the kleio server.
    """
    webapp = request.app.webapp

    return webapp.kleio_server


def get_db(request: Request):
    """Get the database request"""
    webapp = request.app.webapp
    user = Annotated[User, Depends(get_current_active_user)]
    # Todo: Determine the user's project
    # project = webapp.projects[user.name]
    # project_db = project.db
    return webapp.get_current_project_db(user)


def get_github_auth(request: Request):
    """Get the github auth request"""
    webapp = request.app.webapp
    return webapp
