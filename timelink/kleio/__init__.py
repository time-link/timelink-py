# flake8: noqa: F401
from typing import List
from .kleio_server import KleioServer
from .schemas import KleioFile
from .schemas import ApiPermissions, TokenInfo
from .schemas import translation_status_enum
from .schemas import import_status_enum

api_permissions_normal: List[ApiPermissions] = [
    ApiPermissions.sources,
    ApiPermissions.kleioset,
    ApiPermissions.files,
    ApiPermissions.structures,
    ApiPermissions.translations,
    ApiPermissions.upload,
    ApiPermissions.delete,
    ApiPermissions.mkdir,
    ApiPermissions.rmdir,
]

token_info_normal: TokenInfo = TokenInfo(
    comment="An user able to translate, upload and delete files, and also create and remove directories, in specific sub-directoris in kleio-home",
    api=api_permissions_normal,
    structures="structures/reference_sources",
    sources="sources/reference_sources",
)
