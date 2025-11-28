from nicegui import ui, app
from typing import Optional
from fastapi.responses import RedirectResponse
from timelink.web.models.user import User
from passlib.hash import argon2
from timelink.web import timelink_web_utils


class Login:

    def __init__(self, timelink_app) -> None:
        self.timelink_app = timelink_app
        self.user_database = timelink_app.users_db
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server

        @ui.page('/login')
        async def register(redirect_to: str = '/'):
            await self.login_page(redirect_to)

    async def login_page(self, redirect_to: str = '/') -> Optional[RedirectResponse]:

        ui.page_title("Timelink Web Login")
        app.storage.user.clear()

        with ui.header().classes("w-full justify-center"):
            ui.markdown('#### **Welcome to the Timelink Web Interface!**').classes('mb-4')

        def try_login() -> None:
            if not username.value or not password.value:
                ui.notify("Please enter both username and password", color="negative")
                return

            with self.user_database.session() as session:
                user = session.query(User).filter(User.nickname == username.value).first()
                if user and argon2.verify(password.value, user.hashed_password):
                    app.storage.user.update({
                        'username': user.name,
                        'authenticated': True,
                        'is_admin': getattr(user, 'is_admin', False),
                        'user_id': user.id
                    })
                    project_list = self.user_database.get_user_projects(user.id, session)

                    with ui.dialog() as dialog, ui.card().classes('items-center justify-center p-6'):
                        ui.label("Loading user projects...")
                        ui.spinner(size='lg')
                    dialog.open()

                    async def run_setup():
                        timelink_web_utils.setup_pages_and_database(self.timelink_app, project_list)
                        dialog.close()

                    ui.timer(0.1, run_setup, once=True)

                else:
                    ui.notify('Wrong username or password', color='negative')

        if app.storage.user.get('authenticated', False):
            return RedirectResponse('/')

        def continue_as_guest():
            with self.user_database.session() as session:
                user = session.query(User).filter(User.nickname == "guest").first()
                if user:
                    app.storage.user.update({
                        'username': user.name,
                        'authenticated': True,
                        'is_admin': False,
                        'user_id': user.id
                    })
                    project_list = self.user_database.get_user_projects(user.id, session)

                    with ui.dialog() as dialog, ui.card().classes('items-center justify-center p-6'):
                        ui.label("Loading guest projects...")
                        ui.spinner(size='lg')
                    dialog.open()

                    async def run_setup():
                        timelink_web_utils.setup_pages_and_database(self.timelink_app, project_list)
                        dialog.close()

                    ui.timer(0.1, run_setup, once=True)

        with ui.column().classes('absolute-center items-center gap-4'):
            with ui.card().classes('items-center'):
                ui.label("Login").classes("text-lg font-semibold text-orange-500")
                username = ui.input("Username").classes("w-full mb-2")
                password = ui.input(
                    "Password", password=True, password_toggle_button=True
                ).classes("w-full mb-4").on('keydown.enter', try_login)

                with ui.row().classes("w-full justify-between"):
                    ui.button("Login", on_click=lambda: try_login()).classes("bg-blue-500 text-white")
                    ui.button("Continue as Guest", on_click=continue_as_guest).classes("bg-gray-400 text-white")

                ui.separator()

                github_dialog = ui.dialog()
                with github_dialog, ui.card().classes('items-center'):
                    ui.label("Sign up with GitHub").classes('text-lg font-semibold text-orange-500')
                    ui.markdown("We'll redirect you to GitHub to authorize your account.").classes('text-gray-500 text-center')

                    with ui.row():
                        ui.button(
                            "Continue", on_click=lambda: ui.navigate.to("/github/login")
                        ).classes('bg-orange-500 text-white')
                        ui.button("Cancel", on_click=github_dialog.close).classes('bg-gray-300')

                google_dialog = ui.dialog()
                with google_dialog, ui.card():
                    ui.label("Google login coming soon!").classes('text-orange-500 text-center')
                    ui.button('OK', on_click=google_dialog.close).classes('mt-2 bg-orange-500 text-white')
                with ui.row():
                    with ui.button(
                        on_click=github_dialog.open
                    ).classes(
                        'p-1 rounded-full bg-transparent hover:bg-gray-100 transition'
                    ):
                        ui.image(
                            'https://github.githubassets.com/assets/GitHub-Mark-ea2971cee799.png'
                        ).classes('w-12 rounded-full')
                    with ui.button(
                        on_click=google_dialog.open
                    ).classes(
                        'p-1 rounded-full bg-transparent hover:bg-gray-100 transition'
                    ):
                        ui.image(
                            'https://cdn.iconscout.com/icon/free/png-256/free-google-icon-svg-download-png-189813.png'
                        ).classes('w-12 rounded-full')

            ui.link("New account? Sign up here!", "/register")
