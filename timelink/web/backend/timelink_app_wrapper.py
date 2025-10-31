""" Main class for the Timelink web application. """

import os
from pathlib import Path
from dotenv import load_dotenv
import docker
from datetime import datetime

import timelink
from timelink.api.database import TimelinkDatabase, get_postgres_dbnames, get_sqlite_databases
from timelink.web.models.activity import Activity, ActivityBase
from timelink.web.models.project import Project, ProjectAccess
from timelink.web.models.user import UserBase
from timelink.api.models import Entity
from timelink.api.schemas import EntityAttrRelSchema
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from timelink.kleio.kleio_server import KleioServer
from timelink.web.backend.solr_wrapper import SolrWrapper
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR


class TimelinkWebApp:
    """A class to interact with the Timelink system throug NiceGUI

    It stores TimelinkDatabase, KleioServer objects and any other needed configurations.


    Attributes:
        app_name (str): Name of the application.
        timelink_home (str): Directory where the Timelink database is located.
        users_db_type (str): Type of the users database (sqlite or postgres).
        solr_manager (SolrWrapper): Wrapper for the Pysolr client.
        job_scheduler (AsyncIOScheduler): Job scheduler for running jobs at regular intervals.

    """

    def __init__(
        self,
        home_url: Path = "",
        timelink_home: str = None,
        users_db_type: str = "sqlite",
        job_scheduler: AsyncIOScheduler = None,
        solr_manager: SolrWrapper = None
    ):
        """Create a TimelinkWebApp instance

        Setup of Kleio Server and Timelink
        database is done here.

        Several functions are provided to
        manage the kleio files and access the database.

        Args:
            home_url: home path where the application is running from
            timelink_home: directory where the Timelink database is located
            users_db_name: name of the users database
            solr_manager: Solr management class.
        Returns:
            A TimelinkWebApp instance
        """

        self.home_url = home_url
        self.timelink_home = timelink_home
        self.users_db_type = users_db_type
        self.solr_manager = solr_manager
        self.job_scheduler = job_scheduler

        if self.timelink_home is None:
            self.timelink_home = KleioServer.find_local_kleio_home(str(self.home_url))
            print(f"Timelink Home set to {self.timelink_home}")

            # If for some reason timelink home wasn't found, then attempt to read it from .timelink\.env found at root directory.
            if not self.timelink_home:
                print("Could not find timelink home in the current directory. Attempting to read from .timelink env options.")
                load_dotenv(Path.home() / ".timelink" / ".env")
                self.kleio_token = os.getenv('TIMELINK_SERVER_TOKEN')
                self.timelink_home = os.getenv('TIMELINK_HOME')
                self.users_db_type = os.getenv('TIMELINK_DB_TYPE')
                self.kleio_server = KleioServer.start(kleio_admin_token=self.kleio_token, kleio_home=self.timelink_home)

            else:
                self.kleio_server = KleioServer.get_server(self.timelink_home)
                if not self.kleio_server:
                    self.kleio_port = self.find_free_port(8088, 8099)
                    self.kleio_server = KleioServer.start(kleio_home=self.timelink_home, kleio_external_port=self.kleio_port)
                self.users_db_type = users_db_type
            print(f"Connected to Kleio Server at {self.kleio_server.url}, home is {self.kleio_server.kleio_home}")

        self.database = self.run_db_setup()

        self.job_scheduler_init_setup()

    def job_scheduler_init_setup(self):
        """Initiate job scheduler listeners and indeing scheduler event"""

        self.job_scheduler.add_listener(self.job_scheduler_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self.job_scheduler.add_job(self.init_index_job_scheduler, name="Index Documents to Solr", trigger="interval", minutes=1)

    async def init_index_job_scheduler(self):
        """Initiate the job to index new documents to the Apache Solr database"""

        print("Initiating Solr indexing job...")

        ignore_classes = ['class', 'rentity', 'source']

        with self.database.session() as session:
            entities = session.query(Entity).filter(
                Entity.indexed.is_(None)
            ).filter(~Entity.pom_class.in_(ignore_classes)).limit(10).all()

            if not entities:
                print("No entities need to be indexed.")
                return

            solr_doc_list = []
            for entity in entities:
                mr_schema = EntityAttrRelSchema.model_validate(entity)
                mr_schema_dump = mr_schema.model_dump()
                solr_doc_list.append(self.solr_manager.entity_to_solr_doc(mr_schema_dump))

            self.solr_manager.solr_client.add(solr_doc_list, commit=True)

            now = datetime.now()
            for entity in entities:
                print(f"Entity {entity.id} indexed at date {now}.")
                entity.indexed = now

            session.commit()

    def job_scheduler_listener(self, event):
        """Listens to events coming from the scheduler to monitor the execution of scheduled jobs."""

        job = self.job_scheduler.get_job(event.job_id).name

        if event.exception:
            print(f'\"{job}\" job crashed.')
        else:
            print(f'\"{job}\" job executed successfully.')

    def is_port_in_use_docker(self, port: int) -> bool:
        """Check if a port is being used by docker."""
        client = docker.from_env()
        for c in client.containers.list():
            ports = c.attrs["NetworkSettings"]["Ports"]
            if ports:
                for _, mappings in ports.items():
                    if mappings:
                        for m in mappings:
                            if int(m["HostPort"]) == port:
                                return True
        return False

    def find_free_port(self, from_port: int = 8088, to_port: int = 8099):
        """"Helper function to find free port to run a docker instance on."""
        for port in range(from_port, to_port + 1):
            if not self.is_port_in_use_docker(port):
                return port
        raise OSError(f"No free ports available in {from_port}-{to_port}")

    def run_db_setup(self):
        """Run DB setup according to chosen database type."""

        print("Selected Database configuration:", self.users_db_type)

        if self.users_db_type == "sqlite":
            db_dir = os.path.join(self.timelink_home, 'database', 'sqlite')
            print("Database type is set to Sqlite.")
            print("Databases will reside in: ", db_dir)
            print("Databases found in directory: ", get_sqlite_databases(directory_path=self.timelink_home))

            db = TimelinkDatabase(db_type=self.users_db_type, db_path=db_dir, db_name='timelink-web')

        elif self.users_db_type == "postgres":

            print("Database type is set to Postgres.")
            print("Databases found in directory: ", get_postgres_dbnames())

            db = TimelinkDatabase(db_type='postgres', db_name='timelink-web')

        # Check if tables exist here.
        tables = db.db_table_names()

        if "activity" not in tables:
            print("No Activity table found in the database - creating...")
            ActivityBase.metadata.create_all(bind=db.engine, tables=[Activity.__table__])
            print("Done!")

        if "users" not in tables:
            print("Creating user/project tables...")
            UserBase.metadata.create_all(bind=db.engine)
            print("Done!")

        db.set_kleio_server(self.kleio_server)
        return db

    def get_info(self, show_token=False, show_password=False):
        """Print information about the Timelink Webapp object"""

        info_dict = {
            "Timelink version": timelink.version,
            "Timelink home": self.timelink_home,
            "Kleio server": self.kleio_server.get_url()
        }

        kserver: KleioServer = self.kleio_server
        if kserver is not None:
            info_dict.update(
                {
                    "Kleio server token": kserver.get_token(),
                    "Kleio server URL": kserver.get_url(),
                    "Kleio server home": kserver.get_kleio_home(),
                }
            )
            if not show_token:
                info_dict["Kleio server token"] = kserver.get_token()[:5] + "..."
            if kserver.container is not None:
                info_dict["Kleio server container"] = kserver.container.name
            labels = kserver.container.labels
            build = labels.get("BUILD", "")
            version = labels.get("VERSION", "")
            build_date = labels.get("BUILD_DATE", "")
            if version != "":
                info_dict["Kleio server version"] = f"{version}.{build} ({build_date})"
        return info_dict
