import pytest
from timelink.web.pages.tables_page import TablesPage
from nicegui.testing import User
from unittest.mock import MagicMock
import sqlalchemy as sa
from sqlalchemy import Table, Column, String, MetaData, Integer


pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


@pytest.fixture
def fake_db_with_persons():
    metadata = sa.MetaData()
    persons = sa.Table(
        "persons", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String),
        sa.Column("sex", sa.String),
        sa.Column("obs", sa.String),
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt):
            return [{"id": "ana-id", "name": "Ana", "sex": "F", "obs": "ana obs"}]

    mock_db = MagicMock()
    mock_db.get_table.return_value = persons
    mock_db.session.return_value = FakeSession()
    return mock_db


@pytest.mark.asyncio
async def test_display_names_success(user: User, fake_db_with_persons, monkeypatch):
    """Check that _display_names renders a grid with expected columns and rows."""

    # Patch timelink_web_utils.add_description_column
    def fake_add_desc(df, database, id_column, session):
        df["description"] = "this is the file's description."
        return df
    monkeypatch.setattr("timelink.web.pages.tables_page.timelink_web_utils.add_description_column", fake_add_desc)

    # Capture aggrid calls
    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        return MagicMock(on=lambda *a, **k: None, classes=lambda x: None)
    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    page = TablesPage(database=fake_db_with_persons, kserver=None)
    page.register()

    # Call method
    await user.open("/tables/persons?value=Ana")

    await user.should_see("All entries with Ana")
    await user.should_see("Toggle Description")

    # Assertions
    opts = captured["options"]
    assert any(c["field"] == "id" for c in opts["columnDefs"])
    assert opts["rowData"][0]["name"] == "Ana"
    assert opts["rowData"][0]["description"] == "this is the file's description."


@pytest.mark.asyncio
@pytest.mark.parametrize("table_name, table_type, expected_return", [
    ("persons", "names", [
        {"name": "Antonio teste", "name_count": 4},
        {"name": "ana teste 2", "name_count": 2}
    ]
    ),
    ("attributes", "statistics", [
        {"name": "test_attribute", "attribute_count": 4},
        {"name": "test_attribute_2", "attribute_count": 2}
    ]
    ),
    ("relations", "statistics", [
        {"name": "test_relation", "attribute_count": 4},
        {"name": "test_relation_2", "attribute_count": 2}
    ]
    ),
    ("sources", "sources", [
        {"id": "test-sources"},
        {"id": "test-sources-2"}
    ]
    ), ])
