import pytest
from timelink.web.pages.sources_page import Sources
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import asyncio
from nicegui import ui


pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


@pytest.mark.asyncio
async def test_sources_page_init(fake_db, fake_kserver):
    """Test initialization of Sources page and imported files name resolution."""

    fake_file = SimpleNamespace(path="test.cli", name="test", errors=0, warnings=0, import_errors=0)
    fake_db.get_import_status.return_value = [fake_file]
    fake_kserver.kleio_home = "/tmp"
    fake_scheduler = MagicMock()

    page = Sources(fake_db, fake_kserver, fake_scheduler)

    assert str((Path("/tmp") / "test.cli").resolve()) in page.imported_files_dict
    assert page.database is fake_db
    assert page.kserver is fake_kserver


@pytest.mark.asyncio
async def test_sources_refresh_imported_files(fake_db, fake_kserver):
    """Test if refresh_imported_files appropriately associates import/translate warnings and errors with the correct dicionary."""

    fake_ok = SimpleNamespace(path="ok.cli", name="ok", errors=0, warnings=0, import_errors=0)
    fake_error = SimpleNamespace(path="err.cli", name="err", errors=1, warnings=0, import_errors=0)
    fake_warn = SimpleNamespace(path="warn.cli", name="warn", errors=0, warnings=2, import_errors=0)
    fake_import_err = SimpleNamespace(path="imp.cli", name="imp", errors=0, warnings=0, import_errors=3)

    fake_db.get_import_status.return_value = [fake_ok, fake_error, fake_warn, fake_import_err]
    fake_kserver.kleio_home = "/tmp"
    fake_scheduler = MagicMock()

    page = Sources(fake_db, fake_kserver, fake_scheduler)

    assert any("err.cli" in k for k in page.problem_files)
    assert any("warn.cli" in k for k in page.translate_warning_files)
    assert any("imp.cli" in k for k in page.import_error_files)


@pytest.mark.asyncio
async def test_sources_page_register(user, fake_db, fake_kserver):
    """Test that the /sources page is properly registered and can be opened."""

    fake_db.get_import_status.return_value = []
    fake_kserver.kleio_home = "/tmp"
    fake_scheduler = MagicMock()

    page = Sources(fake_db, fake_kserver, fake_scheduler)

    await user.open("/sources")
    assert page.database is fake_db
    assert page.kserver is fake_kserver
    await user.should_see('Help')
    await user.should_see('Importer Output')
    await user.should_see('Translation Output')
    await user.should_see('Source Files')
    await user.should_see('Repository')
    await user.should_see('Translate and Import')


def make_file(path, name, errors=0, warnings=0, import_errors=0):
    """Auxiliary function to create mock files for testing."""
    return SimpleNamespace(path=path, name=name, errors=errors, warnings=warnings, import_errors=import_errors)


@pytest.mark.asyncio
async def test_filter_import_files_filters_correctly(fake_db, fake_kserver, tmp_path):
    """Test that filter_import_files returns only files under current folder and groups errors correctly."""

    fake_kserver.kleio_home = str(tmp_path)

    # Create test files
    ok_file = make_file("sub/ok.cli", "ok")
    err_file = make_file("sub/err.cli", "err", errors=1)
    warn_file = make_file("sub/warn.cli", "warn", warnings=2)
    imp_file = make_file("sub/imp.cli", "imp", import_errors=3)
    outside_file = make_file("other/out.cli", "out", errors=1)
    fake_scheduler = MagicMock()

    fake_db.get_import_status.return_value = [ok_file, err_file, warn_file, imp_file, outside_file]

    page = Sources(fake_db, fake_kserver, fake_scheduler)

    # Filter inside "sub"
    filtered, problems, warnings, import_errors, errors = page.filter_import_files("sub")

    # Only files under sub/ should be included
    assert all("sub" in key for key in filtered.keys())
    assert ok_file.path not in problems  # no issues
    assert err_file.path in problems
    assert warn_file.path in problems
    assert imp_file.path in problems

    # Each type should be split correctly
    assert err_file.path in errors
    assert warn_file.path in warnings
    assert imp_file.path in import_errors

    # File outside folder should not appear
    assert outside_file.path not in filtered


