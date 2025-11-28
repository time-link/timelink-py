from nicegui import ui, app
from fastapi import Request
import httpx
from timelink.web.pages import navbar
from timelink.web.models.user import User
from passlib.hash import argon2
from timelink.web import timelink_web_utils

GITHUB_CLIENT_ID = "Ov23li2llB5KmHOoaBRe"
GITHUB_CLIENT_SECRET = "ce96a524f5c480a6238cbfed5990ff977276827b"


class GithubLoginPage:

    def __init__(self, timelink_app):
        self.timelink_app = timelink_app

        @ui.page('/github/login')
        async def github_redirect():
            return await self.start_github_login()

        @ui.page('/github/callback')
        async def github_callback(request: Request):
            return await self.finish_github_login(request)

    async def start_github_login(self):
        authorize_url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={GITHUB_CLIENT_ID}&scope=user:email"
        )
        return ui.navigate.to(authorize_url)

    async def finish_github_login(self, request: Request):

        code = request.query_params.get("code")
        if not code:
            return ui.notify("GitHub authentication failed", type="negative")

        # Get access token
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                },
            )
            token = token_res.json().get("access_token")

            # Fetch user info
            user_res = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {token}"}
            )
            gh_user = user_res.json()

            # Fetch user mail
            email_res = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {token}"}
            )
            emails = email_res.json()
            email = next((e["email"] for e in emails if e.get("primary")), None)

        username = gh_user.get("login")
        name = gh_user.get("name") or username

        # Find/Create user
        with self.timelink_app.users_db.session() as session:
            user = session.query(User).filter(User.nickname == username).first()

            if not user:
                hashed = argon2.hash(username + email)
                user = User(
                    name=name,
                    nickname=username,
                    email=email,
                    hashed_password=hashed,
                )
                self.timelink_app.users_db.add_user(user, session)
                session.commit()

                # Add user to Demo Project
                user_id = self.timelink_app.users_db.get_user_by_nickname(user.nickname, session).id
                project_id = self.timelink_app.users_db.get_project_by_name("Demo project", session).id

                self.timelink_app.users_db.set_user_project_access(user_id, project_id, "viewer", session)
                session.commit()

            else:
                user_id = user.id

            # Store session
            app.storage.user.update({
                'username': user.name,
                'authenticated': True,
                'is_admin': getattr(user, 'is_admin', False),
                'user_id': user_id
            })

            with ui.dialog() as dialog, ui.card().classes('items-center justify-center p-6'):
                ui.label("Loading user projects...")
                ui.spinner(size='lg')
            dialog.open()

            async def run_setup():
                project_list = self.timelink_app.users_db.get_user_projects(user_id, session)
                timelink_web_utils.setup_pages_and_database(self.timelink_app, project_list)
                dialog.close()
                ui.navigate.to("/")

            ui.timer(0.1, run_setup, once=True)

    async def github_page(self):
        with navbar.header():
            ui.page_title("GitHub Login")
