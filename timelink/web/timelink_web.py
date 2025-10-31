from nicegui import ui, app
from timelink.web import timelink_web_utils
import sys
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette_admin.contrib.sqla import Admin, ModelView


# --- Pages ---
from timelink.web.pages import (homepage, status_page, explore_page,
                                display_id_page, tables_page, overview_page,
                                people_page, families_page, calendar_page,
                                linking_page, sources_page, search_page)
from timelink.web.models.project import Project, ProjectAccess
from timelink.web.models.user import User, UserProperty

port = 8000
kserver = None
database = None
project_path = Path.cwd()
database_type = "sqlite"
job_scheduler = AsyncIOScheduler()


async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""

    timelink_app_settings = await timelink_web_utils.run_setup(
        home_path=project_path,
        job_scheduler=job_scheduler,
        database_type=database_type
    )

    homepage.HomePage(timelink_app=timelink_app_settings)

    explore_page.ExplorePage(timelink_app=timelink_app_settings)

    id_page = display_id_page.DisplayIDPage(timelink_app=timelink_app_settings)
    id_page.register()

    table_page = tables_page.TablesPage(timelink_app=timelink_app_settings)
    table_page.register()

    overview_page.Overview(timelink_app=timelink_app_settings)

    people_page.PeopleGroupsNetworks(timelink_app=timelink_app_settings)

    families_page.Families(timelink_app=timelink_app_settings)

    calendar_page.CalendarPage(timelink_app=timelink_app_settings)

    linking_page.Linking(timelink_app=timelink_app_settings)

    source_page = sources_page.Sources(timelink_app=timelink_app_settings)

    status_page.StatusPage(timelink_app=timelink_app_settings, sources=source_page)

    search_page.Search(timelink_app=timelink_app_settings)

    # Starlette Admin setup
    admin_app = Admin(engine=timelink_app_settings.database.engine)
    admin_app.add_view(ModelView(User))
    admin_app.add_view(ModelView(UserProperty))
    admin_app.add_view(ModelView(Project))
    admin_app.add_view(ModelView(ProjectAccess))
    admin_app.mount_to(app)

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

app.on_startup(initial_setup)

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='Timelink Web Interface', port=int(port))
