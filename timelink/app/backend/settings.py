from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Timelink settings."""

    timelink_app_name: str = "Timelink"
    timelink_admin_email: str = "joaquim@uc.pt"
    timelink_users_db_type: str = "sqlite"
    timelink_users_db_name: str = "timelink_users"
    timelink_users_db_path: str = ""
    timelink_admin_pwd: str = "adminpwd"
