from nicegui import ui, app
from timelink.web import timelink_web_utils
import sys
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


# --- Pages ---
from timelink.web.pages import login, homepage, register_page

port = 8000
kserver = None
database = None
project_path = Path.cwd()
database_type = "sqlite"
job_scheduler = AsyncIOScheduler()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in {'/admin/'}:
                if not app.storage.user.get("is_admin", False):
                    return RedirectResponse("/")
            if request.url.path not in {'/login', '/register'} and not request.url.path.startswith('/_nicegui'):
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        else:
            if request.url.path.startswith('/admin'):
                if not app.storage.user.get("is_admin", False):
                    return RedirectResponse("/")
        return await call_next(request)


async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""

    timelink_app_settings = await timelink_web_utils.run_setup(
        home_path=project_path,
        job_scheduler=job_scheduler,
        database_type=database_type
    )

    login.Login(timelink_app=timelink_app_settings)
    homepage.HomePage(timelink_app=timelink_app_settings)
    register_page.RegisterPage(timelink_app=timelink_app_settings)
    timelink_app_settings.job_scheduler.start()


if "--port" in sys.argv:
    idx = sys.argv.index("--port") + 1
    if idx < len(sys.argv):
        port = int(sys.argv[idx])

if "--directory" in sys.argv:
    idx = sys.argv.index("--directory") + 1
    if idx < len(sys.argv):
        project_path = Path(sys.argv[idx]).resolve()

if "--database" in sys.argv:
    idx = sys.argv.index("--database") + 1
    if idx < len(sys.argv):
        database_type = sys.argv[idx]

app.add_middleware(AuthMiddleware)
app.on_startup(initial_setup)

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='Timelink Web Interface', port=int(port), storage_secret="Very secret secret!")
