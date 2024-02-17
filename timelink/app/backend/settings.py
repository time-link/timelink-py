from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Timelink"
    admin_email: str = "joaquim@uc.pt"
    users_db_type: str = "sqlite"
    users_db_name: str = "timelink_users"
