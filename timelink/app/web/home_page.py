from fastapi import Request

from fastui import AnyComponent, components as c
from fastui.events import GoToEvent

from timelink import version as timelink_version


def home_page(*components: AnyComponent,
              request: Request = None,
              title: str = None,
              user: str = None) -> list[AnyComponent]:
    """Timelink FastUI main page

    Args:
        *components (AnyComponent): Components to add to the page
        request (Request, optional): The request. Defaults to None.
        title (str, optional): The title of the page. Defaults to None.
        user (str, optional): The user logged in. Defaults to None.
        """
    if user is None:
        user_str = ''
    else:
        user_str = f"({user.name})"
    page = [
        c.PageTitle(text=f'{title}' if title else 'Timelink'),
        c.Navbar(
            title=f'Timelink {user_str}',
            title_event=GoToEvent(url='/'),
            start_links=[
                c.Link(
                    components=[c.Text(text='Explore')],
                    on_click=GoToEvent(url='/explore'),
                    active='startswith:/explore',
                ),
                c.Link(
                    components=[c.Text(text='Sources')],
                    on_click=GoToEvent(url='/sources'),
                    active='startswith:/sources',
                ),
                c.Link(
                    components=[c.Text(text='Auth')],
                    on_click=GoToEvent(url='/auth/login/password'),
                    active='startswith:/auth',
                ),
                c.Link(
                    components=[c.Text(text='Info')],
                    on_click=GoToEvent(url='/info'),
                    active='startswith:/info',
                )
            ],
        ),
        c.Page(
            components=[
                *((c.Heading(text=title, level=3),) if title else ()),
                *components,
            ],
        ),
        c.Footer(
            extra_text='timelink-py version: ' + timelink_version,
            links=[
                c.Link(
                    components=[c.Text(text='Source code')], on_click=GoToEvent(url='https://github.com/time-link/timelink-py')
                ),
                c.Link(components=[c.Text(text='PyPI')], on_click=GoToEvent(url='https://pypi.org/project/timelink/')),
                c.Link(components=[c.Text(text='Docs')], on_click=GoToEvent(url='https://joaquimrcarvalho.github.io/timelink/')),
                c.Link(components=[c.Text(text="API documentation")],
                       on_click=GoToEvent(url=f"{request.url.scheme}://{request.url.netloc}/docs")),
                c.Link(components=[c.Text(text="Redoc documentation")],
                       on_click=GoToEvent(url=f"{request.url.scheme}://{request.url.netloc}/redoc"))
            ],
        ),
    ]
    return page
