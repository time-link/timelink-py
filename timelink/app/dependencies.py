from typing import Annotated
from fastapi import Request, Header
from fastapi import Depends
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException
from jose import JWTError, ExpiredSignatureError
from timelink.app.models.user_database import UserDatabase
from timelink.app.schemas.user import UserSchema


from timelink.app.services.auth import decode_token
from timelink.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_fastui_token(authorization: Annotated[str, Header()] = ''):
    try:
        token = authorization.split(' ', 1)[1]
    except IndexError:
        return None
    return token


async def get_current_user(
    request: Request, token: Annotated[str, Depends(get_fastui_token)]
):
    """Get the current user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Token"},
    )
    try:
        users_db: UserDatabase = request.app.state.webapp.users_db
        if token is None:
            # if token is none return guest user
            username = 'guest'
        else:
            try:
                payload = decode_token(token)
                username: str = payload.get("username")
            except ExpiredSignatureError:
                username = 'guest'

        if username is None:
            raise credentials_exception
        with users_db.session() as session:
            user = users_db.get_user_by_name(username, session=session)
            if user is None:
                raise credentials_exception
            user_schema = UserSchema.model_validate(user)

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