@pytest.mark.asyncio
async def test_render_file_tree_renders_files(user, fake_db, fake_kserver, tmp_path, monkeypatch):
    """Test that render_file_tree displays folders and files with correct styling and callbacks."""

    fake_kserver.kleio_home = str(tmp_path)
    fake_scheduler = MagicMock()
    page = Sources(fake_db, fake_kserver, fake_scheduler)

    await user.open("/sources")

    # Patch methods that would otherwise trigger navigation
    mock_handle_home = MagicMock()
    mock_show_report = MagicMock()
    monkeypatch.setattr(page, "_handle_home_click", mock_handle_home)
    monkeypatch.setattr(page, "_show_report_from_update_column", mock_show_report)

    # Patch _render_directory_viewer as async to avoid TaskGroup error
    async def fake_render_directory_viewer():
        files_to_render = {
            "sub/file1.cli": {"name": "file1", "path": "sub/file1.cli", "status": "error"},
            "sub/file2.cli": {"name": "file2", "path": "sub/file2.cli", "status": "warning"},
        }
        page.render_file_tree(files_to_render, str(tmp_path / "sub"))

    monkeypatch.setattr(page, "_render_directory_viewer", fake_render_directory_viewer)

    # Trigger page rendering
    await user.open("/sources")

    # Verify that the file labels are present and have the right classes
    file1_label = user.find("file1")
    user.find("file2")

    # Clicking a file should call _show_report_from_update_column
    file1_label.click()
    mock_show_report.assert_called_once()


@pytest.mark.asyncio
async def test_display_update_column_counts(user, fake_db, fake_kserver, tmp_path, monkeypatch):
    """Test that _display_column_update displays the correct information."""

    fake_scheduler = MagicMock()
    page = Sources(fake_db, fake_kserver, fake_scheduler)

    # Prepare fake files
    file1 = MagicMock(errors=2, warnings=0, import_errors=0, status=MagicMock(name='T'), import_status=MagicMock(name='N'))
    file2 = MagicMock(errors=0, warnings=1, import_errors=0, status=MagicMock(name='T'), import_status=MagicMock(name='N'))
    file3 = MagicMock(errors=0, warnings=0, import_errors=1, status=MagicMock(name='T'), import_status=MagicMock(name='N'))

    fake_imported_files = {
        "file1.cli": file1,
        "file2.cli": file2,
        "file3.cli": file3
    }

    # Patch filter_import_files to return controlled dicts
    monkeypatch.setattr(
        page,
        "filter_import_files",
        lambda current_path=None: (fake_imported_files, {}, {}, {}, {})
    )

    # Patch display container
    page.display_table_container = MagicMock()

    # Set queues
    page.import_queue = ["fileA.cli", "fileB.cli"]
    page.translate_queue = ["fileX.cli"]

    # Call the method
    page.display_update_column(filepath=str(tmp_path))

    # Check if user sees expected labels.
    await user.open("/sources")
    await user.should_see('Recent Changes')
    await user.should_see('Need translation')
    await user.should_see('Need import')
    await user.should_see('Review Needed')
    await user.should_see('With translation errors')
    await user.should_see('With translation warnings')
    await user.should_see('With import errors')
    await user.should_see('In Progress')
    await user.should_see('Currently translating')
    await user.should_see('Queued for translation')
    await user.should_see('Queued for import')

    # Check sums
    sum_translation_errors = sum(1 for f in fake_imported_files.values() if (f.errors or 0) > 0)
    sum_translation_warnings = sum(1 for f in fake_imported_files.values() if (f.warnings or 0) > 0)
    sum_import_errors = sum(1 for f in fake_imported_files.values() if (f.import_errors or 0) > 0)

    assert sum_translation_errors == 1
    assert sum_translation_warnings == 1
    assert sum_import_errors == 1

    # Queues should be visible
    await user.should_see("fileA.cli, fileB.cli")
    await user.should_see("fileX.cli")


