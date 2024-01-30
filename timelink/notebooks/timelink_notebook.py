import os

import pandas
from timelink.api.database import (
    TimelinkDatabase,
    is_valid_postgres_db_name,
    get_postgres_dbnames,
    get_sqlite_databases,
)
from timelink.kleio.kleio_server import KleioServer


class TimelinkNotebook:
    """A class to hold the Timleink server connections and other"""

    def __init__(
        self,
        project_name=None,  # name of the project. Defaults to the name of the directory
        project_home=None,
        # directory where kleio server looks for files. Defaults to the parent of the current directory
        db_type=None,  # type of database ('sqlite' or 'postgres'). Defaults to 'sqlite'
        db_name=None,  # name of the database. Defaults to project name, normalized
        kleio_image=None,  # docker image for kleio server. Defaults to 'timelinkserver/kleio-server'
        kleio_version=None,  # version of kleio server. Defaults to 'latest'
        postgres_image=None,  # docker image for postgres server. Defaults to 'postgres'
        postgres_version=None,  # version of postgres server. Defaults to 'latest'
        sqlite_dir=None,  # directory where sqlite databases are. Defaults to '../database/sqlite'
        **extra_args,
    ):
        """Create a TimelinkNotebook object

        Create a TimelinkNotebook object, which holds the interface
        to the Timelink system. Setup of Kleio Server and Timelink
        database is done here. Several functions are provided to
        manage the kleio files and access the database.

        Usage:
            from timelink.notebooks import TimelinkNotebook

            tln = TimelinkNotebook()
        """
        self.project_name = project_name
        self.project_home = project_home
        self.db_type = db_type
        self.db_name = db_name
        self.sqlite_dir = sqlite_dir
        self.kleio_image = kleio_image
        self.kleio_version = kleio_version
        self.postgres_image = postgres_image
        self.postgres_version = postgres_version

        if self.project_home is None:
            self.project_home = KleioServer.find_local_kleio_home()
        if self.project_name is None:
            self.project_name = os.path.basename(os.path.dirname(os.getcwd()))
        if self.db_type is None:
            self.db_type = "sqlite"
        if self.db_name is None:
            self.db_name = self.project_name.replace("-", "_")
        if self.kleio_image is None:
            self.kleio_image = "timelinkserver/kleio-server"
        if self.kleio_version is None:
            self.kleio_version = "latest"
        if self.sqlite_dir is None:
            self.sqlite_dir = os.path.join(self.project_home, "database", "sqlite")
            # create the directory if it does not exist
            if not os.path.exists(self.sqlite_dir):
                os.makedirs(self.sqlite_dir)
        if self.postgres_image is None:
            self.postgres_image = "postgres"
        if self.postgres_version is None:
            self.postgres_version = "latest"

        if self.db_type == "postgres":
            if not is_valid_postgres_db_name(self.db_name):
                raise Exception(f"Invalid database name: {self.db_name}")

        self.db: TimelinkDatabase = TimelinkDatabase(
            db_name=self.db_name,
            db_type=self.db_type,
            db_path=self.sqlite_dir,
            kleio_home=self.project_home,
            kleio_image=self.kleio_image,
            kleio_version=self.kleio_version,
            postgres_image=self.postgres_image,
            postgres_version=self.postgres_version,
            **extra_args,
        )
        self.kleio_server = self.db.get_kleio_server()

    def __repr__(self):
        return f"TimelinkNotebook(project_name={self.project_name}, project_home={self.project_home}, db_type={self.db_type}, db_name={self.db_name}, kleio_image={self.kleio_image}, kleio_version={self.kleio_version}, postgres_image={self.postgres_image}, postgres_version={self.postgres_version})"

    def __str__(self):
        return f"TimelinkNotebook(project_name={self.project_name}, project_home={self.project_home}, db_type={self.db_type}, db_name={self.db_name}, kleio_image={self.kleio_image}, kleio_version={self.kleio_version}, postgres_image={self.postgres_image}, postgres_version={self.postgres_version})"

    def print_info(self):
        """Print information about the TimelinkNotebook object"""
        print(f"Project name: {self.project_name}")
        print(f"Project home: {self.project_home}")
        print(f"Database type: {self.db_type}")
        print(f"Database name: {self.db_name}")
        print(f"Kleio image: {self.kleio_image}")
        print(f"Kleio version: {self.kleio_version}")

        kserver: KleioServer = self.db.get_kleio_server()
        if kserver is not None:
            print(f"Kleio server token: {kserver.get_token()}")
            print(f"Kleio server URL: {kserver.get_url()}")
            print(f"Kleio server home: {kserver.get_kleio_home()}")
        if self.db_type == "sqlite":
            print(f"SQLite directory: {self.sqlite_dir}")
        elif self.db_type == "postgres":
            print(f"Postgres image: {self.postgres_image}")
            print(f"Postgres version: {self.postgres_version}")
            print(f"Postgres user: {self.db.db_user}")
            print(f"Postgres password: {self.db.db_pwd}")

        print(self.__repr__())

    def get_import_status(self, data_frame=True, **kwargs):
        """Get the status of files imported

        Returns:
            A dictionary with the status of the import process
        """
        ifiles = [f.model_dump() for f in self.db.get_import_status(**kwargs)]
        if data_frame:
            # create a pandas Data frame
            ifiles_df = pandas.DataFrame(ifiles)
            # convert the column "status" to the enum value
            ifiles_df["status"] = ifiles_df["status"].apply(lambda x: x.value)
            ifiles_df["import_status"] = ifiles_df["import_status"].apply(
                lambda x: x.value
            )
            # convert the column "import_errors" to int with NA as 0
            # https://stackoverflow.com/questions/21287624/convert-pandas-column-containing-nans-to-dtype-int
            ifiles_df["import_errors"] = ifiles_df["import_errors"].astype("Int64")
            ifiles_df["import_warnings"] = ifiles_df["import_errors"].astype("Int64")
            return ifiles_df
        else:
            return ifiles

    def get_sqlite_databases(**kwargs):
        """Get the list of sqlite databases

        Returns:
            A list of sqlite databases
        """
        return get_sqlite_databases(**kwargs)

    def get_postgres_databases(**kwargs):
        """Get the list of postgres databases

        Returns:
            A list of postgres databases
        """
        return get_postgres_dbnames(**kwargs)
