from unittest.mock import MagicMock, patch
from timelink.web.backend.timelink_app_wrapper import TimelinkWebApp, Entity, EntityAttrRelSchema
import pytest


def test_init_uses_existing_kleio_home(fake_timelink_app):
    fake_solr = MagicMock(solr_core_name="core1")

    with patch("timelink.web.backend.timelink_app_wrapper.KleioServer.find_local_kleio_home",
               return_value="/fake/home"), \
         patch("timelink.web.backend.timelink_app_wrapper.KleioServer.get_server",
               return_value=fake_timelink_app.kleio_server), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.run_users_db_setup",
               return_value=MagicMock()), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.load_config_for_project_list"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.create_template_project"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.job_scheduler_init_setup"):

        app = TimelinkWebApp(home_url="/x", solr_manager=fake_solr)

        assert app.timelink_home == "/fake/home"
        assert app.kleio_server is fake_timelink_app.kleio_server


@pytest.mark.asyncio
async def test_init_starts_server_if_missing_kserver(fake_kserver):
    with patch("timelink.web.backend.timelink_app_wrapper.KleioServer.find_local_kleio_home", return_value="/fake/home"), \
         patch("timelink.web.backend.timelink_app_wrapper.KleioServer.get_server", return_value=None), \
         patch("timelink.web.backend.timelink_app_wrapper.KleioServer.start", return_value=fake_kserver), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.find_free_port", return_value=8088), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.run_users_db_setup", return_value=MagicMock()), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.load_config_for_project_list"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.create_template_project"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.job_scheduler_init_setup"):

        app = TimelinkWebApp(home_url="/x")

        assert app.kleio_server is fake_kserver


def test_init_uses_env_vars_if_no_home_found(fake_kserver):
    with patch("timelink.web.backend.timelink_app_wrapper.KleioServer.find_local_kleio_home",
               return_value=None), \
         patch("timelink.web.backend.timelink_app_wrapper.load_dotenv"), \
         patch("timelink.web.backend.timelink_app_wrapper.os.getenv") as getenv, \
         patch("timelink.web.backend.timelink_app_wrapper.KleioServer.start",
               return_value=fake_kserver), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.run_users_db_setup",
               return_value=MagicMock()), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.load_config_for_project_list"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.create_template_project"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.job_scheduler_init_setup"):

        getenv.side_effect = lambda k: {
            "TIMELINK_SERVER_TOKEN": "TOK",
            "TIMELINK_HOME": "/env/home",
            "TIMELINK_DB_TYPE": "sqlite"
        }.get(k)

        app = TimelinkWebApp(home_url="/x")

        assert app.kleio_server is fake_kserver
        assert app.timelink_home == "/env/home"
        assert app.db_type == "sqlite"


def test_init_runs_users_db_setup():
    with patch("timelink.web.backend.timelink_app_wrapper.KleioServer.find_local_kleio_home",
               return_value="/fake/home"), \
         patch("timelink.web.backend.timelink_app_wrapper.KleioServer.get_server") as srv, \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.run_users_db_setup",
               return_value="DB") as setup_db, \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.load_config_for_project_list"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.create_template_project"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.job_scheduler_init_setup"):

        srv.return_value.url = "x"
        srv.return_value.kleio_home = "y"

        app = TimelinkWebApp(home_url="/x")

        setup_db.assert_called_once()
        assert app.users_database == "DB"


def test_init_loads_default_project_list():
    with patch("timelink.web.backend.timelink_app_wrapper.KleioServer.find_local_kleio_home",
               return_value="/fake/home"), \
         patch("timelink.web.backend.timelink_app_wrapper.KleioServer.get_server") as srv, \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.load_config_for_project_list") as loadcfg, \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.create_template_project"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.run_users_db_setup"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.job_scheduler_init_setup"):

        srv.return_value.url = "x"
        srv.return_value.kleio_home = "y"

        TimelinkWebApp(home_url="/x")

        loadcfg.assert_called_once_with([])


def test_init_scheduler_setup():

    with patch("timelink.web.backend.timelink_app_wrapper.KleioServer.find_local_kleio_home",
               return_value="/fake/home"), \
         patch("timelink.web.backend.timelink_app_wrapper.KleioServer.get_server") as srv, \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.job_scheduler_init_setup") as sched, \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.create_template_project"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.run_users_db_setup"), \
         patch("timelink.web.backend.timelink_app_wrapper.TimelinkWebApp.load_config_for_project_list"):

        srv.return_value.url = "x"
        srv.return_value.kleio_home = "y"

        TimelinkWebApp(home_url="/x")

        sched.assert_called_once()


