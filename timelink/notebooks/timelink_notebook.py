import os
import pandas
import timelink
from timelink.api.database import TimelinkDatabase
from timelink.api.database import is_valid_postgres_db_name
from timelink.api.database import get_postgres_dbnames
from timelink.api.database import get_sqlite_databases
from timelink.kleio.kleio_server import KleioServer


def clean_kleiofile_df(df: pandas.DataFrame) -> pandas.DataFrame:
    # Todo: move this function to the pandas module
    # convert the column "status" to the enum value
    df["status"] = df["status"].apply(lambda x: x.value)
    df["import_status"] = df["import_status"].apply(lambda x: x.value)
    # convert the column "import_errors" to int with NA as 0
    # https://stackoverflow.com/questions/21287624/convert-pandas-column-containing-nans-to-dtype-int
    df["import_errors"] = df["import_errors"].astype("Int64")
    df["import_warnings"] = df["import_errors"].astype("Int64")
    return df.fillna(0)


class TimelinkNotebook:
    """A class to interact with the Timelink system
    from Jupyter notebooks

    Example:

    .. code-block:: python

        from timelink.notebooks import TimelinkNotebook

        tln = TimelinkNotebook()
        tln.print_info()
    """

    def __init__(
        self,
        project_name=None,
        project_home=None,
        db_type=None,
        db_name=None,
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
        """Create a TimelinkNotebook instance

        Setup of Kleio Server and Timelink
        database is done here.

        Several functions are provided to
        manage the kleio files and access the database.

        Args:
            project_name: name of the project. Defaults to the name of the parent directory
                        of the current directory.
            project_home: directory where kleio server looks for files;
                    defaults to the parent of the current directory.
            db_type: type of database ('sqlite' or 'postgres'). Defaults to 'sqlite'
            db_name: name of the database. Defaults to project name, normalized
            kleio_image: docker image for kleio server;
                            defaults to 'timelinkserver/kleio-server'
            kleio_version: version of kleio server. Defaults to 'latest'
            kleio_token: start kleio server with this token.
                            Defaults to None (create a new token)
            kleio_update: if True, update the kleio server image. Defaults to False
            postgres_image: docker image for postgres server. Defaults to 'postgres'
            postgres_version: version of postgres server. Defaults to 'latest'
            sqlite_dir: directory where sqlite databases are. Defaults to '../database/sqlite'
            stop_duplicates: if True, stop duplicates when importing files. Defaults to True
            **extra_args: extra arguments to pass to the TimelinkDatabase object

        Returns:
            A TimelinkNotebook object
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
            self.db_name = self.project_name.replace("-", "_").replace(" ", "_")
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
                raise ValueError(f"Invalid database name: {self.db_name}")

        self.db: TimelinkDatabase = TimelinkDatabase(
            db_name=self.db_name,
            db_type=self.db_type,
            db_path=self.sqlite_dir,
            kleio_home=self.project_home,
            kleio_image=self.kleio_image,
            kleio_version=self.kleio_version,
            kleio_token=None,
            kleio_update=kleio_update,
            postgres_image=self.postgres_image,
            postgres_version=self.postgres_version,
            stop_duplicates=stop_duplicates,
            **extra_args,
        )
        self.kleio_server = self.db.get_kleio_server()

    def __repr__(self):
        return (
            f"TimelinkNotebook(project_name={self.project_name}, "
            f"project_home={self.project_home}, db_type={self.db_type}, "
            f"db_name={self.db_name}, kleio_image={self.kleio_image}, "
            f"kleio_version={self.kleio_version}, "
            f"postgres_image={self.postgres_image}, "
            f"postgres_version={self.postgres_version})"
        )

    def __str__(self):
        return (
            f"TimelinkNotebook(project_name={self.project_name}, "
            f"project_home={self.project_home}, db_type={self.db_type}, "
            f"db_name={self.db_name}, kleio_image={self.kleio_image}, "
            f"kleio_version={self.kleio_version}, "
            f"postgres_image={self.postgres_image}, "
            f"postgres_version={self.postgres_version})"
        )

    def print_info(self, show_token=False, show_password=False):
        """Print information about the TimelinkNotebook object

        Args:
            show_token: if True, show the token of the kleio server
            show_password: if True, show the password of the postgres server

        """
        info_dict = self.get_info(show_token, show_password)

        for key, value in info_dict.items():
            print(f"{key}: {value}")
        if not show_token:
            print("Call print_info(show_token=True) to show the Kleio Server token")
        if not show_password:
            print("Call print_info(show_password=True) to show the Postgres password")
        print(self.__repr__())

    def get_info(self, show_token, show_password):
        info_dict = {
            "Timelink version": timelink.version,
            "Project name": self.project_name,
            "Project home": self.project_home,
            "Database type": self.db_type,
            "Database name": self.db_name,
            "Kleio image": self.kleio_image,
        }

        kserver: KleioServer = self.db.get_kleio_server()
        if kserver is not None:
            if show_token:
                info_dict["Kleio server token"] = kserver.get_token()
            else:
                info_dict["Kleio server token"] = kserver.get_token()[:5] + "..."

            info_dict.update({
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
            if show_password:
                info_dict["Postgres password"] = self.db.db_pwd
            else:
                info_dict["Postgres password"] = "..."
            info_dict.update({
                "Postgres image": self.postgres_image,
                "Postgres version": self.postgres_version,
                "Postgres user": self.db.db_user,
            })

        return info_dict

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
        """
        self.db.update_from_sources(**kwargs)

    update_from_sources.__doc__ = TimelinkDatabase.update_from_sources.__doc__

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
                rpt += file + "\n"
                rpt += self.db.get_import_rpt(file, match_path=match_path, **kwargs)
                rpt += "\n\n"
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

        | Column             | Non-Null Count | Dtype             |
       \|-------------------\|---------------\|-------------------|
        | path               | 3 non-null     | object            |
        | name               | 3 non-null     | object            |
        | size               | 3 non-null     | int64             |
        | directory          | 3 non-null     | object            |
        | modified           | 3 non-null     | datetime64        |
        | modified_iso       | 3 non-null     | datetime64        |
        | modified_string    | 3 non-null     | object            |
        | qtime              | 3 non-null     | datetime64        |
        | qtime_string       | 3 non-null     | object            |
        | source_url         | 3 non-null     | object            |
        | status             | 3 non-null     | object            |
        | translated         | 3 non-null     | datetime64        |
        | translated_string  | 3 non-null     | object            |
        | errors             | 3 non-null     | int64             |
        | warnings           | 3 non-null     | int64             |
        | version            | 3 non-null     | object            |
        | rpt_url            | 3 non-null     | object            |
        | xml_url            | 3 non-null     | object            |
        | import_status      | 3 non-null     | object            |
        | import_errors      | 3 non-null     | Int64             |
        | import_warnings    | 3 non-null     | Int64             |
        | import_error_rpt   | 3 non-null     | object            |
        | import_warning_rpt | 3 non-null     | object            |
        | imported           | 3 non-null     | int64             |
        | imported_string    | 3 non-null     | int64             |

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