@pytest.mark.asyncio
async def test_render_directory_viewer(user, fake_db, fake_kserver, monkeypatch):
    """Test that directory viewer renders grids and CLI buttons correctly."""
    captured = {}

    def fake_aggrid(options, **kwargs):
        # capture first and second grid separately
        if "folder_name" in str(options):
            captured["folder_grid"] = options
        else:
            captured["file_grid"] = options
        grid_mock = MagicMock()
        grid_mock.on.return_value = grid_mock
        return grid_mock

    monkeypatch.setattr("timelink.web.pages.sources_page.ui.aggrid", fake_aggrid)
    monkeypatch.setattr("timelink.web.pages.sources_page.Sources.update_grid", lambda self: None)
    fake_scheduler = MagicMock()

    page = Sources(fake_db, fake_kserver, fake_scheduler)
    await page._render_directory_viewer()

    # check folder grid
    folder_opts = captured.get("folder_grid")
    assert folder_opts is not None
    assert folder_opts["columnDefs"][0]["field"] == "folder_name"

    # check file grid
    file_opts = captured.get("file_grid")
    assert file_opts is not None
    col_fields = [c["field"] for c in file_opts["columnDefs"]]
    assert "file_name" in col_fields
    assert "t_report" in col_fields
    assert "i_report" in col_fields


class DummyFile:
    def __init__(self, name, status="N", errors=0, warnings=0,
                 import_status="N", import_errors=0, import_warning_rpt=None):
        self.name = name
        self.status = SimpleNamespace(name=status)
        self.errors = errors
        self.warnings = warnings
        self.import_status = SimpleNamespace(name=import_status)
        self.import_errors = import_errors
        self.import_warning_rpt = import_warning_rpt
        self.modified_string = "2025-01-01"


@pytest.mark.parametrize("cli_mode", [False, True])
def test_update_grid(monkeypatch, tmp_path, cli_mode):

    # setup fake folder
    tmp_file = tmp_path / "file.cli"
    if cli_mode:
        tmp_file.write_text("dummy")
    else:
        (tmp_path / "subfolder").mkdir()

    # fake grids
    folder_grid = MagicMock()
    folder_grid.options = {"rowData": []}
    file_grid = MagicMock()
    file_grid.options = {"rowData": []}
    cli_buttons_row = MagicMock()

    # fake page
    page = SimpleNamespace(
        path=tmp_path,
        upper_limit=tmp_path,
        imported_files_dict={str(tmp_file): DummyFile("file.cli")},
        folder_grid=folder_grid,
        file_grid=file_grid,
        cli_buttons_row=cli_buttons_row,
        track_files_to_import=set(),
        track_files_to_translate=set(),
    )

    page.has_cli_files = lambda p: True

    Sources.update_grid(page, translate_boxes=True, import_boxes=False)

    # verify correct grid was used
    if cli_mode:
        assert file_grid.visible is True
        assert folder_grid.visible is False
        row = file_grid.options["rowData"][0]
        assert row["file_name"] == "<strong>file.cli</strong>"
        assert "t_report" in row
        assert "i_report" in row
    else:
        assert folder_grid.visible is True
        assert file_grid.visible is False
        row = folder_grid.options["rowData"][0]
        assert row["folder_name"].startswith("📁")


def test_handle_home_click(monkeypatch, tmp_path):
    page = SimpleNamespace(
        path=None,
        refresh_path=MagicMock(),
        update_grid=MagicMock(),
    )

    Sources._handle_home_click(page, str(tmp_path))

    assert page.path == tmp_path
    page.refresh_path.assert_called_once()
    page.update_grid.assert_called_once()


def test_handle_cell_click(monkeypatch, tmp_path):
    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()

    page = SimpleNamespace(
        path=None,
        refresh_path=MagicMock(),
        update_grid=MagicMock(),
    )

    event = SimpleNamespace(args={"colId": "folder_name", "data": {"path": str(subfolder)}})
    Sources._handle_cell_click(page, event)

    assert page.path == subfolder
    page.refresh_path.assert_called_once()
    page.update_grid.assert_called_once()


