from __future__ import annotations as _annotations

from typing import Annotated, Literal, TypeAlias
import asyncio

from fastapi import APIRouter, Depends, Request

from fastui import AnyComponent, FastUI
from fastui import components as c
from fastui.auth import AuthRedirect, GitHubAuthProvider
from fastui.events import AuthEvent, GoToEvent, PageEvent

# from httpx import AsyncClient
from pydantic import BaseModel, EmailStr, Field, SecretStr

from timelink.app.schemas.user import UserSchema
from timelink.app.dependencies import get_current_user, get_github_auth
from timelink.app.web.home_page import home_page


router = APIRouter(tags=["fastui"], responses={404: {"description": "Not found"}})


# --------------------------


UserDep = Annotated[UserSchema, Depends(get_current_user)]

ACCESS_TOKEN_EXPIRE_MINUTES = 5 * 24 * 60  # 5 days

LoginKind: TypeAlias = Literal["password", "github"]


@router.get("/login/{kind}", response_model=FastUI, response_model_exclude_none=True)
def auth_login(
    kind: LoginKind,
    request: Request,
    user: UserSchema = None,
    # user: Annotated[UserSchema, Depends(get_current_user)]
) -> list[AnyComponent]:
    if user is not None:
        # already logged in
        raise AuthRedirect("/")

    return home_page(
        c.LinkList(
            links=[
                c.Link(
                    components=[c.Text(text="Password Login")],
                    on_click=PageEvent(
                        name="tab",
                        push_path="/auth/login/password",
                        context={"kind": "password"},
                    ),
                    active="/auth/login/password",
                ),
                c.Link(
                    components=[c.Text(text="GitHub Login")],
                    on_click=PageEvent(
                        name="tab",
                        push_path="/auth/login/github",
                        context={"kind": "github"},
                    ),
                    active="/auth/login/github",
                ),
            ],
            mode="tabs",
            class_name="+ mb-4",
        ),
        c.ServerLoad(
            path="/auth/login/content/{kind}",
            load_trigger=PageEvent(name="tab"),
            components=auth_login_content(kind),
        ),
        request=request,
        title="Authentication",
        user=user,
    )


@router.get(
    "/login/content/{kind}", response_model=FastUI, response_model_exclude_none=True
)
def auth_login_content(kind: LoginKind) -> list[AnyComponent]:
    match kind:
        case "password":
            return [
                c.Heading(text="Timelink login", level=5, class_name="text-center"),
                c.ModelForm(
                    model=LoginForm,
                    submit_url="/fastui/auth/login",
                    display_mode="page",
                ),
            ]
        case "github":
            return [
                c.Heading(text="GitHub Login", level=3),
                c.Paragraph(text="Demo of GitHub authentication."),
                c.Paragraph(
                    text="(Credentials are stored in the browser via a JWT only)"
                ),
                c.Button(
                    text="Login with GitHub",
                    on_click=GoToEvent(url="/auth/login/github/gen"),
                ),
            ]
        case _:
            raise ValueError(f"Invalid kind {kind!r}")


class LoginForm(BaseModel):
    email: EmailStr = Field(
        title="Email Address",
        description="Enter a valid email address",
        json_schema_extra={"autocomplete": "email"},
    )
    password: SecretStr = Field(
        title="Password",
        description="Enter your password",
        json_schema_extra={"autocomplete": "current-password"},
    )


@router.get("/profile", response_model=FastUI, response_model_exclude_none=True)
async def profile(
    request: Request, user: Annotated[UserSchema, Depends(get_current_user)]
) -> list[AnyComponent]:
    return home_page(
        c.Paragraph(text=f'You are logged in as "{user.email}".'),
        c.Button(text="Logout", on_click=PageEvent(name="submit-form")),
        c.Heading(text="User Data:", level=3),
        c.Code(language="json", text=user.model_dump_json(indent=2)),
        c.Form(
            submit_url="/fastui/auth/logout",
            form_fields=[
                c.FormFieldInput(
                    name="test", title="", initial="data", html_type="hidden"
                )
            ],
            footer=[],
            submit_trigger=PageEvent(name="submit-form"),
        ),
        title="Authentication",
        request=request,
        user=user,
    )


@router.post("/logout", response_model=FastUI, response_model_exclude_none=True)
async def logout_form_post() -> list[AnyComponent]:
    return [c.FireEvent(event=AuthEvent(token=False, url="/auth/login/password"))]


@router.get(
    "/login/github/gen", response_model=FastUI, response_model_exclude_none=True
)
async def auth_github_gen(
    github_auth: Annotated[GitHubAuthProvider, Depends(get_github_auth)]
) -> list[AnyComponent]:
    auth_url = await github_auth.authorization_url()
    return [c.FireEvent(event=GoToEvent(url=auth_url))]


@router.get(
    "/login/github/redirect", response_model=FastUI, response_model_exclude_none=True
)
async def github_redirect(
    code: str,
    state: str | None,
    github_auth: Annotated[GitHubAuthProvider, Depends(get_github_auth)],
) -> list[AnyComponent]:
    exchange = await github_auth.exchange_code(code, state)
    user_info, emails = await asyncio.gather(
        github_auth.get_github_user(exchange),
        github_auth.get_github_user_emails(exchange),
    )
    user = UserSchema(
        email=next((e.email for e in emails if e.primary and e.verified), None),
        extra={
            "github_user_info": user_info.model_dump(),
            "github_emails": [e.model_dump() for e in emails],
        },
    )
    token = user.encode_token()
    return [c.FireEvent(event=AuthEvent(token=token, url="/auth/profile"))]
