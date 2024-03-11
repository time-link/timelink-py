""" Authentication services

"""
import os
import uuid
from typing import Optional
from typing_extensions import Dict
from datetime import timedelta, timezone
from datetime import datetime
from fastapi import Request, Response, HTTPException, status
from fastapi.security import APIKeyCookie

from pydantic import BaseModel, SecretStr
from passlib.context import CryptContext
from jose import jwt  # noqa

from fastui.auth import GitHubAuthProvider
from httpx import AsyncClient

from timelink.app.models.user_database import UserDatabase

# see https://docs.fief.dev/integrate/python/fastapi/#web-application-example
from fief_client import FiefAsync, FiefUserInfo
from fief_client.integrations.fastapi import FiefAuth


class CustomFiefAuth(FiefAuth):
    """We customize the FiefAuth helper to fit our needs

    The base class is implemented with an API scenario in mind.
    Nevertheless, it's designed in a way you can customize its
    behavior when the user is not authenticated or has not the
    required scope.

    That's what'll do with the get_unauthorized_response.

    See: https://fief-dev.github.io/fief-python/fief_client/integrations/fastapi.html#FiefAuth.__init__
    """

    client: FiefAsync

    async def get_unauthorized_response(self,
                                        request: Request,
                                        response: Response):
        redirect_uri = request.url_for("auth_callback")
        auth_url = await self.client.auth_url(redirect_uri, scope=["openid"])
        # Redirect to the Fief auth URL
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": str(auth_url)},
        )


class MemoryUserInfoCache:
    def __init__(self) -> None:
        self.storage: Dict[uuid.UUID, FiefUserInfo] = {}

    async def get(self, user_id: uuid.UUID) -> Optional[FiefUserInfo]:
        return self.storage.get(user_id)

    async def set(self, user_id: uuid.UUID, userinfo: FiefUserInfo) -> None:
        self.storage[user_id] = userinfo


memory_userinfo_cache = MemoryUserInfoCache()


async def get_memory_userinfo_cache() -> MemoryUserInfoCache:
    return memory_userinfo_cache


fief_url = os.getenv("FIEF_URL")
fief_key = os.getenv("FIEF_KEY")
fief_secret = os.getenv("FIEF_SECRET")
fief = FiefAsync(fief_url, fief_key, fief_secret)

SESSION_COOKIE_NAME = "user_session"
scheme = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)
auth = CustomFiefAuth(
    fief,
    scheme,
    get_userinfo_cache=get_memory_userinfo_cache,
)

# ------
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '0d0315f9c2e055d032e2')
# this will give an error when making requests to GitHub, but at least the app will run
GITHUB_CLIENT_SECRET = SecretStr(os.getenv('GITHUB_CLIENT_SECRET', 'dummy-secret'))
# use 'http://localhost:3000/auth/login/github/redirect' in development
GITHUB_REDIRECT = os.getenv('GITHUB_REDIRECT')

SECRET_KEY = "cd02c76b7bb2911c8eda7ca38f2a8b1bd15551515cd6341d92ba8cf4e8925b8d"
ALGORITHM = "HS256"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create an access token

    Args:
        data (dict): The data to encode in the token
        expires_delta (timedelta, optional): The time delta for the token to expire. Defaults to None.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def decode_token(token):
    """Decode a token"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def authenticate_user(users_db: UserDatabase,
                      userid: str,  # work with user name or email
                      password: str):
    with users_db.session() as session:
        if userid:
            user = users_db.get_user_by_name(userid, session=session)
        if not user:
            user = users_db.get_user_by_email(userid, session=session)
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user


async def get_github_auth(request: Request) -> GitHubAuthProvider:
    client: AsyncClient = request.app.state.httpx_client
    return GitHubAuthProvider(
        httpx_client=client,
        github_client_id=GITHUB_CLIENT_ID,
        github_client_secret=GITHUB_CLIENT_SECRET,
        redirect_uri=GITHUB_REDIRECT,
        scopes=['user:email'],
    )
