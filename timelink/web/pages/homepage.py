from timelink.web.pages import navbar
from timelink.web import timelink_web_utils

from nicegui import ui, app


class HomePage:

    def __init__(self, timelink_app) -> None:

        self.timelink_app = timelink_app

        @ui.page('/')
        def home_page():
            with navbar.header():
                ui.page_title("Timelink Web Home")

                # If the user is not redirected to login and is authenticated load the projects they're in.
                if not self.timelink_app.projects_loaded:
                    with self.timelink_app.users_db.session() as session:
                        project_list = self.timelink_app.users_db.get_user_projects(app.storage.user["user_id"], session)
                        timelink_web_utils.setup_pages_and_database(timelink_app, project_list)

                with ui.column().classes("absolute-center"):
                    ui.markdown(
                        f'#### **Welcome to the Timelink Web Interface, {app.storage.user["username"]}!**'
                    ).classes('text-orange-500')
                    ui.markdown(f'##### **You are browsing {self.timelink_app.current_project_name}!**').classes('text-orange-500')
                    with self.timelink_app.users_db.session() as session:
                        project_list = [
                            p.name for p in self.timelink_app.users_db.get_user_projects(
                                app.storage.user["user_id"], session
                            )
                        ]
                        ui.label('Switch Project:').classes('font-bold text-orange-500')
                        ui.select(
                            project_list,
                            label="Projects",
                            value=self.timelink_app.current_project_name,
                            on_change=lambda e: self.switch_project(e.value, project_list, session)
                        ).classes('w-64')

    def switch_project(self, project_name, project_list, session):
        """Switch to different project."""

        project = self.timelink_app.users_db.get_project_by_name(project_name, session)
        timelink_web_utils.setup_pages_and_database(self.timelink_app, project_list, project)
        ui.navigate.to("/")
