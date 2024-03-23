from fastapi import Request

from fastui import AnyComponent, components as c
from fastui.events import GoToEvent

from timelink import version as timelink_version
from timelink.app.schemas.user import UserSchema


async def home_page(
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
    if user is None:
        user_name = "guest"
        current_project_name = "None"
    else:
        user_name = user.name
        if user_name == "":
            user_name = user.email.split("@")[0]
        if user.current_project_name is None:
            current_project_name = "None"
        else:
            current_project_name = user.current_project_name

    start_links = [
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
    ]
    if user is not None and user.is_admin():
        admin_link = c.Link(
            components=[c.Text(text="Admin")],
            on_click=GoToEvent(url="/adm"),
            active="startswith:/adm",
        )
        start_links.append(admin_link)

    if user is None or user_name == "guest":
        auth_url = request.url_for("login")
        login_logout = c.Link(
            components=[c.Text(text="Login")],
            on_click=GoToEvent(url=str(auth_url)),
            active=f"startswith:{auth_url}",
        )
    else:
        logout_url = request.url_for("logout")
        login_logout = c.Link(
            components=[c.Text(text="Logout")],
            on_click=GoToEvent(url=str(logout_url)),
            active=f"startswith:{logout_url}",
        )
    end_links = [login_logout]
    page = [
        c.PageTitle(text=f"{title}" if title else "Timelink"),
        c.Navbar(
            title="Timelink",
            title_event=GoToEvent(url="/"),
            start_links=start_links,
            end_links=end_links,
        ),
        c.Page(
            components=[
                *((c.Heading(text=title, level=3),) if title else ()),
                *components,
                c.Heading(level=6, text=f"{user_name} ({current_project_name})"),
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
