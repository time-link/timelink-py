""" Authentication services """
import os
import uuid
from typing import Optional
from typing_extensions import Dict
from fastapi import Request, Response, HTTPException, status
from fastapi.security import APIKeyCookie

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

    See https://fief-dev.github.io/fief-python/fief_client/integrations/fastapi.html#FiefAuth.__init__

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
            headers={"Location": str(auth_url)}
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
