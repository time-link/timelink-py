"""Test the Timelink MCP server tools (docs/mcp-tools-draft.md).

Builds the reference database through the library (as test_040 does),
then exercises the MCP tools against it with the context configured to
attach to the session Kleio server — the same path a deployment takes
with TIMELINK_MCP_KLEIO_URL/TOKEN.
"""

import asyncio
from pathlib import Path

import pytest

from timelink.api.database import TimelinkDatabase
from timelink.mcp import McpSettings, configure, get_context, reset_context
from timelink.mcp.server import create_server, load_db_structure
from timelink.mcp.tools.attributes import (
    attribute_values,
    entity_attributes,
    entity_details,
    find_entities_by_attribute,
    find_persons_by_name,
)
from timelink.mcp.tools.discovery import db_info, db_schema, list_databases, list_projects
from timelink.mcp.tools.relations import entity_relations, find_relations
from timelink.mcp.tools.sources import (
    get_import_report,
    get_import_status,
    get_translation_report,
    import_from_sources,
    kleio_server_info,
    translate_sources,
    wait_for_translations,
)

TEST_DB = "test_mcp_db"
TEST_SOURCES = "projects/test-project/sources/reference_sources/pandas"

EXPECTED_TOOLS = {
    "list_projects",
    "list_databases",
    "db_info",
    "db_schema",
    "attribute_values",
    "find_entities_by_attribute",
    "find_persons_by_name",
    "entity_attributes",
    "entity_details",
    "find_relations",
    "entity_relations",
    "translate_sources",
    "wait_for_translations",
    "import_from_sources",
    "get_import_status",
    "get_import_report",
    "get_translation_report",
    "kleio_server_info",
}


@pytest.fixture(scope="module")
def mcp_setup(kleio_server, tmp_path_factory):
    """Create the reference database and point the MCP context at it.

    The database lives in a multi-project home layout
    (``projects/<project>/database/sqlite``), exercising the recursive
    search and project annotation of list_databases.
    """
    home = tmp_path_factory.mktemp("mcp_home")
    sqlite_dir = home / "projects" / "test-mcp" / "database" / "sqlite"
    sqlite_dir.mkdir(parents=True)

    # build the database with the library, attaching the session server
    database = TimelinkDatabase(TEST_DB, "sqlite", db_path=str(sqlite_dir), kleio_server=kleio_server)
    database.update_from_sources(TEST_SOURCES)

    configure(
        McpSettings(
            db_type="sqlite",
            home=str(home),
            kleio_url=kleio_server.get_url(),
            kleio_token=kleio_server.get_token(),
        )
    )
    yield {
        "db_name": TEST_DB,
        "project": "test-mcp",
        "home": str(home),
        "kleio_url": kleio_server.get_url(),
        "kleio_token": kleio_server.get_token(),
    }

    with database.session() as session:
        database.drop_db(session=session)
    reset_context()


# --------------------------------------------------------------- discovery


def test_list_projects(mcp_setup):
    result = list_projects()
    assert result["root"] == mcp_setup["home"]
    projects = {p["name"]: p for p in result["projects"]}
    assert set(projects) == {mcp_setup["project"]}
    project = projects[mcp_setup["project"]]
    assert project["has_database"] is True
    assert [d["name"] for d in project["databases"]] == [mcp_setup["db_name"]]
    assert project["inside"] is None
    assert result["project_count"] == 1
    assert result["databases_without_project"] == 0


