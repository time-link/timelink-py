import pytest
from unittest.mock import MagicMock
from nicegui import ui
from nicegui.testing import User
from timelink.web import timelink_web_utils
from timelink.web.pages import status_page
import pandas as pd
from sqlalchemy import column, table
from timelink.web.timelink_web_utils import setup_pages_and_database

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


def test_run_imports_sync(capsys, fake_timelink_app):

    timelink_web_utils.run_imports_sync(fake_timelink_app.database)

    fake_timelink_app.database.update_from_sources.assert_called_once_with(match_path=True)

    out, _ = capsys.readouterr()
    assert "Attempting to update database from sources..." in out
    assert "Database successfully updated!" in out


@pytest.mark.asyncio
async def test_show_table(user: User, fake_timelink_app, fake_user) -> None:

    fake_timelink_app.database.table_row_count.return_value = [("attributes", 10), ("entities", 5)]

    status_page.StatusPage(fake_timelink_app, MagicMock())

    await user.open("/status")
    user.find("Database Status").click()

    timelink_web_utils.show_table(fake_timelink_app.database)

    table = user.find(ui.table).elements.pop()
    expected_columns = [
        {'name': 'Table', 'label': 'Table', 'field': 'Table'},
        {'name': 'Row Count', 'label': 'Row Count', 'field': 'Row Count'}
    ]

    expected_rows = [
        {'Table': 'attributes', 'Row Count': 10},
        {'Table': 'entities', 'Row Count': 5}
    ]

    assert table.columns == expected_columns
    assert table.rows == expected_rows


@pytest.mark.asyncio
async def test_show_kleio_info(user: User, fake_timelink_app, fake_user) -> None:

    fake_timelink_app.kleio_server.url = "http://fake.kleio.server:8000"
    fake_timelink_app.kleio_server.kleio_home = "/fake/kleio/home"

    status_page.StatusPage(fake_timelink_app, MagicMock())

    await user.open("/status")
    user.find("Timelink Server Status").click()

    timelink_web_utils.show_kleio_info(fake_timelink_app.kleio_server)

    markdown = user.find(ui.markdown).elements.pop()

    expected_markdown = f"""
        - **Kleio URL:** {fake_timelink_app.kleio_server.url}
        - **Kleio Home:** {fake_timelink_app.kleio_server.kleio_home}
        """

    assert markdown.content.strip() == expected_markdown.strip()

    assert user.find("Kleio Server Overview")
    assert user.find("Close")


def test_load_data_functions_query(fake_timelink_app):
    """Test load_data with a 'functions' query."""

    mock_results = [('name', 5), ('ativa', 12)]
    mock_df = pd.DataFrame(mock_results, columns=['the_value', 'count'])
    fake_timelink_app.database.session.return_value.__enter__.return_value.execute.return_value = mock_df

    mock_table = MagicMock()
    mock_table.c.the_value = column('the_value')
    mock_table.c.the_type = column('the_type')
    fake_timelink_app.database.get_table.return_value = mock_table

    df = timelink_web_utils.load_data("functions", fake_timelink_app.database)

    fake_timelink_app.database.get_table.assert_called_once_with("relations")

    assert isinstance(df, pd.DataFrame)

    expected_df = pd.DataFrame(mock_results, columns=['the_value', 'count'])
    pd.testing.assert_frame_equal(df, expected_df)


@pytest.mark.parametrize("query_type", ["relations", "attributes"])
def test_load_data_general_query(fake_timelink_app, query_type):
    """Test load_data with relations/attributes queries."""

    mock_results = [('typeA', 10, 3), ('typeB', 20, 5)]
    mock_df = pd.DataFrame(mock_results, columns=['the_type', 'count', 'distinct_value'])
    fake_timelink_app.database.session.return_value.__enter__.return_value.execute.return_value = mock_df

    mock_table = MagicMock()
    mock_table.c.the_type = column('the_type')
    mock_table.c.the_value = column('the_value')
    fake_timelink_app.database.get_table.return_value = mock_table

    df = timelink_web_utils.load_data(query_type, fake_timelink_app.database)

    fake_timelink_app.database.get_table.assert_called_once_with(query_type)

    assert isinstance(df, pd.DataFrame)

    expected_df = pd.DataFrame(mock_results, columns=['the_type', 'count', 'distinct_value'])
    pd.testing.assert_frame_equal(df, expected_df)


