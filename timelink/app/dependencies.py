from typing import Annotated
from fastapi import Request
from fastapi import Depends
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException
from jose import JWTError, jwt
from timelink.app.models.user_database import UserDatabase
from timelink.app.schemas.user import UserSchema


from timelink.app.services.auth import decode_token, TokenData
from timelink.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(request: Request, token: Annotated[str, Depends(oauth2_scheme)]):
    """Get the current user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        users_db: UserDatabase = request.app.state.webapp.users_db
        payload = decode_token(token)
        username: str = payload.get("username")
        if username is None:
            raise credentials_exception
        with users_db.session() as session:
            user = users_db.get_user_by_name(username, session=session)
            if user is None:
                raise credentials_exception
            user_schema = UserSchema.model_validate(user)

    except JWTError:
        raise credentials_exception
    return user_schema


async def get_current_active_user(request: Request,
    current_user: Annotated[User, Depends(get_current_user)]
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
    project = webapp.projects[user.name]
    project_db = project.db
    return webapp.db