async def test_display_tables(user: User, fake_db, monkeypatch, table_name, table_type, expected_return):

    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock
    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    class FakeSession:

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt):
            return expected_return

    fake_db.session.return_value = FakeSession()

    metadata = MetaData()
    if table_type == "names":
        table = Table(
            table_name,
            metadata,
            Column("name", String),
            Column("name_count", Integer)
        )
    elif table_type == "statistics":
        table = Table(
            table_name,
            metadata,
            Column("the_value", String),
            Column("attribute_count", Integer),
            Column("the_type", String)
        )
    else:  # sources
        table = Table(
            table_name,
            metadata,
            Column("id", String),
            Column("the_type", String),
            Column("the_date", String),
            Column("loc", String),
            Column("ref", String),
            Column("kleiofile", String),
            Column("replace", String),
            Column("obs", String)
        )

    fake_db.get_table.return_value = table

    monkeypatch.setattr(
        "timelink.web.pages.tables_page.timelink_web_utils.add_description_column",
        lambda df, database, id_column, session: df
    )

    page = TablesPage(database=fake_db, kserver=None)
    page.register()

    await user.open(f"/all_tables/{table_name}?display_type={table_type}&value=a")

    if table_type == "names":
        heading = "All names started with a"
    elif table_type == "statistics":
        heading = "Statistics for a"
    else:
        heading = "Sources in Database"

    await user.should_see(heading)

    # Verify aggrid options were captured
    opts = captured.get("options")
    assert opts is not None, "aggrid options were not captured"

    # Check column definitions based on table_type
    if table_type == "names":
        expected_columns = [
            {'headerName': 'Name', 'field': 'name'},
            {'headerName': 'Name Count', 'field': 'name_count', 'cellClass': 'highlight-cell'}
        ]
    elif table_type == "statistics":
        expected_columns = [
            {'headerName': 'Value', 'field': 'the_value'},
            {'headerName': f'{table_name.title()} Count',
             'field': 'attribute_count',
             'cellClass': 'highlight-cell'
             }
        ]
    else:
        expected_columns = [
            {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-cell'},
            {'headerName': 'THE_TYPE', 'field': 'the_type'},
            {'headerName': 'THE_DATE', 'field': 'the_date'},
            {'headerName': 'LOC', 'field': 'loc'},
            {'headerName': 'REF', 'field': 'ref'},
            {'headerName': 'KLEIOFILE', 'field': 'kleiofile'},
            {'headerName': 'REPLACES', 'field': 'replace'},
            {'headerName': 'OBS', 'field': 'obs', 'wrapText': True, 'autoHeight': True},
        ]

    assert opts['columnDefs'] == expected_columns, "Column definitions are incorrect"
    assert opts['rowData'] == expected_return, "Row data is incorrect"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "attr_type, attr_value, expected_rows",
    [
        ("test_type", "test_value", [
            {"id": "test-id", "name": "ana", "the_date": "2025-01-01"},
            {"id": "test-id-2", "name": "joao", "the_date": "2025-02-01"}
        ])
    ]
)
async def test_find_persons(user: User, fake_db, monkeypatch, attr_type, attr_value, expected_rows):

    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock
    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt):
            return expected_rows

    fake_db.session.return_value = FakeSession()

    metadata = MetaData()
    persons_table = Table(
        "persons",
        metadata,
        Column("id", Integer),
        Column("name", String)
    )
    attributes_table = Table(
        "attributes",
        metadata,
        Column("the_type", String),
        Column("the_value", String),
        Column("entity", Integer),
        Column("the_date", String)
    )
    fake_db.get_table.side_effect = lambda name: persons_table if name == "persons" else attributes_table

    # Create page and run method
    page = TablesPage(database=fake_db, kserver=None)
    page._find_persons(attr_type, attr_value)

    # Assertions
    opts = captured.get("options")
    assert opts is not None, "aggrid options were not captured"
    assert [col["field"] for col in opts["columnDefs"]] == ["id", "name", "the_date"]
    assert opts["rowData"] == expected_rows


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rel_type, rel_value, rel_id, is_from, expected_rows",
    [
        ("parentesco", None, None, True, [
            {
                "origin_id": "test-origin-id",
                "origin_name": "joao",
                "the_type": "parentesco",
                "the_value": "pai",
                "destination_name": "ana"}
        ]),
        ("parentesco", "mulher", "ana", True, [
            {
                "id": "test-id",
                "name": "ana",
                "the_type": "parentesco",
                "the_value": "mulher",
                "id_1": "test-id-1",
                "name_1": "joao",
                "relation_date": "2025-01-01"
            }
        ])
    ]
)
async def test_display_relations_view(user: User, fake_db, monkeypatch, rel_type, rel_value, rel_id, is_from, expected_rows):

    captured = {}

    def fake_aggrid(options):

        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)
    monkeypatch.setattr(
        "timelink.web.pages.tables_page.timelink_web_utils.add_description_column",
        lambda df, database, id_column, session: df
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, db):
            return expected_rows

    fake_db.session.return_value = FakeSession()

    metadata = MetaData()
    persons_table = Table("persons", metadata, Column("id", Integer), Column("name", String))
    fake_db.get_table.side_effect = lambda _: persons_table

    fake_db.views = {"nrelations": Table("nrelations", metadata,
                                         Column("origin_id", Integer),
                                         Column("origin_name", String),
                                         Column("relation_type", String),
                                         Column("relation_value", String),
                                         Column("destination_id", Integer),
                                         Column("destination_name", String),
                                         Column("relation_id", Integer),
                                         Column("relation_date", String)
                                         )}

    page = TablesPage(database=fake_db, kserver=None)

    page._display_relations_view(rel_type, rel_value=rel_value, rel_id=rel_id, is_from=is_from)

    opts = captured.get("options")
    assert opts is not None, "aggrid options were not captured"

    col_fields = [col["field"] for col in opts["columnDefs"]]
    if rel_id is None:
        assert "origin_name" in col_fields
        assert "relation_type" in col_fields
        assert "destination_name" in col_fields
    else:
        assert "id" in col_fields
        assert "name" in col_fields
        assert "id_1" in col_fields
        assert "name_1" in col_fields

    assert opts["rowData"] == expected_rows


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "attr_type, attr_value, expected_rows",
    [
        ("alcunha", None, [
            {
                "id": "test-id",
                "name": "ana",
                "the_type": "alcunha",
                "the_value": "anita",
                "the_date": "2025-01-01",
                "sex": "F",
                "pobs": None
            }
        ]),
        ("alcunha", "moco", [
            {
                "id": "test-id-2",
                "name": "joao",
                "the_type": "alcunha",
                "the_value": "moco",
                "the_date": "2025-01-01",
                "sex": "M",
                "pobs": None
            }
        ])
    ]
)
async def test_display_entity_with_attributes(user: User, fake_db, monkeypatch, attr_type, attr_value, expected_rows):

    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    class FakeSession:
        def __enter__(self):

            return self

        def __exit__(self, *_):

            return False

        def execute(self, _):

            return expected_rows

    fake_db.session.return_value = FakeSession()

    metadata = MetaData()
    fake_db.get_view.return_value = Table(
        "nattributes", metadata,
        Column("id", Integer),
        Column("name", String),
        Column("the_type", String),
        Column("the_date", String),
        Column("sex", String),
        Column("the_value", String),
        Column("pobs", String)
    )

    monkeypatch.setattr(
        "timelink.web.pages.tables_page.timelink_web_utils.add_description_column",
        lambda df, database, id_column, session: df
    )

    monkeypatch.setattr(
        "timelink.web.pages.tables_page.timelink_web_utils.pre_process_attributes_df",
        lambda df_to_process, attr_type: (df_to_process, [{"headerName": "ID", "field": "id"}])
    )

    page = TablesPage(database=fake_db, kserver=None)
    page.register()

    url = (
        f"/tables/attributes?attr_type={attr_type}&attr_value={attr_value}"
        if attr_value else f"/tables/attributes?attr_type={attr_type}"
    )

    await user.open(url)

    if not attr_value:
        await user.should_see(f"Entries with attribute {attr_type}")
    else:
        await user.should_see(f"Entries with attribute {attr_type} = {attr_value}")

    opts = captured.get("options")
    assert opts is not None, "aggrid options were not captured"

    # Check columnDefs and rowData
    assert opts["columnDefs"][0]["field"] == "id"
    assert opts["rowData"] == expected_rows


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "func_type, expected_rows",
    [
        ("mad", [
            {"id": "test-id", "name": "ana", "func": "mad", "act_date": "2025-01-01"}
        ]),
        ("ppad", [
            {"id": "test-id-2", "name": "joao", "func": "ppad", "act_date": "2025-01-02"}
        ])
    ]
)
async def test_display_functions_view(user: User, fake_db, monkeypatch, func_type, expected_rows):
    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    class FakeSession:
        def __enter__(self):

            return self

        def __exit__(self, *_):

            return False

        def execute(self, _):

            return expected_rows

    fake_db.session.return_value = FakeSession()

    metadata = MetaData()
    fake_db.views = {"nfunctions": Table(
        "nfunctions", metadata,
        Column("id", Integer),
        Column("name", String),
        Column("func", String),
        Column("act_date", String)
    )}

    page = TablesPage(database=fake_db, kserver=None)
    page.register()

    await user.open(f"/tables/functions?type={func_type}")
    await user.should_see(f"Entities with function of type {func_type}")

    opts = captured.get("options")
    assert opts is not None, "aggrid options were not captured"

    # Check columnDefs
    col_fields = [col["field"] for col in opts["columnDefs"]]
    for f in ["id", "name", "func", "act_date"]:
        assert f in col_fields

    # Check rowData
    assert opts["rowData"] == expected_rows


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "geoentity, expected_rows",
    [
        ("lisbon", [{"id": "test-geo-1", "name": "Lisbon", "the_type": "regiao", "obs": None, "description": ""}]),
        ("hunan", [{"id": "test-geo-2", "name": "Huwan", "the_type": "provincia", "obs": None, "description": ""}])
    ]
)
async def test_display_geoentities(user: User, fake_db, monkeypatch, geoentity, expected_rows):
    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    class FakeSession:
        def __enter__(self):

            return self

        def __exit__(self, *_):
            return False

        def execute(self, _):

            return expected_rows

    fake_db.session.return_value = FakeSession()

    # Mock get_table
    metadata = MetaData()
    fake_db.get_table.return_value = Table(
        "geoentity", metadata,
        Column("id", Integer),
        Column("name", String),
        Column("the_type", String),
        Column("obs", String),
        Column("description", String)
    )

    # Mock add_description_column
    monkeypatch.setattr(
        "timelink.web.pages.tables_page.timelink_web_utils.add_description_column",
        lambda df, database, id_column, session: df
    )

    page = TablesPage(database=fake_db, kserver=None)
    page.register()

    await user.open(f"/tables/geoentities?name={geoentity}")

    await user.should_see(f"All entries with {geoentity}")

    opts = captured.get("options")
    assert opts is not None, "aggrid options were not captured"

    # Check columnDefs
    col_fields = [col["field"] for col in opts["columnDefs"]]
    for f in ["id", "name", "the_type", "obs", "description"]:
        assert f in col_fields

    # Check rowData
    assert opts["rowData"] == expected_rows


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "act_type, expected_rows",
    [
        ("test act", [{"id": "deh-test-id", "the_type": "testact", "the_date": "2025-01-01", "loc": "", "ref": None, "obs": None}]),
    ]
)
async def test_display_acts(user: User, fake_db, monkeypatch, act_type, expected_rows):

    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    class FakeSession:
        def __enter__(self):

            return self

        def __exit__(self, *_):

            return False

        def execute(self, _):

            return expected_rows

    fake_db.session.return_value = FakeSession()

    # Mock get_table
    metadata = MetaData()
    fake_db.get_table.return_value = Table(
        "acts", metadata,
        Column("id", Integer),
        Column("the_type", String),
        Column("the_date", String),
        Column("loc", String),
        Column("ref", String),
        Column("obs", String)
    )

    # Mock add_description_column
    monkeypatch.setattr(
        "timelink.web.pages.tables_page.timelink_web_utils.add_description_column",
        lambda df, database, id_column, session: df
    )

    # Mock pre_process_attributes_df
    monkeypatch.setattr(
        "timelink.web.pages.tables_page.timelink_web_utils.pre_process_attributes_df",
        lambda df_to_process, attr_type: (df_to_process, [
            {"headerName": "ID", "field": "id"},
            {"headerName": "Type", "field": "the_type"},
            {"headerName": "Date", "field": "the_date"},
            {"headerName": "Location", "field": "loc"},
            {"headerName": "Reference", "field": "ref"},
            {"headerName": "Observations", "field": "obs"},
        ])
    )

    page = TablesPage(database=fake_db, kserver=None)
    page.register()

    await user.open(f"/tables/acts?name={act_type}")

    await user.should_see(f"Acts with type {act_type}")

    opts = captured.get("options")
    assert opts is not None, "aggrid options were not captured"

    col_fields = [col["field"] for col in opts["columnDefs"]]
    for f in ["id", "the_type", "the_date", "loc", "ref", "obs"]:
        assert f in col_fields

    assert opts["rowData"] == expected_rows