@pytest.mark.parametrize("query_type", ["relations", "attributes", "functions"])
def test_load_data_exception_handling(fake_timelink_app, capsys, query_type):
    """Test that load_data correctly handles exceptions."""

    fake_table = table(
        query_type,
        column("the_value"),
        column("the_type"),
    )
    fake_timelink_app.database.get_table.return_value = fake_table
    fake_exception = ValueError("Mock database error")
    fake_timelink_app.database.session.return_value.__enter__.return_value.execute.side_effect = fake_exception

    df = timelink_web_utils.load_data(query_type, fake_timelink_app.database)

    assert df is None

    captured = capsys.readouterr()

    expected_tablename = query_type if query_type != "functions" else "relations"
    expected_message = f"Couldn't load info from table '{expected_tablename}': {fake_exception}"

    assert expected_message in captured.out


def test_add_description_column(fake_timelink_app):
    """Test if a 'description' column is added to the DataFrame with correct values."""

    fake_session = MagicMock()

    fake_timelink_app.database.get_entity.side_effect = ["description_for_A", "description_for_B", "description_for_C"]

    test_data = {'id': ['A', 'B', 'C'], 'value': [1, 2, 3]}
    df = pd.DataFrame(test_data)

    result_df = timelink_web_utils.add_description_column(df, fake_timelink_app.database, 'id', fake_session)

    assert isinstance(result_df, pd.DataFrame)
    assert "description" in result_df.columns

    fake_timelink_app.database.get_entity.assert_any_call('A', session=fake_session)
    fake_timelink_app.database.get_entity.assert_any_call('B', session=fake_session)
    fake_timelink_app.database.get_entity.assert_any_call('C', session=fake_session)

    assert fake_timelink_app.database.get_entity.call_count == len(df)

    expected_descriptions = ["description_for_A", "description_for_B", "description_for_C"]
    pd.testing.assert_series_equal(result_df["description"], pd.Series(expected_descriptions, name="description"))


def test_pre_process_attributes_df():
    """Test if a dataframe to retrieved with entities_with_attributes is properly processed to be displayed."""

    df = pd.DataFrame({
        "id": [1, 2],
        "description": ["desc1", "desc2"],
        "attr_extra_info": ["x", "y"],
        "some.attr": ["a", "b"],
        "my_attr_value": [10, 20],
    })

    processed_df, col_defs = timelink_web_utils.pre_process_attributes_df(df, "my_attr")

    # test if extra_info columns was dropped
    assert "attr_extra_info" not in processed_df.columns

    # test "." replacement with "_"
    assert "some_attr" in processed_df.columns

    # test column defs length matches df columns
    assert len(col_defs) == len(processed_df.columns)

    # test if "id" column gets highlight class
    id_col = next(c for c in col_defs if c["field"] == "id")
    assert id_col["cellClass"] == "highlight-cell"

    # test if "description" column gets extra props
    desc_col = next(c for c in col_defs if c["field"] == "description")
    assert desc_col["wrapText"] is True
    assert desc_col["hide"] is True
    assert desc_col["minWidth"] == 300

    # test if headerName is correctly parsed
    my_val_col = next(c for c in col_defs if c["field"] == "my_attr_value")
    assert my_val_col["headerName"] == "VALUE"


def test_build_expected_col_list():
    """Test function that builds expected columns to be displayed in an AG Grid"""

    df = pd.DataFrame({
        "id": [1, 2],
        "first_name": ["Alice", "Bob"],
        "age": [30, 40],
    })

    col_defs = timelink_web_utils.build_expected_col_list(df, id_field="id")

    assert len(col_defs) == len(df.columns)

    assert any(c["headerName"] == "First Name" for c in col_defs)
    assert any(c["headerName"] == "Age" for c in col_defs)

    id_col = next(c for c in col_defs if c["field"] == "id")
    assert id_col["cellClass"] == "highlight-cell"


