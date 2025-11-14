from nicegui import ui


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
                github_dialog = ui.dialog()
                with github_dialog, ui.card().classes('w-64 h-64 items-center'):
                    ui.label("Sign up with GitHub").classes('text-lg font-semibold text-orange-500')
                    ui.markdown("We'll redirect you to GitHub to authorize your account.").classes('text-gray-500 text-center')

                    with ui.row():
                        ui.button(
                            "Continue", on_click=lambda: ui.notify("Redirecting to GitHub...")
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
