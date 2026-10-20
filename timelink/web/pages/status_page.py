from timelink.web.pages import navbar
from timelink.web import timelink_web_utils
from nicegui import ui, run, app
from contextlib import contextmanager
import asyncio


class StatusPage:

    """Currently used as a debug page to check for additional information."""
    def __init__(self, timelink_app, sources) -> None:
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server
        self.timelink_app = timelink_app
        self.sources = sources

        @ui.page('/project_admin')
        def page():
            self.status_page()

    def status_page(self):
        with navbar.header():
            ui.page_title("Project Administration")

            with ui.row():
                ui.markdown('#### **Project Administration**').classes('ml-2 text-orange-500')

            with self.timelink_app.users_db.session() as session:
                self.current_project = self.timelink_app.users_db.get_project_by_name(
                    self.timelink_app.current_project_name, session
                )
                self.current_project_id = self.current_project.id
                self.current_role = self.timelink_app.users_db.get_user_project_access(
                    int(app.storage.user["user_id"]), self.current_project_id, session
                ).access_level.value

            with ui.row():
                ui.label('You are viewing ').classes('ml-2 mb-4 text-lg font-bold text-orange-500')
                ui.label(self.timelink_app.current_project_name).classes('-ml-2 text-lg font-bold text-blue-500')
                ui.label('. Your role is').classes('-ml-4 text-lg font-bold text-orange-500')
                ui.label(f'{self.current_role}.').classes('-ml-3 text-lg font-bold text-blue-500')

            with self.timelink_app.users_db.session() as session:
                project_list = [
                    p.name for p in self.timelink_app.users_db.get_user_projects(
                        app.storage.user["user_id"], session
                    )
                ]
                with ui.row().classes("-mt-4 ml-4 items-center gap-2"):
                    ui.label('Switch Project:').classes('mr-5 font-bold text-orange-500')
                    ui.select(
                        project_list,
                        value=self.timelink_app.current_project_name,
                        on_change=lambda e: self.switch_project(e.value, project_list, session)
                    ).classes('text-blue-500 font-bold')

            btn_style = "w-80"

            with ui.row().classes("ml-4 mt-8"):
                if self.current_role in ("viewer", "colaborator", "admin", "manager"):
                    with ui.card():
                        with ui.column().classes('items-center justify-center'):
                            ui.label("Viewer Options").classes('font-bold text-lg text-orange-500 mb-4')
                            ui.button(
                                "Check Server Status",
                                on_click=lambda: timelink_web_utils.show_kleio_info(self.kserver)
                            ).classes(btn_style)
                            ui.button(
                                "Check Database Status",
                                on_click=lambda: timelink_web_utils.show_table(self.database)
                            ).classes(btn_style)
                            ui.button(
                                "Check Project Status",
                                on_click=lambda: timelink_web_utils.show_project_info(self.current_project)
                            ).classes(btn_style)

                if self.current_role in ("admin", "manager"):
                    with ui.card():
                        with ui.column().classes('items-center justify-center'):
                            ui.label("Manager Options").classes('font-bold text-lg text-orange-500 mb-4')
                            ui.button(
                                "Update Database from Sources",
                                on_click=lambda this_button: self.update_from_sources(this_button.sender)
                            ).classes(btn_style)
                            ui.button(
                                "Clean Translations",
                                on_click=lambda this_button: self.clean_translations(this_button.sender)
                            ).classes(btn_style)

                if self.current_role == "admin":
                    with ui.card():
                        with ui.column().classes('items-center justify-center'):
                            ui.label("Admin Options").classes('font-bold text-lg text-orange-500 mb-4')
                            ui.button(
                                "Add/Remove Users",
                                on_click=lambda: self.add_remove_users(self.current_project)
                            ).classes(btn_style)
                            ui.button(
                                "Change User Permissions",
                                on_click=lambda: self.manage_user_permissions(self.current_project)
                            ).classes(btn_style)

    @contextmanager
    def disable(self, button: ui.button):
        button.disable()
        try:
            yield
        finally:
            button.enable()

    async def update_from_sources(self, button: ui.button) -> None:
        """ Attempt to update database from sources."""
        with self.disable(button):
            ui.notify("Updating database from sources...")
            try:
                await asyncio.to_thread(timelink_web_utils.run_imports_sync, self.database)
                await run.io_bound(self.sources.refresh_imported_files)
                ui.notify("Done updating the database!", type="positive")
            except Exception as e:
                ui.notify(f"ERROR: Database import failed: {e}", type="negative")

    def run_clean_translations_sync(self):
        print("Attempting to clean translations...")
        self.kserver.translation_clean("", recurse="yes")
        print("Translations are clean!")

    async def clean_translations(self, button: ui.button) -> None:
        """ Attempt to clean translations."""
        with self.disable(button):
            ui.notify("Cleaning translations")
            try:
                await asyncio.to_thread(self.run_clean_translations_sync)
                await run.io_bound(self.sources.refresh_imported_files)
                ui.notify("Done clearing translations!", type="positive")
            except Exception as e:
                ui.notify(f"ERROR: Translation cleanup failed: {e}", type="negative")
                print(f"ERROR: Translation cleanup failed: {e}")

    def switch_project(self, project_name, project_list, session):
        """Switch to different project."""

        project = self.timelink_app.users_db.get_project_by_name(project_name, session)

        with ui.dialog() as dialog, ui.card().classes('items-center justify-center p-6'):
            ui.label("Switching projects...")
            ui.spinner(size='lg')
        dialog.open()

        async def run_setup():
            self.timelink_app.load_config_for_project_list(project_list, project)
            ui.navigate.reload()
            dialog.close()

        ui.timer(0.1, run_setup, once=True)

    def add_remove_users(self, project):
        """Add or remove users from the current project."""

        dialog = ui.dialog()
        with dialog, ui.card():
            ui.label(f'Users associated with {project.name}').classes(
                'text-lg font-bold text-orange-500 mb-4'
            )

            with self.timelink_app.users_db.session() as session:
                users_not_in_project = self.timelink_app.users_db.get_all_users_not_in_project(project.id, session)
                current = self.timelink_app.users_db.get_project_user_list(project.id, session)

            remove_list = set()
            add_list = set()

            # Remove current users
            user_column = ui.column().classes('gap-2')

            def refresh_users():
                user_column.clear()
                with user_column:
                    ui.label('Current Users').classes('font-bold text-orange-500 mt-2')
                    for u in current:
                        with ui.row().classes('w-full items-center justify-between'):
                            ui.label(u.name).classes('text-blue-500 font-bold')

                            def do_remove(_u=u):
                                remove_list.add(_u.id)
                                refresh_changes()
                            ui.button('Remove', on_click=do_remove).props('flat color=red')

            ui.separator()

            # Add user input
            ui.label('Add User').classes('font-bold text-orange-500 mt-2')
            name_map = {u.name: u for u in users_not_in_project}
            with ui.row().classes('items-center gap-2'):
                add_input = ui.select(
                    label='User\'s Name',
                    with_input=True,
                    options=list(name_map.keys())
                ).classes('w-48 font-bold text-blue-500')

                def add_click():
                    name = add_input.value
                    if name not in name_map:
                        ui.notify('User not found', type='negative')
                        return

                    u = name_map[name]
                    add_list.add(u.id)
                    add_input.set_value('')
                    refresh_changes()
                    ui.notify(f"{name} added to pending list", type='positive')

                ui.button('Add', on_click=add_click)

            ui.separator()

            changes_column = ui.column().classes('gap-2')

            def refresh_changes():
                changes_column.clear()
                with changes_column:
                    ui.label("To be removed:").classes('font-bold text-red-500')
                    if remove_list:
                        for uid in remove_list:
                            uname = next(u.name for u in current if u.id == uid)
                            ui.label(f"- {uname}").classes('text-red-400')
                    else:
                        ui.label("None").classes('text-gray-400')

                    ui.label("To be added:").classes('font-bold text-green-600 mt-2')
                    if add_list:
                        for uid in add_list:
                            uname = next(u.name for u in users_not_in_project if u.id == uid)
                            ui.label(f"+ {uname}").classes('text-green-500')
                    else:
                        ui.label("None").classes('text-gray-400')

            refresh_users()
            refresh_changes()
            changes_column
            ui.separator()

            # Apply changes
            def apply_changes():
                with self.timelink_app.users_db.session() as session:
                    for uid in remove_list:
                        self.timelink_app.users_db.remove_user_from_project(uid, project.id, session)
                    for uid in add_list:
                        self.timelink_app.users_db.set_user_project_access(uid, project.id, "viewer", session)
                    session.commit()

                ui.notify('Changes applied', type='positive')
                dialog.close()

            with ui.row().classes('justify-end mt-4 gap-2'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('Apply', on_click=apply_changes).props('color=green')

        dialog.open()

    def manage_user_permissions(self, project):
        """Modify a user's access level inside a project."""

        dialog = ui.dialog()
        with dialog, ui.card():
            ui.label(f'Manage Permissions for {project.name}').classes('text-lg font-bold text-orange-500 mb-4')

            with self.timelink_app.users_db.session() as session:
                users = self.timelink_app.users_db.get_project_user_list(project.id, session)

            user_names = {u.name: u for u in users}
            roles = ['viewer', 'colaborator', 'manager', 'admin']

            with ui.row().classes("w-full gap-2"):
                selected_user = ui.select(list(user_names.keys()), label='User').classes('font-bold text-blue-500 w-1/3')
                selected_role = ui.select(roles, label='New Role').classes('font-bold text-blue-500 ml-4 w-1/3')

            def save():
                uname = selected_user.value
                rname = selected_role.value
                if not uname or not rname:
                    ui.notify('Select both user and role', type='negative')
                    return

                u = user_names[uname]

                with self.timelink_app.users_db.session() as session:
                    self.timelink_app.users_db.set_user_project_access(u.id, project.id, rname, session)
                    session.commit()

                ui.notify('Permissions updated', type='positive')
                dialog.close()

            ui.separator()

            with ui.row().classes('justify-end mt-4 gap-2'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('Save', on_click=save).props('color=green')

        dialog.open()