def test_parse_entity_details(monkeypatch):
    """Test if parse_entity_details returns correct dictionaries."""

    rel_in = MagicMock(the_date="16200101")
    rel_out = MagicMock(the_date="16000101")
    attr = MagicMock(the_date="15400101")

    fake_entity = MagicMock()
    fake_entity.rels_in = [rel_in]
    fake_entity.rels_out = [rel_out]
    fake_entity.attributes = [attr]

    def fake_dated_bio():
        return {
            "16200101": [rel_in],
            "16000101": [rel_out],
            "15400101": [attr],
        }
    fake_entity.dated_bio.side_effect = fake_dated_bio

    fake_schema = MagicMock()
    fake_schema.model_dump.return_value = {
        "rels_in": [{"id": 1, "type": "parent"}],
        "rels_out": [{"id": 2, "type": "child"}],
    }

    monkeypatch.setattr(
        "timelink.web.timelink_web_utils.EntityAttrRelSchema.model_validate",
        lambda e: fake_schema,
    )

    bio, rels_in, rels_out = timelink_web_utils.parse_entity_details(fake_entity)

    assert "15400101" in bio
    assert "16000101" in bio
    assert "16200101" in bio
    assert bio["16200101"][0] is rel_in
    assert bio["16000101"][0] is rel_out
    assert bio["15400101"][0] is attr

    assert rels_in == [{"id": 1, "type": "parent"}]
    assert rels_out == [{"id": 2, "type": "child"}]


def test_format_obs():
    """Test if format_obs returns properly indented observation HTML"""

    obs = "Test observation"
    level = 2
    result = timelink_web_utils.format_obs(obs, level)
    expected_indent = (level + 1) * 6

    assert f'padding-left:{expected_indent}ch' in result
    assert "obs" in result
    assert obs in result


def test_highlight_link():
    """Test if highlight_link returns HTML span with correct path and text."""

    path = "/some/path"
    text = "some text goes here"
    result = timelink_web_utils.highlight_link(path, text)

    assert path in result
    assert text in result
    assert "highlight-cell" in result
    assert "onclick" in result


def test_collect_all_ids_sync(monkeypatch, fake_timelink_app):
    """Test if collect_all_ids_sync correctly collects child entities with levels and extra_attrs."""

    fake_session = MagicMock()
    fake_timelink_app.database.session.return_value.__enter__.return_value = fake_session

    parent = MagicMock()
    parent.inside = "parent_inside"
    parent_contains_id = 123
    parent_dict = {
        "contains": [{"id": parent_contains_id}],
        "extra_info": {"some_attr": {"kleio_element_class": "my_class"}}
    }

    child = MagicMock()
    child.inside = "child_inside"
    child.some_attr = "child_value"
    child_dict = {"contains": [], "extra_info": {"some_attr": {"kleio_element_class": "my_class"}}}

    # patch get_entity to return child when called with the parent's child ID
    fake_timelink_app.database.get_entity.side_effect = (
        lambda entity_id, session=None: child if entity_id == parent_contains_id else None
    )

    monkeypatch.setattr(
        "timelink.web.timelink_web_utils.EntityAttrRelSchema.model_validate",
        lambda e: MagicMock(model_dump=MagicMock(return_value=parent_dict if e == parent else child_dict))
    )

    result = timelink_web_utils.collect_all_ids_sync(fake_timelink_app.database, parent)

    # checks
    assert len(result) == 1
    r = result[0]
    assert r["level"] == 1
    assert r["extra_attrs"]["my_class"] == "child_value"
    assert r["extra_attrs"]["inside"] == "child_inside"


def test_get_entity_count_table(fake_timelink_app):
    """Test if get_entity_count_table returns a DataFrame with a count of each entity class."""

    fake_session = MagicMock()
    fake_timelink_app.database.session.return_value.__enter__.return_value = fake_session

    fake_session.execute.return_value = [("person", 3), ("attribute", 5)]

    df = timelink_web_utils.get_entity_count_table(fake_timelink_app.database)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["pom_class", "count"]
    assert df.shape[0] == 2
    assert df.iloc[0]["pom_class"] == "person"
    assert df.iloc[0]["count"] == 3


