""" Main class for the Timelink web application. """

import os
import json

import pandas
from timelink.api.database import TimelinkDatabase, get_postgres_dbnames, get_sqlite_databases, is_valid_postgres_db_name
from timelink.kleio.kleio_server import KleioServer


class TimelinkWebApp:
    """A class to interact with the Timelink system
    from a FastAPI web application

    It stores TimelinkDatabase and KleioServer objects,
    and an user registry.

    Each user has a token to access
    the KleioServer and the TimelinkDatabase associated.

    Several functions are provided to manage the kleio files
    and access the database.


    """

    def __init__(
        self,
        timelink_url: str = "http://localhost:8000",
        timelink_home: str = None,
        kleio_server: KleioServer = None,
        users_db_type: str = None,
        users_db_name: str = None,
        kleio_image=None,
        kleio_version=None,
        kleio_token=None,
        kleio_update=False,
        postgres_image=None,
        postgres_version=None,
        sqlite_dir=None,
        stop_duplicates=True,
        **extra_args,
    ):
        """Create a TimelinkWebApp instance

        Setup of Kleio Server and Timelink
        database is done here.

        Several functions are provided to
        manage the kleio files and access the database.

        Args:
            timelink_url: URL of the Timelink web application
            timelink_home: directory where the Timelink database is located
            kleio_server: a KleioServer instance
            users_db_type: type of the users database (sqlite or postgres)
            users_db_name: name of the users database
            kleio_image: name of the Kleio image to use
            kleio_version: version of the Kleio image to use
            kleio_token: token to access the Kleio server
            kleio_update: if True, update the Kleio server
            postgres_image: name of the postgres image to use
            postgres_version: version of the postgres image to use
            sqlite_dir: directory where the sqlite databases are located
            stop_duplicates: if True, stop duplicates
            **extra_args: extra arguments to pass to the TimelinkDatabase

        Returns:
            A TimelinkWebApp instance
        """
        self.timelink_home = timelink_home
        self.host_url = timelink_url
        self.kleio_server = kleio_server
        self.kleio_version = kleio_version
        self.db_type = users_db_type
        self.mhk_users_db = users_db_name
        self.kleio_image = kleio_image
        self.postgres_image = postgres_image
        self.postgres_version = postgres_version
        self.sqlite_dir = sqlite_dir
        self.stop_duplicates = stop_duplicates

        if self.timelink_home is None:
            self.timelink_home = os.path.join(os.getcwd(), "timelink-home")
        if self.db_type == "sqlite":
            if self.timelink_home is None:
                self.timelink_home = os.path.join(os.getcwd(), "timelink")
            self.db = TimelinkDatabase(
                db_type=self.db_type,
                db_name=self.mhk_users_db,
                timelink_home=self.timelink_home,
                stop_duplicates=self.stop_duplicates,
                **extra_args,
            )
        elif self.db_type == "postgres":
            self.db = TimelinkDatabase(
                db_type=self.db_type,
                db_name=self.mhk_users_db,
                **extra_args,
            )
        else:
            raise ValueError(f"Invalid database type: {self.db_type}")

        if self.kleio_server is not None:
            self.kleio_server = kleio_server
        else:
            self.kleio_server = KleioServer(
                image=self.kleio_image,
                version=self.kleio_version,
                token=kleio_token,
                update=kleio_update,
            )




    def print_info(self):
        """Print information about the Timel8nk Webapp object

        """
        info_dict = {
            "Timelink home": self.timelink_home,
            "Timelink host URL": self.host_url,
            "Timelink users database": self.mhk_users_db,
            "Kleio server": "None"

        }

        kserver: KleioServer = self.kleio_server
        if kserver is not None:
            info_dict.update({
                "Kleio server token": kserver.get_token(),
                "Kleio server URL": kserver.get_url(),
                "Kleio server home": kserver.get_kleio_home(),
            })
            if kserver.container is not None:
                info_dict["Kleio server container"] = kserver.container.name
            info_dict["Kleio version requested"] = self.kleio_version
            labels = kserver.container.labels
            build = labels.get("BUILD", "")
            version = labels.get("VERSION", "")
            build_date = labels.get("BUILD_DATE", "")
            if version != "":
                info_dict["Kleio server version"] = f"{version}.{build} ({build_date})"
        if self.db_type == "sqlite":
            info_dict["SQLite directory"] = self.sqlite_dir
        elif self.db_type == "postgres":
            info_dict.update({
                "Postgres image": self.postgres_image,
                "Postgres version": self.postgres_version,
                "Postgres user": self.db.db_user,
                "Postgres password": self.db.db_pwd,
            })

        print(json.dumps(info_dict, indent=4))
        print(self.__repr__())

    def get_imported_files(self, data_frame=True, **kwargs):
        """Get the list of imported files in the database

        See the get_imported_files method in the TimelinkDatabase class:
        :meth:`timelink.api.database.TimelinkDatabase.get_imported_files`

        Args:
            data_frame: if True, return a pandas DataFrame; otherwise,
                        return a list of dictionaries
            **kwargs: extra arguments to pass to the get_imported_files method
        """
        ifiles = self.db.get_imported_files(**kwargs)

        if data_frame:
            if len(ifiles) == 0:
                return pandas.DataFrame()
            ifiles_json = [f.model_dump() for f in ifiles]
            ifiles_df = pandas.DataFrame(ifiles_json)
            ifiles_df["nerrors"] = ifiles_df["nerrors"].astype("Int64")
            ifiles_df["nwarnings"] = ifiles_df["nerrors"].astype("Int64")
            return ifiles_df
        else:
            return ifiles

    def update_from_sources(self, **kwargs):
        """Update the database from a list of sources

        See the update_from_sources method in the TimelinkDatabase class:
        :meth:`timelink.api.database.TimelinkDatabase.update_from_sources`

        """
        self.db.update_from_sources(**kwargs)

    def get_import_status(self, data_frame=True, **kwargs):
        """Get the import status of Kleio Files

        Returns:
            A dictionary with the status of the import process
        """
        ifiles = [f.model_dump() for f in self.db.get_import_status(**kwargs)]
        if data_frame:
            if len(ifiles) == 0:
                return pandas.DataFrame()
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
            return ifiles_df.fillna(0)
        else:
            return ifiles

    def get_sqlite_databases(self, sqlite_dir=None, **kwargs):
        """Get the list of sqlite databases

        Args:
            sqlite_dir: directory where the sqlite databases are located
            **kwargs: extra arguments to pass to the get_sqlite_databases function

        Returns:
            A list of sqlite databases
        """
        if sqlite_dir is None:
            sqlite_dir = self.sqlite_dir
        return get_sqlite_databases(directory_path=sqlite_dir, **kwargs)

    def get_postgres_databases(self):
        """Get the list of postgres databases

        Returns:
            A list of postgres databases
        """
        return get_postgres_dbnames()

    def table_row_count_df(self):
        """Return the row count of all tables in the database"""
        tables = self.db.table_row_count()
        tables_df = pandas.DataFrame(tables, columns=["table", "count"])
        return tables_df

    def get_file_paths(self, file_spec, rows, column):
        """Get the file paths from DataFrame of from a string

        TODO: #27 add parameter to convert the paths to absolute local paths"""
        if isinstance(file_spec, pandas.DataFrame):
            if column not in file_spec.columns:
                raise Exception(f"There is no {column} in the DataFrame")
            if rows is None:
                raise Exception("The 'rows' argument must be present")
            if type(rows) is not list:
                rows = [rows]
            file_paths = file_spec.iloc[list(rows)][column].tolist()
            return file_paths
        else:
            return []

    def get_import_rpt(
        self, file_spec: pandas.DataFrame | str, rows=None, match_path=False, **kwargs
    ):
        """Show the import report for a given file specification

        Args:
            file_spec: file specification (DataFrame or string)
                       If a DataFrame, it should have the columns 'path'
                       and the arguments 'rows' must be present
            rows: if file_spec is a DataFrane, the row number to show
            match_path: if True, the path is used to retrieve the import report;
                        if false the filename is used (default).
            **kwargs: extra arguments to pass to the show_import_rpt method
                      in the TimelinkDatabase class

        """
        rpt = ""
        if match_path:
            column = "path"
        else:
            column = "name"
        if isinstance(file_spec, pandas.DataFrame):
            paths = self.get_file_paths(file_spec, rows, column)
            for file in paths:
                rpt += self.db.get_import_rpt(file, match_path=match_path, **kwargs)
        elif isinstance(file_spec, str):
            return self.db.get_import_rpt(file_spec, match_path=match_path, **kwargs)
        else:
            raise ValueError
        return rpt

    def get_translation_report(self, file_spec, rows=None):
        """Show the translation report for a given file specification

        Args:
            file_spec: file specification (DataFrame or string)
                       If a DataFrame, it should have the columns 'rpt_url'
                       and the arguments 'rows' must be present
            rows: if file_spec is a DataFrane, the row number of interest
        """
        rpt = ""
        if isinstance(file_spec, pandas.DataFrame):
            if rows is None:
                raise ValueError(
                    "The 'rows' argument must be present "
                    "if the file_spec is a DataFrame"
                )
            elif type(rows) is not list:
                rows = [rows]
            if len(rows) == 0:
                raise ValueError(
                    "The 'rows' argument must be a non-empty list, or an integer"
                )

            paths = self.get_file_paths(file_spec, rows, "rpt_url")
            for file in paths:
                rpt += self.kleio_server.get_report(file)
        elif isinstance(file_spec, str):
            return self.kleio_server.get_report(file_spec)
        else:
            raise ValueError
        return rpt

    def get_kleio_files(self, data_frame=True, **kwargs):
        """Get the list of files in the kleio server.

        Alias to :meth:`timelink.notebooks.TimelinkNotebook.get_import_status`
        but returns a subset of the columns.

            #   Column              Non-Null Count  Dtype
            ---  ------              --------------  -----
            0   path                3 non-null      object
            1   name                3 non-null      object
            2   size                3 non-null      int64
            3   directory           3 non-null      object
            4   modified            3 non-null      datetime64[ns, UTC]
            5   modified_iso        3 non-null      datetime64[ns, UTC]
            6   modified_string     3 non-null      object
            7   qtime               3 non-null      datetime64[ns, UTC]
            8   qtime_string        3 non-null      object
            9   source_url          3 non-null      object
            10  status              3 non-null      object
            11  translated          3 non-null      datetime64[ns, UTC]
            12  translated_string   3 non-null      object
            13  errors              3 non-null      int64
            14  warnings            3 non-null      int64
            15  version             3 non-null      object
            16  rpt_url             3 non-null      object
            17  xml_url             3 non-null      object
            18  import_status       3 non-null      object
            19  import_errors       3 non-null      Int64
            20  import_warnings     3 non-null      Int64
            21  import_error_rpt    3 non-null      object
            22  import_warning_rpt  3 non-null      object
            23  imported            3 non-null      int64
            24  imported_string     3 non-null      int64
        """
        result = self.get_import_status(**kwargs)
        return result[
            [
                "path",
                "name",
                "modified",
                "status",
                "translated",
                "errors",
                "warnings",
                "import_status",
                "import_errors",
                "import_warnings",
                "import_error_rpt",
                "import_warning_rpt",
                "imported",
                "rpt_url",
                "xml_url",
            ]
        ]