def test_create_template_project_real_app(monkeypatch):
    # Instantiate real TimelinkWebApp but patch side effects
    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.sqlite_dir = "/fake/sqlite"
    app.kleio_server = MagicMock(url="http://fake-kleio")

    class FakeSolr:
        solr_core_name = "fake_core"
    app.solr_manager = FakeSolr()

    fake_users_db = MagicMock()
    app.users_db = fake_users_db
    fake_session = MagicMock()
    fake_users_db.session.return_value.__enter__.return_value = fake_session

    # Make query.first() return None so the branch is executed
    fake_session.query.return_value.filter_by.return_value.first.return_value = None

    fake_admin = MagicMock(id=10)
    fake_guest = MagicMock(id=20)
    fake_users_db.get_user_by_nickname.side_effect = [fake_admin, fake_guest]

    # Run the real method
    app.create_template_project()

    # Assertions
    fake_users_db.add_project.assert_called_once()
    fake_users_db.set_user_project_access.assert_any_call(
        user_id=10, project_id=1, access_level="admin", session=fake_session
    )
    fake_users_db.set_user_project_access.assert_any_call(
        user_id=20, project_id=1, access_level="viewer", session=fake_session
    )
    fake_session.commit.assert_called_once()


def test_job_scheduler_init_setup_adds_listener_and_job():

    fake_timelink_app = TimelinkWebApp.__new__(TimelinkWebApp)
    fake_timelink_app.job_scheduler = MagicMock()
    fake_timelink_app.solr_manager = MagicMock()
    fake_timelink_app.database = MagicMock()

    fake_timelink_app.job_scheduler.add_listener = MagicMock()
    fake_timelink_app.job_scheduler.add_job = MagicMock()

    fake_timelink_app.job_scheduler_init_setup()

    fake_timelink_app.job_scheduler.add_listener.assert_called_once()
    fake_timelink_app.job_scheduler.add_job.assert_called_once()
    assert fake_timelink_app.job_scheduler.add_job.call_args[1]["name"] == "Index Documents to Solr"
    assert fake_timelink_app.job_scheduler.add_job.call_args[1]["trigger"] == "interval"
    assert fake_timelink_app.job_scheduler.add_job.call_args[1]["minutes"] == 5


@pytest.mark.asyncio
async def test_init_index_job_scheduler_indexes_entities():

    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.job_scheduler = MagicMock()
    app.database = MagicMock()
    app.solr_manager = MagicMock()
    app.solr_manager.solr_client = MagicMock()

    # Create a real Entity object
    fake_entity = Entity(
        id="123",
        pom_class="person",
        inside="A",
        groupname="G",
        the_source="SRC",
        the_order=1,
        the_level=1,
        updated=None,
        rels_in=[]
    )

    # Patch session and query chain
    fake_session = MagicMock()
    app.database.session.return_value.__enter__.return_value = fake_session
    fake_session.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = [fake_entity]

    # Patch model_validate to return a mock with model_dump
    mock_schema = MagicMock()
    mock_schema.model_dump.return_value = {
        "id": "123",
        "pom_class": "person",
        "inside": "A"
    }

    with patch(
        "timelink.web.backend.timelink_app_wrapper.EntityAttrRelSchema.model_validate",
        return_value=mock_schema
    ):
        app.solr_manager.entity_to_solr_doc.side_effect = lambda x: {"id": x["id"]}

        # Run the indexing job
        await app.init_index_job_scheduler()

    # Assertions
    app.solr_manager.entity_to_solr_doc.assert_called_once()
    app.solr_manager.solr_client.add.assert_called_once_with([{"id": "123"}], commit=True)
    fake_session.commit.assert_called_once()


def test_job_scheduler_listener_prints(monkeypatch):

    fake_timelink_app = TimelinkWebApp.__new__(TimelinkWebApp)
    fake_timelink_app.job_scheduler = MagicMock()
    fake_timelink_app.solr_manager = MagicMock()
    fake_timelink_app.database = MagicMock()

    fake_event = MagicMock()
    fake_event.job_id = "job123"
    fake_event.exception = None
    fake_job = MagicMock()
    fake_job.name = "TestJob"

    fake_timelink_app.job_scheduler.get_job.return_value = fake_job

    printed = []
    monkeypatch.setattr("builtins.print", lambda s: printed.append(s))
    fake_timelink_app.job_scheduler_listener(fake_event)
    assert '"TestJob" job executed successfully.' in printed[0]


