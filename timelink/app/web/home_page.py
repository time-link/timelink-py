from fastapi import Request

from fastui import AnyComponent, components as c
from fastui.events import GoToEvent

from timelink import version as timelink_version
from timelink.app.schemas.user import UserSchema


def home_page(
    *components: AnyComponent,
    request: Request = None,
    title: str = None,
    user: UserSchema = None,
) -> list[AnyComponent]:
    """Timelink FastUI main page

    This function creates the basic layout of the Timelink FastUI main page.
    It adds specific componenents passed as the first argument to the page.
    Also if uses the user parameter to configure the login/logout link, and
    change the options available in the navbar.

    The current app instance is obtained from the request object

    Args:
        *components (AnyComponent): Components to add to the page
        request (Request, optional): The request. Defaults to None.
        title (str, optional): The title of the page. Defaults to None.
        user (str, optional): The user logged in. Defaults to None.
    """
    if user is None or user.name == "guest":
        user_name = "guest"
        login_logout = c.Link(
            components=[c.Text(text="Login")],
            on_click=GoToEvent(url="/auth/login/password"),
            active="startswith:/auth/login",
        )
    else:
        user_name = user.name
        login_logout = c.Link(
            components=[c.Text(text="Logout")],
            on_click=GoToEvent(url="/auth/profile"),
            active="startswith:/auth/profile",
        )
    if user is None:
        admin_link = None
    else:
        roles = [p.value for p in user.properties if p.name == "timelink.role"]
        if "admin" in roles:
            admin_app = "http://localhost:8000/admin/"
            admin_link = c.Link(
                components=[c.Text(text="Admin")],
                on_click=GoToEvent(url=admin_app)
            )
        else:
            admin_link = None
    end_links = [admin_link, login_logout] if admin_link else [login_logout]
    page = [
        c.PageTitle(text=f"{title}" if title else "Timelink"),
        # align user name to the right
        c.Navbar(
            title=f"Timelink  {user_name}",
            title_event=GoToEvent(url="/"),
            start_links=[
                c.Link(
                    components=[c.Text(text="Explore")],
                    on_click=GoToEvent(url="/explore"),
                    active="startswith:/explore",
                ),
                c.Link(
                    components=[c.Text(text="Sources")],
                    on_click=GoToEvent(url="/sources"),
                    active="startswith:/sources",
                ),
                c.Link(
                    components=[c.Text(text="Info")],
                    on_click=GoToEvent(url="/info"),
                    active="startswith:/info",
                ),
                c.Link(
                    components=[c.Text(text="Projects")],
                    on_click=GoToEvent(url="/projects"),
                    active="startswith:/projects",
                ),
                c.Link(
                    components=[c.Text(text="Auth")],
                    on_click=GoToEvent(url="/auth/login/password"),
                    active="startswith:/auth",
                ),
            ],
            end_links=end_links,
        ),
        c.Page(
            components=[
                *((c.Heading(text=title, level=3),) if title else ()),
                *components,
            ],
        ),
        c.Footer(
            extra_text="timelink-py version: " + timelink_version,
            links=[
                c.Link(
                    components=[c.Text(text="Source code")],
                    on_click=GoToEvent(url="https://github.com/time-link/timelink-py"),
                ),
                c.Link(
                    components=[c.Text(text="PyPI")],
                    on_click=GoToEvent(url="https://pypi.org/project/timelink/"),
                ),
                c.Link(
                    components=[c.Text(text="Docs")],
                    on_click=GoToEvent(
                        url="https://joaquimrcarvalho.github.io/timelink/"
                    ),
                ),
                c.Link(
                    components=[c.Text(text="API documentation")],
                    on_click=GoToEvent(
                        url=f"{request.url.scheme}://{request.url.netloc}/docs"
                    ),
                ),
                c.Link(
                    components=[c.Text(text="Redoc documentation")],
                    on_click=GoToEvent(
                        url=f"{request.url.scheme}://{request.url.netloc}/redoc"
                    ),
                ),
            ],
        ),
    ]
    return page
