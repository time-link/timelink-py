from pydantic import BaseModel, AnyUrl
from timelink.kleio.kleio_server import KleioServer
from timelink.api.database import TimelinkDatabase


class Project(BaseModel):
    name: str
    kleioServerURL: AnyUrl
    DatabaseURL: AnyUrl


base_projects = [
    Project(name="tutorial",
            kleioServerURL="http://localhost:8088",
            DatabaseURL="http://localhost:5001"),
    Project(name="test-project",
            kleioServerURL="http://localhost:8088",
            DatabaseURL="http://localhost:5001")
]