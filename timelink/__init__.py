"""Timelink Python package.

Timelink, formerly known as MHK (Micro History with Kleio)
is an information system
designed for processing person related
information collected from historical sources.

.. moduleauthor:: Joaquim Ramos de Carvalho



"""
from .api import database  # noqa: F401
from .api import models  # noqa: F401
from .api import views  # noqa: F401
from .api import schemas  # noqa: F401


__author__ = """Joaquim Ramos de Carvalho"""
__email__ = 'joaquim@uc.pt'
__version__ = '1.1.11'

version = __version__