def test_redirect_to_view(monkeypatch):
    navigated = {}

    # Fake ui.navigate.to
    monkeypatch.setattr("timelink.web.pages.tables_page.ui.navigate.to", lambda url: navigated.setdefault("url", url))

    page = TablesPage(database=MagicMock(), kserver=None)

    # Test attribute table
    event = MagicMock()
    event.args = {"data": {"the_value": "val1"}}
    page._redirect_to_view(event, type="alcunha", table="attributes")
    assert navigated["url"] == "/tables/attributes?attr_type=alcunha&attr_value=val1"

    # Test persons table
    navigated.clear()
    page._redirect_to_view(event, type="Alice", table="persons")
    assert navigated["url"] == "/tables/persons?value=Alice"

    # Test relations table
    navigated.clear()
    page._redirect_to_view(event, type="marido", table="relations")
    assert navigated["url"] == "/tables/relations?type=marido&value=val1"


@pytest.mark.asyncio
async def test_search_database(user: User, fake_db, fake_kserver, monkeypatch):

    captured = {}

    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)

    # Mock navigate.to
    monkeypatch.setattr("timelink.web.pages.tables_page.ui.navigate.to", lambda url: captured.setdefault("navigated", url))

    # Mock database session and Entity
    class FakeEntity:
        id = "e1"
        pom_class = "person"

        def __str__(self):

            return "Test Entity"

    class FakeSession:

        def __enter__(self):

            return self

        def __exit__(self, *_):

            return False

        def execute(self, stmt):

            class Result:

                def scalars(self):

                    return self

                def all(self):

                    return [FakeEntity()]

            return Result()

        def add(self, obj):

            pass

        def commit(self):

            pass

    fake_db.session.return_value = FakeSession()

    page = TablesPage(database=fake_db, kserver=fake_kserver)
    page.register()

    await user.open('/search_tables?keywords=test&tables=Persons')

    opts = captured.get("options")
    assert opts is not None
    assert opts["rowData"][0]["entity"] == "e1"
    assert opts["rowData"][0]["entity_class"] == "person"
    assert "Test Entity" in opts["rowData"][0]["description"]