def test_list_projects_finds_databaseless_projects(tmp_path):
    """Projects are detected structurally, not from database files: a
    project with sources and structures but no imported database must
    be listed, together with nested subprojects and loose source
    collections; home infrastructure (``system``) is not a project.

    Needs no Kleio server — plain directories and empty sqlite files.
    """
    home = tmp_path / "home"
    for sub in (
        "sources/legacy/database",  # legacy-MHK project, no db file
        "sources/legacy/structures",
        "sources/legacy/sources",
        "sources/bare/sources",  # sources never imported, no database dir
        "sources/bare/identifications",
        "sources/legacy/sources/submod/database",  # git-submodule subproject
        "sources/legacy/sources/submod/structures",
        "sources/not-a-project/misc",  # plain directory
        "projects/alpha/database/sqlite",
        "system/database/sqlite",
    ):
        (home / sub).mkdir(parents=True)
    (home / "projects" / "alpha" / "database" / "sqlite" / "shared.sqlite").touch()
    (home / "system" / "database" / "sqlite" / "users.sqlite").touch()

    from timelink.mcp.context import get_context

    restore = get_context().settings
    configure(McpSettings(db_type="sqlite", home=str(home)))
    try:
        result = list_projects()
        projects = {p["name"]: p for p in result["projects"]}
        assert {"legacy", "bare", "submod", "alpha"} <= set(projects)
        assert "system" not in projects
        assert "not-a-project" not in projects
        assert "sources" not in projects  # the container itself

        legacy = projects["legacy"]
        assert legacy["has_database"] is True
        assert legacy["has_structures"] is True
        assert legacy["databases"] == []  # the gap: project exists, no db yet

        assert projects["bare"]["has_database"] is False
        assert projects["bare"]["databases"] == []

        assert projects["submod"]["inside"] == "sources/legacy"
        assert projects["legacy"]["inside"] is None

        alpha = projects["alpha"]
        assert [d["name"] for d in alpha["databases"]] == ["shared"]

        # the system users db belongs to no project
        assert result["databases_without_project"] == 1

        # every project annotation of list_databases is a listed project
        databases = list_databases()
        names = set(projects)
        assert all(d["project"] in names for d in databases["databases"] if d["project"] is not None)
        assert next(d for d in databases["databases"] if d["name"] == "users")["project"] is None
        assert next(d for d in databases["databases"] if d["name"] == "shared")["project"] == "alpha"
    finally:
        configure(restore)


def test_list_projects_single_project_home(tmp_path):
    """When the home root itself has the project layout, it is listed
    as the (only) project, marked ``is_home``."""
    home = tmp_path / "solo"
    for sub in ("database/sqlite", "sources", "structures"):
        (home / sub).mkdir(parents=True)
    (home / "database" / "sqlite" / "one.sqlite").touch()

    from timelink.mcp.context import get_context

    restore = get_context().settings
    configure(McpSettings(db_type="sqlite", home=str(home)))
    try:
        result = list_projects()
        assert result["project_count"] == 1
        project = result["projects"][0]
        assert project["is_home"] is True
        assert project["name"] == home.name
        assert [d["name"] for d in project["databases"]] == ["one"]
        # annotation agrees: the db belongs to the home project
        entry = next(d for d in list_databases()["databases"] if d["name"] == "one")
        assert entry["project"] == home.name
    finally:
        configure(restore)


def test_list_databases(mcp_setup):
    result = list_databases()
    names = [d["name"] for d in result["databases"]]
    assert mcp_setup["db_name"] in names
    assert result["default_db_type"] == "sqlite"
    entry = next(d for d in result["databases"] if d["name"] == mcp_setup["db_name"])
    assert entry["db_type"] == "sqlite"
    assert entry["project"] == mcp_setup["project"]
    assert entry["path"].endswith(".sqlite")
    assert result["sqlite_root"] == mcp_setup["home"]


def test_get_unknown_database_fails_loudly(mcp_setup):
    with pytest.raises(ValueError, match="not found"):
        db_info("no_such_database")


def test_db_info(mcp_setup):
    info = db_info(mcp_setup["db_name"])
    assert info["database"] == mcp_setup["db_name"]
    persons = next(t for t in info["tables"] if t["name"] == "persons")
    assert persons["rows"] > 0
    assert "person" in info["entity_classes"]
    assert "nrelations" in info["views"]


def test_db_schema_mapping(mcp_setup):
    schema = db_schema(mcp_setup["db_name"])
    mapping = {m["group"]: m for m in schema["group_model_mapping"]}
    # groups are Kleio groups (e.g. n, bap, ls) mapping to ORM models
    assert any(m["model"] == "Person" and m["table"] == "persons" for m in mapping.values())


def test_db_schema_describes_model(mcp_setup):
    schema = db_schema(mcp_setup["db_name"], model_or_table="person")
    names = [c["name"] for c in schema["columns"]]
    assert "name" in names


