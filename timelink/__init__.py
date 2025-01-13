"""Timelink Python package.

Timelink, formerly known as MHK (Micro History with Kleio)
is an information system
designed for processing person related
information collected from historical sources.

.. moduleauthor:: Joaquim Ramos de Carvalho



"""
import requests

from .api import models  # noqa: F401
from .api import database  # noqa: F401
from .api import views  # noqa: F401
from .api import schemas  # noqa: F401


__author__ = """Joaquim Ramos de Carvalho"""
__email__ = 'joaquimcarvalho@mpu.edu.mo'
__version__ = '1.1.16'

version = __version__


def get_latest_version(package_name="timelink"):
    """Get the latest version of a package from PyPI."""
    # Step 1: Fetch the package information from PyPI
    url = f'https://pypi.org/pypi/{package_name}/json'
    response = requests.get(url)

    # Step 2: Parse the JSON data
    if response.status_code == 200:
        data = response.json()
        latest_version = data['info']['version']
        return latest_version
    else:
        return None