def test_job_scheduler_listener_exception(monkeypatch):

    fake_timelink_app = TimelinkWebApp.__new__(TimelinkWebApp)
    fake_timelink_app.job_scheduler = MagicMock()
    fake_timelink_app.solr_manager = MagicMock()
    fake_timelink_app.database = MagicMock()

    fake_event = MagicMock()
    fake_event.job_id = "job123"
    fake_event.exception = True
    fake_job = MagicMock()
    fake_job.name = "FailJob"

    fake_timelink_app.job_scheduler.get_job.return_value = fake_job

    printed = []
    monkeypatch.setattr("builtins.print", lambda s: printed.append(s))
    fake_timelink_app.job_scheduler_listener(fake_event)
    assert '"FailJob" job crashed.' in printed[0]


def test_is_port_in_use_docker_true():
    app = TimelinkWebApp.__new__(TimelinkWebApp)
    fake_container = MagicMock()
    fake_container.attrs = {
        "NetworkSettings": {
            "Ports": {"8088/tcp": [{"HostPort": "8088"}]}
        }
    }

    with patch("docker.from_env") as mock_docker:
        mock_docker.return_value.containers.list.return_value = [fake_container]
        assert app.is_port_in_use_docker(8088) is True
        assert app.is_port_in_use_docker(9999) is False


def test_find_free_port():

    app = TimelinkWebApp.__new__(TimelinkWebApp)

    # Mock is_port_in_use_docker to simulate 8088 and 8089 in use
    app.is_port_in_use_docker = MagicMock(side_effect=lambda p: p in [8088, 8089])

    free_port = app.find_free_port(8088, 8090)
    assert free_port == 8090


def test_find_free_port_no_free():
    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.is_port_in_use_docker = MagicMock(return_value=True)

    with pytest.raises(OSError) as e:
        app.find_free_port(8088, 8090)
    assert "No free ports available" in str(e.value)


def test_run_users_db_setup_sqlite():

    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.users_db_type = "sqlite"
    app.users_db_name = "test_db"
    app.sqlite_dir = "/tmp/sqlite_dir"
    app.timelink_home = "/tmp"
    app.postgres_image = None
    app.postgres_version = None

    with patch("os.makedirs") as makedirs, \
         patch("os.path.exists", return_value=False), \
         patch("timelink.web.backend.timelink_app_wrapper.UserDatabase") as mock_db, \
         patch("argon2.hash", return_value="hashed"):

        app.run_users_db_setup()

        makedirs.assert_called_once_with("/tmp/sqlite_dir")
        mock_db.assert_called_once()
        assert isinstance(app.users_db, MagicMock)


def test_run_users_db_setup_postgres():
    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.users_db_type = "postgres"
    app.users_db_name = "pg_db"
    app.postgres_image = "pg_image"
    app.postgres_version = "15"

    with patch("timelink.web.backend.timelink_app_wrapper.UserDatabase") as mock_db, \
         patch("argon2.hash", return_value="hashed"):
        app.run_users_db_setup()
        mock_db.assert_called_once()
        assert isinstance(app.users_db, MagicMock)


def test_run_users_db_setup_invalid_type():

    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.users_db_name = "pg_db"
    app.users_db_type = "mongo"

    with pytest.raises(ValueError):
        app.run_users_db_setup()


def test_get_info_masks_token():
    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.timelink_home = "/home"
    app.kleio_server = MagicMock()
    app.kleio_server.get_url.return_value = "http://server"
    app.kleio_server.get_token.return_value = "1234567890"
    app.kleio_server.get_kleio_home.return_value = "/khome"
    app.kleio_server.container = MagicMock()
    app.kleio_server.container.labels = {"BUILD": "b", "VERSION": "v", "BUILD_DATE": "d"}

    info = app.get_info()
    assert info["Kleio server token"].endswith("...")


def test_load_config_for_project_list_guest_db():
    app = TimelinkWebApp.__new__(TimelinkWebApp)
    app.run_db_setup = MagicMock(return_value="DB")

    app.load_config_for_project_list([])

    assert app.database == "DB"
    assert app.current_project_name == "Demo project"


def test_load_config_for_project_list_select_project():

    app = TimelinkWebApp.__new__(TimelinkWebApp)
    project = MagicMock()
    project.name = "Proj"
    project.solr_core_name = "core1"
    app.run_db_setup = MagicMock(return_value="DB")
    app.solr_manager = MagicMock()

    app.load_config_for_project_list([project], select_project=project)

    assert app.database == "DB"
    assert app.current_project_name == "Proj"
    app.solr_manager.switch_active_core.assert_called_once_with("core1")