def test_db_schema_unknown_target_lists_available(mcp_setup):
    with pytest.raises(ValueError, match="not a known entity class"):
        db_schema(mcp_setup["db_name"], model_or_table="nope")


# -------------------------------------------------------------- attributes


def test_attribute_values(mcp_setup):
    result = attribute_values(mcp_setup["db_name"], the_type="residencia")
    assert result["row_count"] > 0
    assert result["total_count"] >= result["row_count"]
    assert isinstance(result["rows"][0]["value"], str)


def test_attribute_values_paging(mcp_setup):
    full = attribute_values(mcp_setup["db_name"], the_type="residencia")
    page = attribute_values(mcp_setup["db_name"], the_type="residencia", row_limit=2)
    assert page["row_count"] <= 2
    if full["total_count"] > 2:
        assert page["truncated"] is True
        assert page["next_offset"] == 2
        page2 = attribute_values(mcp_setup["db_name"], the_type="residencia", row_limit=2, offset=2)
        assert page2["rows"][0] != page["rows"][0]


def test_find_entities_by_attribute(mcp_setup):
    result = find_entities_by_attribute(mcp_setup["db_name"], the_type="residencia", the_value="alencarce%")
    assert result["row_count"] > 0
    row = result["rows"][0]
    assert row["id"]
    assert "residencia" in row  # the attribute value column
    assert any(r.get("name") for r in result["rows"])


def test_find_entities_by_attribute_dates(mcp_setup):
    result = find_entities_by_attribute(mcp_setup["db_name"], the_type="residencia", dates_in=["16850101", "16851231"])
    assert result["total_count"] > 0


def test_find_persons_by_name(mcp_setup):
    exact = find_persons_by_name(mcp_setup["db_name"], name="%matias%")
    assert exact["row_count"] > 0
    similar = find_persons_by_name(mcp_setup["db_name"], name="matias carvalho", similar=True)
    assert similar["row_count"] > 0


def test_entity_attributes(mcp_setup):
    search = find_entities_by_attribute(mcp_setup["db_name"], the_type="residencia")
    eid = search["rows"][0]["id"]
    result = entity_attributes(mcp_setup["db_name"], ids=[eid])
    assert result["row_count"] > 0
    types = {r["the_type"] for r in result["rows"]}
    assert "residencia" in types


def test_entity_details(mcp_setup):
    search = find_entities_by_attribute(mcp_setup["db_name"], the_type="residencia")
    eid = search["rows"][0]["id"]
    result = entity_details(mcp_setup["db_name"], ids=[eid])
    detail = result["details"][0]
    assert detail["id"] == eid
    assert detail["entity_class"] == "person"
    assert eid in detail["text"]  # kleio rendering contains the id


def test_entity_details_rejects_too_many_ids(mcp_setup):
    with pytest.raises(ValueError, match="between 1 and 5"):
        entity_details(mcp_setup["db_name"], ids=[str(i) for i in range(6)])


# --------------------------------------------------------------- relations


def test_find_relations(mcp_setup):
    result = find_relations(mcp_setup["db_name"], row_limit=5)
    assert result["row_count"] > 0
    row = result["rows"][0]
    for key in (
        "relation_id",
        "origin_id",
        "origin_name",
        "destination_id",
        "destination_name",
        "relation_type",
    ):
        assert key in row


def test_find_relations_by_type_and_dates(mcp_setup):
    # SQL-paged results have no total_count; a wide-open date filter must
    # not lose rows relative to the unfiltered query at the same page size
    wide = find_relations(mcp_setup["db_name"], relation_type="%", dates_in=["00000000", "99999999"])
    plain = find_relations(mcp_setup["db_name"])
    assert wide["row_count"] == plain["row_count"]
    assert wide["truncated"] == plain["truncated"]


def test_entity_relations(mcp_setup):
    someone = find_relations(mcp_setup["db_name"], row_limit=1)["rows"][0]["origin_id"]
    result = entity_relations(mcp_setup["db_name"], id=someone)
    assert result["row_count"] > 0
    directions = {r["direction"] for r in result["rows"]}
    assert directions <= {"in", "out"}
    assert all(r["other_id"] != someone for r in result["rows"])
    outgoing = entity_relations(mcp_setup["db_name"], id=someone, direction="out")
    assert all(r["direction"] == "out" for r in outgoing["rows"])


