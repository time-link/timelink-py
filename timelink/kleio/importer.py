import os
import sys
import time
from datetime import datetime

from pathlib import Path
from typing import Union
import platform
import urllib.request

from sqlalchemy.orm import Session
from sqlalchemy import func
from xml.sax import make_parser

from .sax_handler import SaxHandler
from .kleio_handler import KleioHandler


def import_from_xml(
    filespec: Union[str, Path], session: Session, options: dict = None
) -> dict:
    """Import data from file or url into a timelink-mhk database.

    The data file must be a XML file in the format exported by the ``kleio``
    translator.

    Arguments:
        filespec (str,Path): a file path, URL of a data file or path in a Kleio Server.
        session: a database session from TimelinkDatabase.session()
        options (dict): a dictionnary with options

           - 'return_stats':  if True import stats will be returned
           - 'kleio_url':  the url of kleio server;
           - 'kleio_token':  the authorization token for the kleio server.
           - 'mode':  the mode of the import, either 'TL'(Timelink) or 'MHK'

        If kleio_url and kleio_token are specified the data will be fetched from
        a KleioServer and the filespec should contain the "xml_path" of the file
        in the server (e.g. /rest/exports/reference_sources/varia/vereacao.xml) and
        the kleio_token will be inserted in the header for autentication

    Returns:
        If stats is True in options a dict with statistical information will be
        returned.

            - 'datetime': the time stamp of the start of the import
            - 'machine':  local machine name
            - 'file': path to imported file or url
            - 'import_time_seconds':  elapsed time during import
            - 'entities_processed': number of entities processed
            - 'entity_rate': number of entities processed per second
            - 'person_rate': number of persons (entities of class 'person')
            - 'nerrors': number of errors during import
            - 'errors': list of error messages

    Examples:
        Returned statistical information when stats=True
    ::

        {
        'datetime': '2022-01-02 18:11:12',
        'machine': 'joaquims-mbpr.local',
        'file': 'https://...b1685.xml',
        'import_time_seconds': 7.022288084030151,
        'entities_processed': 747,
        'entity_rate': 106.37558457603042,
        'person_rate': 27.483919441999827
        'nerrors': 0
        'errors': []
        }

        TODO: should use https when the kleio_url not local.
    """
    collect_stats = False
    kleio_url = None
    kleio_token = None
    mode = "TL"  # determines the database model TL=Timelink, MHK=MHK
    nentities_before = 0
    npersons_before = 0
    now = datetime.now()
    if options is not None and options.get("return_stats", False):
        collect_stats = True
    if options is not None and options.get("mode", None) is not None:
        mode = options.get("mode")
    if options is not None and options.get("kleio_url", None) is not None:
        kleio_url = options.get("kleio_url")
    if options is not None and options.get("kleio_token", None) is not None:
        kleio_token = options.get("kleio_token")

    kleio_handler = KleioHandler(session, mode=mode)
    sax_handler = SaxHandler(kleio_handler)
    parser = make_parser()
    parser.setContentHandler(sax_handler)
    start = time.time()
    if collect_stats:
        nentities_before = session.query(
            func.count(kleio_handler.entity_model.id)  # pylint: disable=not-callable
        ).scalar()
        npersons_before = session.query(
            func.count(kleio_handler.person_model.id)  # pylint: disable=not-callable
        ).scalar()

    if kleio_url is not None and kleio_token is not None:
        headers = {"Authorization": f"Bearer {kleio_token}"}
        server_url = f"{kleio_url}{filespec}"
        req = urllib.request.Request(server_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as source:
            parser.parse(source)
    elif kleio_token is not None or kleio_url is not None:
        # this means that one of the options is missing
        raise ValueError(
            "Both kleio_url and kleio_token must be specified to fetch from kleio server"
        )
    elif isinstance(filespec, os.PathLike):
        source = os.fspath(filespec)
        parser.parse(source)
    else:
        source = filespec
        parser.parse(source)

    end = time.time()
    if collect_stats:
        machine = platform.node()
        nentities = session.query(func.count(kleio_handler.entity_model.id)).scalar()  # pylint: disable=not-callable
        npersons = session.query(func.count(kleio_handler.person_model.id)).scalar()  # pylint: disable=not-callable
        erate = (nentities - nentities_before) / (end - start)
        prate = (npersons - npersons_before) / (end - start)
        stats = {
            "datetime": now.timestamp(),
            "machine": machine,
            "database": session.bind.url,
            "file": filespec,
            "import_time_seconds": end - start,
            "entities_processed": nentities - nentities_before,
            "entity_rate": erate,
            "person_rate": prate,
            "nerrors": len(kleio_handler.errors),
            "errors": kleio_handler.errors,
        }
        return stats


if (
    __name__ == "__main__"
):  # Not sure this works, where is the session for KleioHandler?
    saxParser = make_parser()
    kleioHandler = KleioHandler(None, mode="TL")
    saxParser.setContentHandler(SaxHandler(kleioHandler))
    saxParser.parse(sys.argv[1])