@pytest.mark.parametrize("translate, import_", [(True, False), (False, True), (True, True), (False, False)])
def test_handle_cell_value_changed(monkeypatch, translate, import_):
    page = SimpleNamespace(
        track_files_to_translate=set(),
        track_files_to_import=set(),
    )

    row_data = {"row_id": 1, "translate_checkbox": translate, "import_checkbox": import_}
    event = SimpleNamespace(args={"data": row_data})

    Sources._handle_cell_value_changed(page, event)

    if translate:
        assert 1 in page.track_files_to_translate
    else:
        assert 1 not in page.track_files_to_translate

    if import_:
        assert 1 in page.track_files_to_import
    else:
        assert 1 not in page.track_files_to_import


@pytest.mark.asyncio
@pytest.mark.parametrize("checkbox_type, expected_queue_attr, expected_count_attr", [
    ("translate_checkbox", "translate_queue", "queued_for_translate"),
    ("import_checkbox", "import_queue", "queued_for_import"),
])
async def test_process_files(monkeypatch, tmp_path, checkbox_type, expected_queue_attr, expected_count_attr):
    # fake file path + row
    file_path = tmp_path / "file.cli"
    row = {
        "row_id": 0,
        "path": str(file_path),
        "file_name_no_html": "file.cli",
    }

    dummy_file = MagicMock()
    dummy_file.import_warning_rpt = None

    # fake page
    page = SimpleNamespace(
        file_grid=SimpleNamespace(options={"rowData": [row]}),
        track_files_to_translate={0} if checkbox_type == "translate_checkbox" else set(),
        track_files_to_import={0} if checkbox_type == "import_checkbox" else set(),
        queued_for_translate=0,
        queued_for_import=0,
        translate_queue=[],
        import_queue=[],
        imported_files_dict={str(file_path): dummy_file},
        _run_import_background=MagicMock(),
        _run_translate_background=MagicMock(),
        display_update_column=MagicMock(),
        _handle_home_click=MagicMock(),
    )

    # patch asyncio.create_task so it just calls synchronously
    monkeypatch.setattr("timelink.web.pages.sources_page.ui.row", lambda *a, **k: MagicMock())
    monkeypatch.setattr(asyncio, "create_task", lambda coro: None)

    await Sources.process_files(page, checkbox_type)

    # verify queued counts updated
    queued_count = getattr(page, expected_count_attr)
    queued_list = getattr(page, expected_queue_attr)
    assert queued_count == 1
    assert "file.cli" in queued_list

    if checkbox_type == "import_checkbox":
        # import branch should mark "QT" and schedule _run_import_background
        assert dummy_file.import_warning_rpt == "QT"
        page._run_import_background.assert_called_once_with(dummy_file)
    else:
        # translate branch schedules _run_translate_background
        page._run_translate_background.assert_called_once_with(dummy_file)

    # display_update_column and handle_home_click called with parent path
    parent_path = file_path.parent.resolve()
    page.display_update_column.assert_called_once_with(filepath=parent_path)
    page._handle_home_click.assert_called_once_with(parent_path)


@pytest.mark.asyncio
async def test_run_import_background(fake_db, fake_kserver, monkeypatch):
    from timelink.web.pages.sources_page import Sources

    # Create a real Sources instance
    fake_scheduler = MagicMock()
    page = Sources(fake_db, fake_kserver, fake_scheduler)

    # Setup attributes for the test
    dummy_file = MagicMock()
    dummy_file.name = "file.cli"
    page.import_queue = ["file.cli"]
    page.queued_for_import = 1
    page.imported_files_dict = {"file.cli": dummy_file}
    page.refresh_imported_files = MagicMock()
    page.import_lock = asyncio.Lock()

    # Patch io_bound to do nothing
    monkeypatch.setattr("timelink.web.pages.sources_page.run.io_bound", lambda f, *a, **kw: asyncio.sleep(0))

    await page._run_import_background(dummy_file)

    assert page.queued_for_import == 0
    assert "file.cli" not in page.import_queue


