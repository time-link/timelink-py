from timelink.web.pages import navbar
from pathlib import Path
from nicegui import ui, events, run
from collections import defaultdict
import asyncio


class Sources:

    """Page for sources viewing. """
    def __init__(self, timelink_app) -> None:
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server
        self.scheduler = timelink_app.job_scheduler
        self.track_files_to_import = set()
        self.track_files_to_translate = set()
        self.imported_files_dict = {}
        self.problem_files = []
        self.translate_warning_files = []
        self.import_error_files = []
        self.queued_for_import = 0
        self.queued_for_translate = 0
        self.currently_translating = 0
        self.import_queue = []
        self.translate_queue = []
        self.import_lock = asyncio.Lock()
        self.translate_lock = asyncio.Lock()

        # Refresh imported files on load and once every five minutes automatically.
        self.refresh_imported_files()
        self.scheduler.add_job(self.scheduled_refresh_imported_files, "interval", name="Refresh Source Files Dictionary", minutes=5)

        @ui.page('/sources')
        async def register():
            await self.sources_page()

    async def scheduled_refresh_imported_files(self):
        """Job trigger to refresh imported files."""
        self.refresh_imported_files()

    def refresh_imported_files(self):
        """Method to refresh import files. Runs once on start and when there are changes to the database."""

        self.imported_files_dict.clear()
        for f in self.database.get_import_status(match_path=True):
            self.imported_files_dict[str((Path(self.kserver.kleio_home) / f.path).resolve())] = f

        self.problem_files = [
            name for name, f in self.imported_files_dict.items()
            if (f.errors or 0) > 0 or (f.warnings or 0) > 0 or (f.import_errors or 0) > 0
        ]
        self.translate_warning_files = [
            name for name, f in self.imported_files_dict.items() if (f.warnings or 0) > 0
        ]
        self.import_error_files = [
            name for name, f in self.imported_files_dict.items() if (f.import_errors or 0) > 0
        ]

    async def sources_page(self):
        with navbar.header():
            ui.page_title("Sources")

            with ui.card().tight().classes("w-full border-0 border-gray-300 rounded-none shadow-none"):
                with ui.tabs() as self.tabs:
                    self.files_tab = ui.tab('files', label='Source Files').classes("w-full text-orange-500 font-bold")
                    self.repository_tab = ui.tab('repository', label='Repository').classes("w-full text-orange-500 font-bold")
                    self.trans_output_tab = ui.tab(
                        'translation_output', label='Translation Output'
                    ).classes("w-full text-orange-500 font-bold")
                    self.import_output_tab = ui.tab(
                        'import_output', label='Importer Output'
                    ).classes("w-full text-orange-500 font-bold")
                    self.help_tab = ui.tab('help', label='Help').classes("w-full text-orange-500 font-bold")

                with ui.tab_panels(self.tabs, value=self.files_tab).classes('w-full'):
                    with ui.tab_panel(self.files_tab):

                        ui.add_body_html('''<style>
                            .highlight-cell { text-decoration: underline dotted; }
                            .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                            </style>''')

                        ui.add_body_html('''<style>
                            .import-cell { text-decoration: underline dotted; }
                            .import-cell:hover { color: purple; font-weight: bold; cursor: pointer; }
                            </style>''')

                        self.path_container_row = ui.row()

                        with self.path_container_row:
                            ui.label("Kleio Files in ").classes("-mr-2 font-bold text-xs text-orange-500")
                            self.home_path = ui.label(
                                "home: "
                            ).classes(
                                "-mr-2 font-bold text-xs highlight-cell cursor-pointer"
                            ).on("Click", lambda path=self.kserver.kleio_home: self._handle_home_click(path))

                        with ui.grid(columns=3).classes("w-full"):
                            with ui.column().classes("col-span-2 mr-4"):
                                with ui.card().tight().classes("w-full border-0 border-gray-300 rounded-none shadow-none"):
                                    await self._render_directory_viewer()

                            self.display_table_container = ui.column().classes("col-span-1")
                            self.display_update_column(filepath=self.kserver.kleio_home)

                        ui.separator()
                        ui.label(
                            "Already Imported Sources"
                        ).on(
                            'click',
                            lambda sources: ui.navigate.to(f'/all_tables/sources?display_type=sources&value={sources}')
                        ).classes('mb-4 cursor-pointer text-orange-500 text-sm underline italic')

                    with ui.tab_panel(self.repository_tab).classes("items-center"):
                        ui.label("Repository Tab")

                    with ui.tab_panel(self.trans_output_tab).classes("items-center"):
                        with ui.column().classes("w-full"):
                            self.translate_file_displayer = ui.code(
                                "Nothing to display yet - use the file browser to select content."
                            )

                    with ui.tab_panel(self.import_output_tab).classes("items-center"):
                        with ui.column().classes("w-full"):
                            self.import_file_displayer = ui.code("Nothing to display yet - use the file browser to select content.")

                    with ui.tab_panel(self.help_tab):
                        ui.label("Translate and Import").classes("-mr-2 font-bold text-lg text-orange-500")
                        ui.label(
                            "The process of inputing data into Timelink is a two step process: " +
                            "first the files in kleio notation are translated and then imported into the database. " +
                            "Files with errors at the translation phase should not be imported. " +
                            "Clicking on the message with the number of errors shows an error report. " +
                            "Kleio documents should be placed in the specific diretory for sources. "
                        ).classes("-mr-2 text-xs")

    def filter_import_files(self, current_path: str = None):
        """Filters the files displayed in the update column to only the ones within the current folder."""

        current_folder = (Path(self.kserver.kleio_home) / current_path).resolve()
        filtered_files = {}

        for key, value in self.imported_files_dict.items():

            full_file_path = (Path(self.kserver.kleio_home) / value.path).resolve()
            if full_file_path.is_relative_to(current_folder):
                filtered_files[key] = value

        dir_problem_files = {
            f.path: {
                "name": f.name,
                "path": f.path,
                "status": (
                    "error" if (f.errors or 0) > 0
                    else "warning" if (f.warnings or 0) > 0
                    else "import_error"
                )
            }
            for f in filtered_files.values()
            if (f.errors or 0) > 0 or (f.warnings or 0) > 0 or (f.import_errors or 0) > 0
        }

        dir_trans_error_files = {
            f.path: {
                "name": f.name,
                "path": f.path,
                "status": "error"
            } for f in filtered_files.values() if (f.errors or 0) > 0
        }

        dir_trans_warning_files = {
            f.path: {
                "name": f.name,
                "path": f.path,
                "status": "warning"
            } for f in filtered_files.values() if (f.warnings or 0) > 0
        }
        dir_imp_error_files = {
            f.path: {
                "name": f.name,
                "path": f.path,
                "status": "import_error"
            } for f in filtered_files.values() if (f.import_errors or 0) > 0
        }

        return filtered_files, dir_problem_files, dir_trans_warning_files, dir_imp_error_files, dir_trans_error_files

    def render_file_tree(self, files_to_render: dict, filepath: str):
        """Render a file tree depending on the passed dictionary to display the problem files."""

        # Group by parent folder
        grouped_problem_files = defaultdict(list)
        for full_path, name in files_to_render.items():
            full_path_abs = (Path(self.kserver.kleio_home) / full_path).resolve()
            try:
                relative_parent = full_path_abs.parent.relative_to(filepath)
            except ValueError:
                relative_parent = full_path_abs.parent

            key = "__current__" if relative_parent == Path('.') else str(relative_parent)
            grouped_problem_files[key].append(name)

        status_colors = {
            "error": "red",
            "warning": "gray",
            "import_error": "purple",
        }

        with ui.column():
            if files_to_render:
                for folder, files in grouped_problem_files.items():
                    with ui.row():
                        with ui.column():
                            if folder != "__current__":
                                folder_path = Path(folder)
                                if folder_path.is_absolute():
                                    full_folder_path = folder_path.resolve()
                                else:
                                    full_folder_path = (Path(filepath) / folder_path).resolve()
                                ui.label(
                                    f"📁 {folder}"
                                ).classes(
                                    "font-bold text-gray-700 highlight-cell"
                                ).on("click", lambda _, path=full_folder_path: self._handle_home_click(path))
                            for file in files:
                                full_file_path = str(Path(self.kserver.kleio_home) / file["path"])
                                file_type = file["status"]
                                file_name = file["name"]
                                ui.label(
                                    f"{file_name}"
                                ).classes(
                                    f"text-{status_colors[file_type]}-600 ml-5 highlight-cell"
                                ).on(
                                    "click",
                                    lambda _,
                                    file_path=full_file_path,
                                    file_name=file_name,
                                    file_type=file_type:
                                    self._show_report_from_update_column(file_path, file_type, file_name)
                                )
            else:
                ui.label("None").classes("italic text-gray-600 ml-5")

    def display_update_column(self, filepath: str = None):
        """Function to render file status table dynamically."""

        (directory_imported_files,
         dir_problem_files,
         dir_translate_warning_files,
         dir_import_error_files,
         dir_translate_error_files) = self.filter_import_files(current_path=filepath)

        self.display_table_container.clear()

        sum_translation_error_files = sum(1 for f in directory_imported_files.values() if (f.errors or 0) > 0)
        sum_translation_warning_files = sum(1 for f in directory_imported_files.values() if (f.warnings or 0) > 0)
        sum_import_error_files = sum(1 for f in directory_imported_files.values() if (f.import_errors or 0) > 0)

        with self.display_table_container:
            with ui.card().tight().classes("w-full bg-blue-100 text-orange-500 font-bold"):
                ui.label("Recent Changes").classes("ml-1 mt-1 mb-1")

            with ui.row().classes("justify-between w-full"):
                ui.label("Need translation").classes("border-b text-blue-900")
                ui.label(
                    str(sum(1 for f in directory_imported_files.values() if f.status.name == "T"))
                ).classes("border-b text-blue-900 mr-4")

            with ui.row().classes("justify-between w-full"):
                ui.label("Need import").classes("border-b text-blue-900")
                ui.label(
                    str(sum(1 for f in directory_imported_files.values() if f.import_status.name in ("N", "U")))
                ).classes("border-b text-blue-900 mr-4")

            with ui.card().tight().classes("w-full bg-blue-100 text-orange-500 font-bold"):
                ui.label("Review Needed").classes("ml-1 mt-1 mb-1")

            with ui.row().classes("justify-between w-full"):
                ui.label("With translation errors").classes("border-b text-red-600")
                navigate_translation_error = ui.row()
                with navigate_translation_error:
                    ui.label(str(sum_translation_error_files)).classes("border-b text-blue-900 mr-4")

            with ui.row().classes("justify-between w-full"):
                ui.label("With translation warnings").classes("border-b text-gray-600")
                navigate_translation_warnings = ui.row()
                with navigate_translation_warnings:
                    ui.label(str(sum_translation_warning_files)).classes("border-b text-blue-900 mr-4")

            with ui.row().classes("justify-between w-full"):
                ui.label("With import errors").classes("border-b text-purple-700")
                navigate_import_errors = ui.row()
                with navigate_import_errors:
                    ui.label(str(sum_import_error_files)).classes("border-b text-blue-900 mr-4")

            with ui.card().tight().classes("w-full bg-blue-100 text-orange-500 font-bold"):
                ui.label("In Progress").classes("ml-1 mt-1 mb-1")

            with ui.row().classes("justify-between w-full"):
                ui.label("Currently translating").classes("border-b text-blue-900")
                ui.label(self.currently_translating).classes("border-b text-blue-900 mr-4")

            with ui.row().classes("justify-between w-full"):
                ui.label("Queued for translation").classes("border-b text-blue-900")
                navigate_translate_queue = ui.row()
                with navigate_translate_queue:
                    ui.label(self.queued_for_translate).classes("border-b text-blue-900 mr-4")
                    ui.label(
                        'Update Info'
                    ).classes(
                        "highlight-cell"
                    ).on(
                        "click",
                        lambda _,
                        path=filepath: self._handle_home_click(path)
                    ) if len(self.translate_queue) > 0 else None

            with ui.row().classes("justify-between w-full"):
                ui.label("Queued for import").classes("border-b text-blue-900")
                navigate_import_queue = ui.row()
                with navigate_import_queue:
                    ui.label(self.queued_for_import).classes("border-b text-blue-900 mr-4")
                    ui.label(
                        'Update Info'
                    ).classes(
                        "highlight-cell"
                    ).on(
                        "click",
                        lambda _,
                        path=filepath: self._handle_home_click(path)
                    ) if len(self.import_queue) > 0 else None

            if self.import_queue:
                with ui.card().tight().classes(
                    "w-full border-b text-orange-500 font-bold rounded-none shadow-none"
                ):
                    ui.label("Queued for Import").classes("border-b text-orange-500")
                    ui.label(", ".join(self.import_queue)).classes("border-b ml-5 mt-2 text-gray-400")

            if self.translate_queue:
                with ui.card().tight().classes(
                    "w-full border-b text-orange-500 font-bold rounded-none shadow-none"
                ):
                    ui.label("Queued for Translation").classes("border-b text-orange-500")
                    ui.label(", ".join(self.translate_queue)).classes("border-b ml-5 mt-2 text-gray-400")

            if dir_problem_files:
                with ui.card().tight().classes(
                    "w-full border-b text-orange-500 font-bold rounded-none shadow-none"
                ):
                    ui.label("Review needed").classes("border-b text-orange-500")

                self.render_file_tree(dir_problem_files, filepath)

            if dir_translate_error_files:
                with ui.card().tight().classes(
                    "w-full border-b text-orange-500 font-bold rounded-none shadow-none"
                ):
                    translation_error_label = ui.label("With Translation Errors").classes("border-b text-orange-500")
                    with navigate_translation_error:
                        ui.link(
                            'See List',
                            translation_error_label
                        ).classes("highlight-cell") if sum_translation_error_files > 0 else None

                self.render_file_tree(dir_translate_error_files, filepath)

            if dir_translate_warning_files:
                with ui.card().tight().classes(
                    "w-full border-b text-orange-500 font-bold rounded-none shadow-none"
                ):
                    translation_warning_label = ui.label("With Translation Warnings").classes("border-b text-orange-500")
                with navigate_translation_warnings:
                    ui.link(
                        'See List', translation_warning_label
                    ).classes("highlight-cell") if sum_translation_warning_files > 0 else None

                self.render_file_tree(dir_translate_warning_files, filepath)

            if dir_import_error_files:
                with ui.card().tight().classes(
                    "w-full border-b text-orange-500 font-bold rounded-none shadow-none"
                ):
                    import_error_label = ui.label("With Import Errors").classes("border-b text-orange-500")
                    with navigate_import_errors:
                        ui.link('See List', import_error_label).classes("highlight-cell") if sum_import_error_files > 0 else None

                self.render_file_tree(dir_import_error_files, filepath)

    async def _render_directory_viewer(self):
        """View of the source files available on the current timelink home."""

        self.path = Path(self.kserver.kleio_home).expanduser()
        self.upper_limit = self.path

        with ui.column().classes("w-full h-[calc(90vh-64px)]"):

            self.folder_grid = ui.aggrid({
                'columnDefs': [{'field': 'folder_name', 'headerName': 'Folder'}],
                'rowSelection': 'multiple',
            }, html_columns=[0]).classes('w-full flex-1').on('cellClicked', lambda e: self._handle_cell_click(e))

            self.file_grid = ui.aggrid({
                'columnDefs': [
                    {'field': 'translate_checkbox', 'headerName': '', "cellRenderer": 'checkboxRenderer', 'width': 30},
                    {'field': 'icon_status', 'headerName': 'Status', 'width': 60},
                    {'field': 'file_name', 'headerName': 'Name', "cellClass": "highlight-cell"},
                    {'field': 'date', 'headerName': 'Date'},
                    {'field': 't_report', 'headerName': 'Translation Report', "cellClass": "highlight-cell"},
                    {'field': 'import_checkbox', 'headerName': ' ', "cellRenderer": 'checkboxRenderer', 'width': 30},
                    {'field': 'i_report', 'headerName': 'Import Report', "cellClass": "import-cell"},
                ],
                'rowSelection': 'multiple',
            }, html_columns=[2]).classes('w-full flex-1').on('cellValueChanged', self._handle_cell_value_changed)

            self.file_grid.on(
                'cellClicked',
                lambda e: self._get_report(e.args) if e.args["colId"] in ("file_name", "t_report", "i_report") else None
            )

            self.file_grid.visible = False

            self.cli_buttons_row = ui.row().classes("mt-2 w-full justify-between items-center")

            with self.cli_buttons_row:
                with ui.row():
                    ui.button(
                        "Translate Selected Files",
                        on_click=lambda: self.process_files("translate_checkbox")
                    ).classes("text-xs px-2 py-1 h-6")

                    ui.label("Unselect all").on(
                        "click",
                        lambda: self.select_deselect_checkboxes("translate_checkbox", False)
                    ).classes("mt-2 highlight-cell")

                    ui.label("Select all").on(
                        "click",
                        lambda: self.select_deselect_checkboxes("translate_checkbox", True)
                    ).classes("mt-2 highlight-cell")

                with ui.row():
                    ui.button(
                        "Import Selected Files",
                        on_click=lambda: self.process_files("import_checkbox")
                    ).classes("text-xs px-2 py-1 h-6")

                    ui.label("Unselect all").on(
                        "click",
                        lambda: self.select_deselect_checkboxes("import_checkbox", False)
                    ).classes("mt-2 highlight-cell")

                    ui.label("Select all").on(
                        "click",
                        lambda: self.select_deselect_checkboxes("import_checkbox", True)
                    ).classes("mt-2 highlight-cell")

        self.cli_buttons_row.visible = False
        self.update_grid()

    def has_cli_files(self, folder: Path) -> bool:
        """Check if a folder has cli files within it."""
        return any(f.suffix == ".cli" for f in folder.rglob("*.cli"))

    def update_grid(self, translate_boxes: bool = False, import_boxes: bool = False) -> None:
        """Refresh grid contextually depending on if there are files within the current subdirectory.

        Args:

            translate_boxes:    the initial state the translation resolution checkboxes are in (for select buttons).
            import_boxes:       the initial state the import resolution checkboxes are in (for select buttons).

            """

        cli_files = [p for p in self.path.glob("*.cli") if not p.name.startswith('.')]
        in_cli_mode = bool(cli_files)

        self.track_files_to_import = set()
        self.track_files_to_translate = set()

        self.folder_grid.visible = not in_cli_mode
        self.file_grid.visible = in_cli_mode
        grid_select = self.file_grid if in_cli_mode else self.folder_grid
        self.cli_buttons_row.visible = True if in_cli_mode else False

        if self.path == self.upper_limit:
            dirs = [
                p for p in self.path.rglob('*')
                if (
                    p.is_dir() and
                    not any(part.startswith('.') for part in p.relative_to(self.upper_limit).parts) and
                    self.has_cli_files(p)
                )
            ]
            paths = dirs + [p for p in self.path.glob('*.cli')]
        else:
            paths = [
                p for p in self.path.glob('*')
                if not p.name.startswith('.') and (
                    (p.is_dir() and self.has_cli_files(p)) or
                    p.suffix == ".cli"
                )
            ]

        if in_cli_mode:
            paths = [p for p in paths if p.suffix == ".cli"]

        paths.sort(key=lambda p: str(p.relative_to(self.upper_limit)).lower())
        paths.sort(key=lambda p: not p.is_dir())

        # Display grid according to if files are present or just folders.
        grid_select.options['rowData'] = [
            {
                'folder_name': f'📁 <strong>{str(p.relative_to(self.upper_limit))}</strong>' if p.is_dir() else '',
                'translate_checkbox': translate_boxes,
                'icon_status' : f'📄 [{self.imported_files_dict[str(p)].status.name}]' if not p.is_dir() else '',
                'file_name': (
                    f'<strong>{self.imported_files_dict[str(p)].name}</strong>' if not p.is_dir() and p.suffix == ".cli"
                    else ''
                ),
                'file_name_no_html': p.name if not p.is_dir() and p.suffix == ".cli" else '',
                'date': self.imported_files_dict[str(p)].modified_string if not p.is_dir() else '',
                't_report': (
                    "Currently Translating"
                    if self.imported_files_dict[str(p)].status.name == "P"
                    else (
                        f'{self.imported_files_dict[str(p)].errors or 0} Errors, '
                        f'{self.imported_files_dict[str(p)].warnings or 0} Warnings'
                        if (
                            self.imported_files_dict[str(p)].errors is not None or
                            self.imported_files_dict[str(p)].warnings is not None
                        )
                        else "File Not Translated Yet"
                    )
                ) if not p.is_dir() else '',
                'import_checkbox': import_boxes,
                'i_report': (
                    "Currently Translating"
                    if self.imported_files_dict[str(p)].status.name == "P"
                    else "QUEUED FOR IMPORT" if self.imported_files_dict[str(p)].import_warning_rpt == "QT"
                    else f'{self.imported_files_dict[str(p)].import_errors or 0} ERRORS'
                    if self.imported_files_dict[str(p)].import_status.name not in ("N", "U")
                    else 'Not Imported Yet.'
                ) if not p.is_dir() else '',
                'path': str(p),
                'row_id': idx,
            }
            for idx, p in enumerate(paths)
        ]

        # Update the sets with rows that are True
        for idx, row in enumerate(grid_select.options['rowData']):
            if row.get('translate_checkbox'):
                self.track_files_to_translate.add(idx)
            if row.get('import_checkbox'):
                self.track_files_to_import.add(idx)

        if self.path != self.upper_limit and not cli_files:
            grid_select.options['rowData'].insert(0, {
                'folder_name': '📁 <strong>..</strong>',
                'path': str(self.path.parent),
            })

        grid_select.update()

    def _handle_home_click(self, home_path: str):
        """Event handler for returning to initial path."""

        self.path = Path(home_path)
        self.refresh_path()
        self.update_grid()

    def _handle_cell_click(self, e: events.GenericEventArguments) -> None:
        """Refresh the grid with the new subdirectory when clicking on a new folder."""

        if e.args["colId"] == "folder_name":
            self.path = Path(e.args['data']['path'])
            if self.path.is_dir():
                self.refresh_path()
                self.update_grid()

    def _handle_cell_value_changed(self, e: events.GenericEventArguments) -> None:
        """Track which files to translate/import based on the checkboxes that are being selected/deselected."""

        row_data = e.args['data']

        if row_data.get("translate_checkbox"):
            self.track_files_to_translate.add(row_data["row_id"])
        else:
            self.track_files_to_translate.discard(row_data["row_id"])

        if row_data.get("import_checkbox"):
            self.track_files_to_import.add(row_data["row_id"])
        else:
            self.track_files_to_import.discard(row_data["row_id"])

    def refresh_path(self):
        """Construct navigation path above the grid display to allow for navigation within subfolders when dealing with files. """

        # Remove all labels after the timelink_home path
        while len(list(self.path_container_row)) > 2:
            self.path_container_row.remove(-1)

        parts = list(self.path.relative_to(self.upper_limit).parts)
        subpath = self.kserver.kleio_home

        with self.path_container_row:
            for i, part in enumerate(parts):

                subpath = self.upper_limit.joinpath(*parts[:i + 1])

                # Clickable subdirectory previous to the current one.
                if i < len(parts) - 1:
                    ui.label(part).classes(
                        "-mr-2 font-bold text-xs highlight-cell cursor-pointer"
                    ).on("click", lambda _, path=subpath: self._handle_home_click(path))

                    ui.label(":").classes("-mr-2 font-bold text-xs text-orange-500")

                # Last subdirectory is just a label.
                else:
                    ui.label(part).classes("-mr-2 font-bold text-xs text-orange-500")

            self.display_update_column(filepath=subpath)

    async def process_files(self, checkbox_type: str):
        """Send files to translate and/or import."""

        files_to_process = []
        data = self.file_grid.options.get('rowData', []) or []
        checked = self.track_files_to_translate if checkbox_type == 'translate_checkbox' else self.track_files_to_import

        for row in data:
            if row['row_id'] in checked:
                files_to_process.append([row['path'], row['file_name_no_html']])

        if not files_to_process:
            return

        verb = "translated" if checkbox_type == 'translate_checkbox' else "imported"

        if verb == "imported":
            self.queued_for_import += len(files_to_process)
            self.import_queue.extend([f[1] for f in files_to_process])
            for file in files_to_process:
                self.imported_files_dict[file[0]].import_warning_rpt = "QT"
                with ui.row():
                    asyncio.create_task(self._run_import_background(self.imported_files_dict[file[0]]))
        else:
            self.translate_queue = [f[1] for f in files_to_process]
            self.queued_for_translate = len(files_to_process)
            for file in files_to_process:
                asyncio.create_task(self._run_translate_background(self.imported_files_dict[file[0]]))
        self.display_update_column(filepath=Path(files_to_process[0][0]).parent.resolve())
        self._handle_home_click(Path(files_to_process[0][0]).parent.resolve())

    async def _run_import_background(self, file):
        async with self.import_lock:
            try:
                print(f"Attempting to import {file.name}...")
                await run.io_bound(self.database.import_from_xml, file, self.kserver)
                await run.io_bound(self.refresh_imported_files)
                if file.name in self.import_queue:
                    self.import_queue.remove(file.name)
                self.queued_for_import = self.queued_for_import - 1
                print(f"Finished importing {file.name}!")
            except Exception as e:
                print(f"Error importing {file.name}: {e}")

    async def _run_translate_background(self, file):
        async with self.translate_lock:
            try:
                print(f"Attempting to translate {file.name}...")
                self.currently_translating = self.currently_translating + 1
                self.queued_for_translate = self.queued_for_translate - 1
                await run.io_bound(self.kserver.translate, file.path, recurse="no", spawn="no")

                # Keep checking if translation is complete
                while True:
                    await asyncio.sleep(5)  # wait between polls
                    await run.io_bound(self.refresh_imported_files)

                    current_file = self.imported_files_dict.get(str((Path(self.kserver.kleio_home) / file.path).resolve()))
                    status = current_file.status.name
                    if status not in ("P", "Q"):
                        print(f"Finished {file.name} translation!")
                        break

                if file.name in self.translate_queue:
                    self.translate_queue.remove(file.name)

                self.currently_translating = self.currently_translating - 1
            except Exception as e:
                print(f"Error translating {file.name}: {e}")

    def select_deselect_checkboxes(self, checkbox_type: str, select: bool):
        """Handle selection of checkboxes when buttons to select/deselect all are pressed."""

        data = self.file_grid.options.get('rowData', []) or []

        for row in data:
            if row[checkbox_type]:
                row[checkbox_type] = select

        if checkbox_type == "translate_checkbox":
            self.update_grid(translate_boxes=select)
        else:
            self.update_grid(import_boxes=select)

    async def _get_report(self, row_data):
        """Handle the retrieval of translation/error reports according to the row information of the picked file
        """

        col = row_data["colId"]
        base_name = row_data["data"]["file_name_no_html"]
        full_path = row_data["data"]["path"]

        if col == "i_report":
            if (
                row_data["data"]["i_report"] != "Not Imported Yet." and
                row_data["data"]["i_report"] not in ("QUEUED FOR IMPORT", "Currently Translating")
            ):
                await self.switch_tabs(self.import_output_tab, base_name, "i_report", full_path)
            elif row_data["data"]["i_report"] == "QUEUED FOR IMPORT":
                ui.notify(f"{base_name} is queued for import.")
            elif row_data["data"]["i_report"] == "Currently Translating":
                ui.notify(f"{base_name} is queued for translation.")
            else:
                ui.notify(f"{base_name} has not been imported yet!", type="negative")

        elif col == "t_report":
            if row_data["data"]["t_report"] not in ("Not Translated Yet.", "Currently Translating"):
                await self.switch_tabs(self.trans_output_tab, base_name, "t_report", full_path)
            elif row_data["data"]["t_report"] == "Currently Translating":
                ui.notify(f"{base_name} is queued for translation.")
            else:
                ui.notify(f"{base_name} was not translated yet!", type="negative")
        else:
            await self.switch_tabs(self.trans_output_tab, base_name, "cli_file", full_path)

    async def _show_report_from_update_column(self, filepath: str, file_type: str, file_name: str):
        """Switches to the appropriate tab based on a file's path and report type that was clicked in the update column.

        Args:

            filepath:   Path to the file
            file_type:  Type of report that should be shown.
            file_name:  Name of the file
        """

        self._handle_home_click(Path(filepath).parent.resolve())

        if file_type in {"error", "warning"}:    # If it's a translation issue
            await self.switch_tabs(self.trans_output_tab, file_name, "cli_file", filepath)
        else:         # If it's an import issue
            await self.switch_tabs(self.import_output_tab, file_name, "import_error", filepath)

    async def switch_tabs(self, tab_to_switch: ui.tab, file_to_read: str, report_type: str, path: str):
        """Display reports on a specified row of data, both translation and import are possible depending on the cell clicked.
        Tab switching happens automatically, however importer output is incorrect because no file has been imported as of yet.

        Args:

            tab_to_switch:      Value of the ui.tab to switch to.
            file_to_read:       File to be displayed on the selected tab.
            file_type:          What type of report should be shown.
            path:               The relative path to the file.

        """

        self.tabs.set_value(tab_to_switch)
        full_path = str(Path(path).with_name(file_to_read))

        if report_type == "cli_file":
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    self.translate_file_displayer.content = f.read()
            except FileNotFoundError:
                self.translate_file_displayer.content = "File not found."
        elif report_type == "t_report":
            self.translate_file_displayer.content = self.kserver.get_report(self.imported_files_dict[full_path])
        else:
            self.import_file_displayer.content = self.database.get_import_rpt(file_to_read)
