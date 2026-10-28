from nicegui import ui, app
from fastapi import Request
import httpx
import os
import secrets
from timelink.web.pages import navbar
from timelink.web.models.user import User, UserProperty
from passlib.hash import argon2
from timelink.web import timelink_web_utils

# Register an OAuth app at https://github.com/settings/developers and
# set these env vars to enable GitHub login.
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")

# user property binding a local account to an immutable GitHub account id
GITHUB_ID_PROPERTY = "github:id"


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
        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            ui.notify("GitHub login is not configured on this server", type="negative")
            return ui.navigate.to("/login")
        # OAuth state nonce: proves the callback belongs to this browser
        state = secrets.token_urlsafe(16)
        app.storage.user['oauth_state'] = state
        authorize_url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={GITHUB_CLIENT_ID}&scope=user:email&state={state}"
        )
        return ui.navigate.to(authorize_url)

    async def finish_github_login(self, request: Request):

        # validate and consume the OAuth state nonce (login-CSRF defence)
        expected_state = app.storage.user.pop('oauth_state', None)
        if not expected_state or request.query_params.get("state") != expected_state:
            ui.notify("GitHub login failed: state mismatch", type="negative")
            return ui.navigate.to("/login")

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
        github_id = str(gh_user.get("id") or "")

        # Find/Create user. Accounts are bound to the immutable GitHub
        # account id — a nickname match alone is NOT proof of ownership.
        with self.timelink_app.users_db.session() as session:
            binding = (
                session.query(UserProperty)
                .filter(UserProperty.name == GITHUB_ID_PROPERTY,
                        UserProperty.value == github_id)
                .first()
            )
            user = binding.user if binding else None

            if not user:
                same_nickname = session.query(User).filter(User.nickname == username).first()
                if same_nickname is not None:
                    # a local account with this nickname exists but is not
                    # bound to this GitHub identity; do not sign it in
                    ui.notify(
                        f"A local account '{username}' already exists. Log in with "
                        "its password and link GitHub from account settings.",
                        type="negative",
                    )
                    return ui.navigate.to("/login")

                # random, unguessable password: password login is not
                # available for GitHub-created accounts
                hashed = argon2.hash(secrets.token_urlsafe(32))
                user = User(
                    name=name,
                    nickname=username,
                    email=email,
                    hashed_password=hashed,
                )
                self.timelink_app.users_db.add_user(user, session)
                session.flush()
                user.properties.append(
                    UserProperty(name=GITHUB_ID_PROPERTY, value=github_id)
                )
                session.commit()

                # Add user to Demo Project
                project_id = self.timelink_app.users_db.get_project_by_name("Demo project", session).id
                self.timelink_app.users_db.set_user_project_access(user.id, project_id, "viewer", session)
                session.commit()

            if getattr(user, 'disabled', False):
                ui.notify('This account is disabled', type="negative")
                return ui.navigate.to("/login")

            user_id = user.id

            # Store session
            app.storage.user.update({
                'username': user.name,
                'nickname': user.nickname,
                'authenticated': True,
                'is_admin': getattr(user, 'is_admin', False),
                'user_id': user_id
            })

            with ui.dialog() as dialog, ui.card().classes('items-center justify-center p-6'):
                ui.label("Loading user projects...")
                ui.spinner(size='lg')
            dialog.open()

            async def run_setup():
                try:
                    project_list = self.timelink_app.users_db.get_user_projects(user_id, session)
                    timelink_web_utils.setup_pages_and_database(
                        self.timelink_app, project_list)
                except Exception as e:
                    # never leave the user on an infinite spinner
                    print(f"GitHub login setup failed: {e}")
                    dialog.close()
                    ui.notify(f'Login failed during setup: {e}',
                              type='negative', close_button='OK',
                              multi_line=True)
                    return
                dialog.close()
                ui.navigate.to("/")

            ui.timer(0.1, run_setup, once=True)

    async def github_page(self):
        with navbar.header():
            ui.page_title("GitHub Login")
