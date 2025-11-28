from nicegui import ui
from passlib.hash import argon2
from timelink.web.models.user import User


class RegisterPage:

    def __init__(self, timelink_app) -> None:

        self.timelink_app = timelink_app

        @ui.page('/register')
        async def register():
            await self.register_page()

    async def register_page(self):
        ui.page_title("Register")

        with ui.header().classes("w-full justify-center"):
            ui.markdown('#### **Welcome to the Timelink Web Interface!**')

        with ui.column().classes('-mt-10 absolute-center'):
            with ui.card().classes('items-center'):
                ui.label("Sign Up").classes("text-lg font-semibold mb-4 text-orange-500")

                name = ui.input(
                    "Name",
                    validation=lambda value: 'Please input something' if len(value) < 1 else None,
                ).classes("-mt-4 w-64")

                username = ui.input(
                    "Username",
                    validation=lambda value: 'Please input something' if len(value) < 1 else None
                ).classes("-mt-4 w-64")

                email = ui.input(
                    "Email",
                    validation=lambda value: 'Please input something' if len(value) < 1 else None
                ).classes("-mt-4 w-64")

                password = ui.input(
                    "Password",
                    validation=lambda value: 'Please input something' if len(value) < 1 else None,
                    password=True,
                    password_toggle_button=True
                ).classes("-mt-4 w-64")

                confirm_password = ui.input(
                    "Confirm Password",
                    validation=lambda value: 'Passwords do not match!' if value != password.value else None,
                    password=True, password_toggle_button=True
                ).classes("-mt-4 w-64")

                with ui.row():
                    ui.button(
                        "Create Account",
                        on_click=lambda: self.register_new_account(
                            name.value,
                            username.value,
                            email.value,
                            password.value,
                            confirm_password.value
                        )
                    ).classes("bg-orange-500 text-white")

                    ui.button(
                        "Back to login",
                        on_click=lambda: ui.navigate.to('/login')
                    ).classes("bg-orange-500 text-white")

    async def register_new_account(self, name, username, email, password, confirm_password):
        """Register a new account into the database and add the user to the guest project."""

        if not all([name, username, email, password]):
            ui.notify("All fields are required!", type="negative")
            return

        if password != confirm_password:
            ui.notify("Passwords do not match!", type="negative")
            return

        # Hash password before indexing
        hashed_password = argon2.hash(password)

        # Index into database and add to guest project

        new_user = User(
            name=name,
            nickname=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=False
        )

        with self.timelink_app.users_db.session() as session:
            try:
                # Add user to the database
                self.timelink_app.users_db.add_user(new_user, session)
                session.commit()

                # Get user id and demo project id
                user_id = self.timelink_app.users_db.get_user_by_nickname(new_user.nickname, session).id
                project_id = self.timelink_app.users_db.get_project_by_name("Demo project", session).id

                self.timelink_app.users_db.set_user_project_access(user_id, project_id, "viewer", session)
                session.commit()

                ui.notify("User registered successfully!", type="positive")
                ui.navigate.to("/")

            except Exception as e:
                print(e)
                ui.notify("Registration failed...", type="negative")