def test_entity_relations_bad_direction(mcp_setup):
    with pytest.raises(ValueError, match="direction"):
        entity_relations(mcp_setup["db_name"], id="x", direction="sideways")


# ------------------------------------------------------- sources / updates


def test_kleio_server_info(mcp_setup):
    info = kleio_server_info()
    assert info["attached"] is True
    assert info["url"].startswith("http")
    assert "token" not in str(info)


def test_get_import_status(mcp_setup):
    # explicit path: the fixture database lives in a synthetic project the
    # Kleio server does not serve, so point at the reference sources
    result = get_import_status(mcp_setup["db_name"], path=TEST_SOURCES)
    assert result["count"] > 0
    statuses = {f["import_status"] for f in result["files"]}
    # the fixture imports everything; the reference set itself contains a
    # file that imports with errors, so I (imported) and possibly E are set
    assert "I" in statuses
    assert statuses <= {"I", "E", "W"}
    imported = get_import_status(mcp_setup["db_name"], path=TEST_SOURCES, status="I")
    assert imported["count"] > 0


def test_update_pipeline_with_nothing_stale(mcp_setup):
    # everything was translated and imported by the fixture: the pipeline
    # must run through cleanly without re-doing work
    translated = translate_sources(mcp_setup["db_name"], path=TEST_SOURCES)
    assert translated["count"] == 0
    assert translated["source_path"] == TEST_SOURCES

    waited = wait_for_translations(mcp_setup["db_name"])
    assert waited["still_pending"] == []
    assert "note" in waited  # nothing was requested

    imported = import_from_sources(mcp_setup["db_name"], path=TEST_SOURCES)
    assert imported["counts"]["candidates"] > 0
    assert imported["counts"]["imported"] == 0
    assert imported["skipped"] == []


def test_get_translation_report(mcp_setup):
    files = get_import_status(mcp_setup["db_name"], path=TEST_SOURCES)["files"]
    with_report = next(f for f in files if f["rpt_url"])
    result = get_translation_report(mcp_setup["db_name"], with_report["path"])
    assert result["file"] == with_report["path"]
    assert result["report"]


def test_get_import_report(mcp_setup):
    files = get_import_status(mcp_setup["db_name"], path=TEST_SOURCES)["files"]
    result = get_import_report(mcp_setup["db_name"], files[0]["name"])
    assert isinstance(result["report"], str)


def test_default_path_scopes_to_database_project(kleio_server):
    """With no path argument, source tools default to the database's own
    project sources (``projects/<project>/sources``) in a multi-project
    home — not to the whole Kleio server."""
    from tests import KLEIO_HOME

    database = None
    sqlite_dir = KLEIO_HOME / "projects" / "test-project" / "database" / "sqlite"
    try:
        database = TimelinkDatabase("test-mcp-defaults", "sqlite", db_path=str(sqlite_dir), kleio_server=kleio_server)
        restore = get_context().settings
        configure(
            McpSettings(
                db_type="sqlite",
                home=str(KLEIO_HOME),
                kleio_url=kleio_server.get_url(),
                kleio_token=kleio_server.get_token(),
            )
        )
        try:
            status = get_import_status("test-mcp-defaults")
            assert status["count"] > 0
            assert all(f["path"].startswith("projects/test-project/") for f in status["files"])
            # fresh database: everything is new, nothing imported
            assert {f["import_status"] for f in status["files"]} == {"N"}
        finally:
            configure(restore)
    finally:
        if database is not None:
            with database.session() as session:
                database.drop_db(session=session)


# ------------------------------------------------------ server and paging


def test_max_rows_cap(mcp_setup):
    # reconfigure with a tiny cap; tools must clamp even a huge row_limit
    configure(
        McpSettings(
            db_type="sqlite",
            home=mcp_setup["home"],
            kleio_url=mcp_setup["kleio_url"],
            kleio_token=mcp_setup["kleio_token"],
            max_rows=2,
        )
    )
    try:
        result = attribute_values(mcp_setup["db_name"], the_type="residencia", row_limit=1000)
        assert result["row_count"] <= 2
        assert result["truncated"] is True
    finally:
        configure(
            McpSettings(
                db_type="sqlite",
                home=mcp_setup["home"],
                kleio_url=mcp_setup["kleio_url"],
                kleio_token=mcp_setup["kleio_token"],
            )
        )