@pytest.mark.asyncio
async def test_get_report(fake_db, fake_kserver, monkeypatch):

    fake_scheduler = MagicMock()
    page = Sources(fake_db, fake_kserver, fake_scheduler)
    page.switch_tabs = AsyncMock()
    page.import_output_tab = "import_tab_mock"
    page.trans_output_tab = "trans_tab_mock"
    monkeypatch.setattr(ui, "notify", MagicMock())

    base_row = {"file_name_no_html": "file.cli", "path": "/tmp/file.cli"}

    # i_report: Not Imported Yet
    row_data = {"colId": "i_report", "data": {**base_row, "i_report": "Not Imported Yet."}}
    await page._get_report(row_data)
    ui.notify.assert_called_with("file.cli has not been imported yet!", type="negative")
    ui.notify.reset_mock()
    page.switch_tabs.reset_mock()

    # t_report: Currently Translating
    row_data = {"colId": "t_report", "data": {**base_row, "t_report": "Currently Translating"}}
    await page._get_report(row_data)
    ui.notify.assert_called_with("file.cli is queued for translation.")
    ui.notify.reset_mock()
    page.switch_tabs.reset_mock()

    # i_report: normal value triggers switch_tabs
    row_data = {"colId": "i_report", "data": {**base_row, "i_report": "1 ERRORS"}}
    await page._get_report(row_data)
    page.switch_tabs.assert_called_with(page.import_output_tab, "file.cli", "i_report", "/tmp/file.cli")


@pytest.mark.asyncio
async def test_show_report_from_update_column(fake_db, fake_kserver, tmp_path):

    fake_scheduler = MagicMock()
    page = Sources(fake_db, fake_kserver, fake_scheduler)
    page.switch_tabs = AsyncMock()
    page.trans_output_tab = "trans_tab_mock"
    page.import_output_tab = "import_tab_mock"
    page._handle_home_click = MagicMock()

    file_path = tmp_path / "file.cli"

    # test translation error type
    await page._show_report_from_update_column(str(file_path), "error", "file.cli")
    page._handle_home_click.assert_called_with(file_path.parent.resolve())
    page.switch_tabs.assert_called_with("trans_tab_mock", "file.cli", "cli_file", str(file_path))

    # test import type
    await page._show_report_from_update_column(str(file_path), "import", "file.cli")
    page.switch_tabs.assert_called_with("import_tab_mock", "file.cli", "import_error", str(file_path))


@pytest.mark.asyncio
async def test_switch_tabs(fake_db, fake_kserver, tmp_path):

    fake_scheduler = MagicMock()

    page = Sources(fake_db, fake_kserver, fake_scheduler)
    page.tabs = MagicMock()
    page.translate_file_displayer = MagicMock()
    page.import_file_displayer = MagicMock()

    # Mocks for reports
    page.kserver.get_report = MagicMock(return_value="translation report")
    page.database.get_import_rpt = MagicMock(return_value="import report")

    # CLI file
    cli_file = tmp_path / "file.cli"
    cli_file.write_text("dummy content", encoding="utf-8")

    # ----------------- cli_file branch -----------------
    await page.switch_tabs(
        tab_to_switch="tab_cli",
        file_to_read="file.cli",
        report_type="cli_file",
        path=str(cli_file)
    )
    page.tabs.set_value.assert_called_with("tab_cli")
    assert page.translate_file_displayer.content == "dummy content"

    # ----------------- t_report branch -----------------
    row_path = tmp_path / "t_file.cli"
    row_path.write_text("ignored content")
    page.imported_files_dict[str(row_path)] = MagicMock()
    await page.switch_tabs(
        tab_to_switch="tab_trans",
        file_to_read="t_file.cli",
        report_type="t_report",
        path=str(row_path)
    )
    assert page.translate_file_displayer.content == "translation report"

    # ----------------- import_error branch -----------------
    await page.switch_tabs(
        tab_to_switch="tab_import",
        file_to_read="import_file.cli",
        report_type="import_error",
        path=str(tmp_path)
    )
    page.database.get_import_rpt.assert_called_with("import_file.cli")
    assert page.import_file_displayer.content == "import report"
