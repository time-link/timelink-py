from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Timelink settings. Override them by creating a .timelink.env file in your home directory.

    """

    timelink_app_name: str = "Timelink"
    timelink_admin_email: str = "joaquim@uc.pt"
    timelink_users_db_type: str = "sqlite"
    timelink_users_db_name: str = "timelink_users.sqlite"
    timelink_app_url: str = "http://localhost:8008"
    timelink_users_db_path: str = ""
    timelink_admin_pwd: str = "admin"  # for startlette admin
    timelink_project_db_type: str = "sqlite"
    fief_main_user_email: str = ""
    fief_main_user_password: str = ""

    model_config = dict(env_file='~/.timelink.env')