@pytest.mark.asyncio
async def test_display_sql_results(user: User, fake_db, fake_kserver, monkeypatch):
    captured = {}

    # Fake aggrid
    def fake_aggrid(options):
        captured["options"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.tables_page.ui.aggrid", fake_aggrid)
    monkeypatch.setattr("timelink.web.pages.tables_page.ui.navigate.to",
                        lambda url: captured.setdefault("navigated", url))

    # Fake SQL results
    class FakeResult:

        def fetchall(self):

            return [("test-id-1", "ana"), ("test-id-2", "joao")]

        def keys(self):

            return ["id", "name"]

    fake_db.query.return_value = FakeResult()

    # Fake session for Activity logging
    class FakeSession:
        def __enter__(self):

            return self

        def __exit__(self, *_):

            return False

        def add(self, obj):

            pass

        def commit(self):

            pass

    fake_db.session.return_value = FakeSession()

    page = TablesPage(database=fake_db, kserver=fake_kserver)
    page.register()

    # Directly call the coroutine
    await page._display_sql_results("SELECT * FROM entities LIMIT 50", "entities")

    opts = captured.get("options")
    assert opts is not None
    assert opts["rowData"][0]["id"] == "test-id-1"
    assert opts["rowData"][0]["name"] == "ana"
    assert opts["rowData"][1]["id"] == "test-id-2"
    assert opts["rowData"][1]["name"] == "joao"


def test_toggle_and_fit_columns():
    # Create a mock grid
    grid_mock = MagicMock()
    page = TablesPage(database=MagicMock(), kserver=MagicMock())

    # Initially show_desc should be False
    assert page.show_desc is False

    # Test _toggle_description
    page._toggle_description(grid_mock)

    # It should toggle show_desc to True
    assert page.show_desc is True

    # Check grid method calls
    grid_mock.run_grid_method.assert_any_call('setColumnVisible', 'description', True)
    grid_mock.run_grid_method.assert_any_call('autoSizeAllColumns')
    grid_mock.run_grid_method.assert_any_call('sizeColumnsToFit')

    # Test toggling back
    page._toggle_description(grid_mock)
    assert page.show_desc is False
    grid_mock.run_grid_method.assert_any_call('setColumnVisible', 'description', False)
