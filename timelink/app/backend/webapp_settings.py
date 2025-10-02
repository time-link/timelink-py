from pydantic_settings import BaseSettings


class WebAppSettings(BaseSettings):
    """Timelink settings.

    Check https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    for details.

    Sample usage:

        settings = WebAppSettings(timelink_admin_pwd="xpto", time_user_db_type="postgres")

    Note that values in environment variables with the same name as fields
    in this class with override the default values defined here.

    """

    timelink_app_name: str = "Timelink"
    timelink_admin_email: str = "joaquim@uc.pt"
    timelink_users_db_type: str = "sqlite"
    timelink_users_db_name: str = "timelink_users.sqlite"
    timelink_app_url: str = "http://localhost:8008"
    timelink_users_db_path: str = ""
    timelink_admin_pwd: str = None
    timelink_solr_url: str = "http://localhost:8983"