def test_server_registers_expected_tools():
    # registration needs no database; the context builds from env defaults
    reset_context()
    try:
        server = create_server()
        tools = asyncio.run(server.list_tools())
        assert {t.name for t in tools} == EXPECTED_TOOLS
    finally:
        reset_context()


def test_schema_resource_content():
    text = load_db_structure()
    assert "Timelink database structure" in text


def test_tool_errors_surface_guidance(mcp_setup):
    """The registration wrapper converts exceptions to ToolError so the
    guidance text (candidates, available names) reaches MCP clients on
    both mcp 1.x and 2.x."""
    from timelink.mcp.errors import ToolError, tool_errors

    def raises_value_error():
        raise ValueError("ambiguous: alpha/shared, beta/shared")

    with pytest.raises(ToolError, match="ambiguous: alpha/shared, beta/shared"):
        tool_errors(raises_value_error)()

    with pytest.raises(ToolError, match="not found"):
        tool_errors(db_info)("no_such_database")

    def crashes():
        return 1 / 0

    with pytest.raises(ToolError, match="ZeroDivisionError"):
        tool_errors(crashes)()


def test_settings_from_env():
    settings = McpSettings.from_env(
        {
            "TIMELINK_MCP_DB_TYPE": "postgres",
            "TIMELINK_MCP_MAX_ROWS": "10",
            "TIMELINK_MCP_HOME": "/tmp/home",
        }
    )
    assert settings.db_type == "postgres"
    assert settings.max_rows == 10
    assert settings.resolved_home() == Path("/tmp/home")
    # the sqlite search root defaults to the home and can be overridden
    assert settings.resolved_sqlite_root() == Path("/tmp/home")
    assert McpSettings.from_env(
        {"TIMELINK_MCP_HOME": "/tmp/home", "TIMELINK_MCP_SQLITE_ROOT": "/tmp/elsewhere"}
    ).resolved_sqlite_root() == Path("/tmp/elsewhere")
    # with nothing configured, both fall back to ~/.timelink
    assert McpSettings.from_env({}).resolved_sqlite_root() == McpSettings.from_env({}).resolved_home()

    with pytest.raises(ValueError, match="db_type"):
        McpSettings.from_env({"TIMELINK_MCP_DB_TYPE": "mysql"})


# --------------------------------------------------- multiproject layouts


def test_multiproject_name_collisions(tmp_path):
    """Two projects with the same database name: annotate, disambiguate.

    Needs no Kleio server — empty databases created directly through the
    library, as the test_010 fixtures do.
    """
    home = tmp_path / "home"
    for project in ("alpha", "beta"):
        sqlite_dir = home / "projects" / project / "database" / "sqlite"
        TimelinkDatabase("shared", "sqlite", db_path=str(sqlite_dir))
    system_dir = home / "system" / "database" / "sqlite"
    TimelinkDatabase("users", "sqlite", db_path=str(system_dir))

    from timelink.mcp.context import get_context

    restore = get_context().settings
    configure(McpSettings(db_type="sqlite", home=str(home)))
    try:
        result = list_databases()
        by_project = {d["project"]: d for d in result["databases"]}
        assert set(by_project) == {"alpha", "beta", None}
        assert all(d["name"] == "shared" for p, d in by_project.items() if p in ("alpha", "beta"))

        # bare ambiguous name fails with both candidates listed
        with pytest.raises(ValueError, match="ambiguous.*alpha/shared.*beta/shared"):
            db_info("shared")

        # qualified project/name connects to the right file
        alpha = db_info("alpha/shared")
        assert alpha["db_type"] == "sqlite"
        assert any(t["name"] == "persons" for t in alpha["tables"])
        beta_path = home / "projects" / "beta" / "database" / "sqlite" / "shared.sqlite"
        assert beta_path.is_file()
        # relative and absolute path forms also connect
        db_info("projects/beta/database/sqlite/shared.sqlite")
        db_info(str(beta_path))
        # unambiguous name connects directly
        db_info("users")
    finally:
        configure(restore)