def test_get_recent_sources(fake_timelink_app):
    """Test if get_recent_sources returns a DataFrame with recent sources."""

    fake_timelink_app.database.get_imported_files.return_value = [
        {"file": "file1.txt", "imported": pd.Timestamp("2023-01-01")},
        {"file": "file2.txt", "imported": None},
    ]

    df = timelink_web_utils.get_recent_sources(fake_timelink_app.database)

    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {"file", "imported"}

    # NaT should be replaced by Timestamp(0)
    assert df["imported"].iloc[1] == "1970-01-01"

    assert all(isinstance(v, str) for v in df["imported"])


@pytest.mark.parametrize("searched_only", [True, False])
def test_get_recent_history(fake_timelink_app, searched_only):
    """Test if get_recent_history returns a recent activity DataFrame with correct columns and data."""

    fake_session = MagicMock()
    fake_timelink_app.database.session.return_value.__enter__.return_value = fake_session

    def execute_side_effect(*args, **kwargs):

        if searched_only:
            rows = [
                (1, "EntityA", "searched", "desc1", pd.Timestamp("2023-01-01")),
            ]
        else:
            rows = [
                (2, "EntityB", "viewed", "desc2", pd.Timestamp("2023-02-01")),
            ]
        fake_result = MagicMock()
        fake_result.fetchall.return_value = rows
        fake_result.keys.return_value = ["entity_id", "entity_type", "activity_type", "desc", "when"]
        return fake_result

    fake_session.execute.side_effect = execute_side_effect

    df = timelink_web_utils.get_recent_history(fake_timelink_app.database, searched_only=searched_only)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["entity_id", "entity_type", "activity_type", "desc", "when"]

    if searched_only:
        assert df.iloc[0]["activity_type"] == "searched"
        assert df.shape[0] == 1
    else:
        assert df.iloc[0]["activity_type"] == "viewed"
        assert df.shape[0] == 1

    assert isinstance(df.iloc[0]["when"], str)


@pytest.mark.asyncio
async def test_setup_pages_and_database(fake_timelink_app, monkeypatch):
    # Add users_db mock
    fake_timelink_app.users_db = MagicMock()
    fake_timelink_app.users_db.engine = "fake_engine"

    # Create some fake projects
    fake_project1 = MagicMock()
    fake_project1.name = "Project1"
    fake_project2 = MagicMock()
    fake_project2.name = "Project2"
    project_list = [fake_project1, fake_project2]

    # Patch the Admin class so we can track instantiation
    admin_mock = MagicMock()
    monkeypatch.setattr("timelink.web.timelink_web_utils.Admin", lambda **kwargs: admin_mock)

    # Patch ModelView and Link
    monkeypatch.setattr("timelink.web.timelink_web_utils.ModelView", lambda model, **kwargs: MagicMock())
    monkeypatch.setattr("timelink.web.timelink_web_utils.Link", lambda **kwargs: MagicMock())

    # Prepare page mocks
    page_paths = [
        "explore_page.ExplorePage",
        "display_id_page.DisplayIDPage",
        "tables_page.TablesPage",
        "overview_page.Overview",
        "people_page.PeopleGroupsNetworks",
        "families_page.Families",
        "calendar_page.CalendarPage",
        "linking_page.Linking",
        "sources_page.Sources",
        "status_page.StatusPage",
        "search_page.Search",
    ]

    page_mocks = {path: MagicMock() for path in page_paths}
    for path, mock in page_mocks.items():
        monkeypatch.setattr(f"timelink.web.pages.{path}", mock)

    # Call function
    setup_pages_and_database(fake_timelink_app, project_list, active_project=fake_project1)

    # Assertions
    assert fake_timelink_app.projects_loaded is True
    fake_timelink_app.load_config_for_project_list.assert_called_with(project_list, fake_project1)

    # Check that all pages were instantiated
    for mock in page_mocks.values():
        mock.assert_called()

    # Check that admin app mounted
    admin_mock.mount_to.assert_called()
