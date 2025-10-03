from nicegui import ui, app
from timelink.web import timelink_web_utils
import sys
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# --- Pages ---
from timelink.web.pages import (homepage, status_page, explore_page,
                                display_id_page, tables_page, overview_page,
                                people_page, families_page, calendar_page,
                                linking_page, sources_page, search_page, admin_page)


port = 8000
kserver = None
database = None
project_path = Path.cwd()
database_type = "sqlite"
job_scheduler = AsyncIOScheduler()


def job_scheduler_listener(event):
    """Listens to events coming from the scheduler to monitor the execution of scheduled jobs."""

    job = job_scheduler.get_job(event.job_id).name

    if event.exception:
        print(f'\"{job}\" job crashed.')
    else:
        print(f'\"{job}\" job executed successfully.')


async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""

    global database, kserver, job_scheduler

    job_scheduler.add_listener(job_scheduler_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    kserver, database, solr_manager = await timelink_web_utils.run_setup(
        home_path=project_path,
        job_scheduler=job_scheduler,
        database_type=database_type)

    homepage.HomePage(database=database, kserver=kserver)

    explore_page.ExplorePage(database=database, kserver=kserver)

    id_page = display_id_page.DisplayIDPage(database=database, kserver=kserver)
    id_page.register()

    table_page = tables_page.TablesPage(database=database, kserver=kserver)
    table_page.register()

    overview_page.Overview(database=database, kserver=kserver)

    people_page.PeopleGroupsNetworks(database=database, kserver=kserver)

    families_page.Families(database=database, kserver=kserver)

    calendar_page.CalendarPage(database=database, kserver=kserver)

    linking_page.Linking(database=database, kserver=kserver)

    source_page = sources_page.Sources(database=database, kserver=kserver, scheduler=job_scheduler)

    status_page.StatusPage(database=database, kserver=kserver, sources=source_page)

    search_page.Search(database=database, kserver=kserver, solr_manager=solr_manager)

    admin_page.Admin(database=database, kserver=kserver)

    job_scheduler.start()


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
