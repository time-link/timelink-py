import os
import pandas
from timelink.api.database import TimelinkDatabase
from timelink.api.database import is_valid_postgres_db_name
from timelink.api.database import get_postgres_dbnames
from timelink.api.database import get_sqlite_databases
from timelink.kleio.kleio_server import KleioServer


def clean_kleiofile_df(df: pandas.DataFrame) -> pandas.DataFrame:
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
        postgres_image=None,
        postgres_version=None,
        sqlite_dir=None,
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
            postgres_image: docker image for postgres server. Defaults to 'postgres'
            postgres_version: version of postgres server. Defaults to 'latest'
            sqlite_dir: directory where sqlite databases are. Defaults to '../database/sqlite'
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
        """Get the file paths from DataFrame of from a string"""
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
                raise ValueError("The 'rows' argument must be present "
                                 "if the file_spec is a DataFrame")
            elif type(rows) is not list:
                rows = [rows]
            if len(rows) == 0:
                raise ValueError("The 'rows' argument must be a non-empty list, or an integer")

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
        return result[["path", "name", "modified",
                       "status", "translated",
                       "errors", "warnings",
                       "import_status",
                       "import_errors", "import_warnings",
                       "import_error_rpt",
                       "import_warning_rpt",
                       "imported",
                       "rpt_url", "xml_url"]]
