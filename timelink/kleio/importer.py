import logging
import os
import sys
import time
import copy

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union
import platform

import urllib.request

from xml.sax import handler, make_parser, SAXParseException

from sqlalchemy import func, delete  # pylint: disable=import-error
from sqlalchemy.orm import Session  # pylint: disable=import-error
from sqlalchemy.exc import IntegrityError  # pylint: disable=import-error

from timelink.kleio.groups import KGroup, KElement
from timelink.mhk.models.db import pom_som_base_mappings as pom_som_base_mappingsMHK
from timelink.mhk.models.pom_som_mapper import (
    PomSomMapper as PomSomMapperMHK,
    PomClassAttributes as PomClassAttributesMHK,
)
from timelink.mhk.models.entity import Entity as EntityMHK
from timelink.mhk.models.person import Person as PersonMHK
from timelink.mhk.models.system import KleioImportedFile as KleioFileMHK

from timelink.api.models.base_mappings import (
    pom_som_base_mappings as pom_som_base_mappingsTL,
)
from timelink.api.models.pom_som_mapper import PomSomMapper as PomSomMapperTL
from timelink.api.models.pom_som_mapper import (
    PomClassAttributes as PomClassAttributesTL,
)
from timelink.api.models.base import Entity as EntityTL, Person as PersonTL
from timelink.api.models.system import KleioImportedFile as KleioFileTL


class KleioContext(Enum):
    """Kleio context enumeration"""

    START = (1,)
    KLEIO = (2,)
    CLASS = (3,)
    GROUP = (4,)
    ELEMENT = (5,)
    CORE = (6,)
    COMMENT = 7
    ORIGINAL = 8


class SaxHandler(handler.ContentHandler):
    """SAX Handler for Kleio XML files"""

    _context: KleioContext
    _current_class: Optional[PomSomMapperTL | PomSomMapperMHK]
    _current_class_attrs: List[PomClassAttributesTL | PomClassAttributesMHK]
    _current_group: Optional[KGroup]
    _current_element: Optional[KElement]
    _current_entry: str

    def __init__(self, kleio_handler):
        handler.ContentHandler.__init__(self)
        self._kleio_handler = kleio_handler

    def startDocument(self):
        self._context = KleioContext.START
        self._current_class = None
        self._current_class_attrs = []
        self._current_group = None
        self._current_element = None
        self._current_entry = ""

    def endDocument(self):
        self._kleio_handler.endKleioFile()

    def startElement(self, name: str, attrs):
        #  https://stackoverflow.com/questions/15477363/xml-sax-parser-and-line-numbers-etc
        loc = self._locator
        ename = name.upper()
        if ename == "KLEIO":
            self._kleio_handler.newKleioFile(attrs)
            self._context = KleioContext.KLEIO
        elif ename == "CLASS":
            # <CLASS NAME="source" SUPER="entity"
            #       TABLE="sources" GROUP="fonte">
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    exception=None,
                    locator=loc,
                    msg="CLASS out of context, should be inside KLEIO element",
                )
            self._current_class = self._kleio_handler.pom_som_mapper(
                id=attrs["NAME"],
                super_class=attrs["SUPER"],
                table_name=attrs["TABLE"],
                group_name=attrs["GROUP"],
            )
            self._current_class_attrs = []
            self._context = KleioContext.CLASS

        elif ename == "ATTRIBUTE":
            #  <ATTRIBUTE NAME="id"
            #       COLUMN="id"
            #       CLASS="id"
            #       TYPE="varchar"
            #       SIZE="64"
            #       PRECISION="0"
            #       PKEY="1" >
            #   </ATTRIBUTE>
            if self._context != KleioContext.CLASS:
                raise SAXParseException(
                    "ATTRIBUTE out of context, should be inside CLASS element",
                    None,
                    loc,
                )
            new_attribute = self._kleio_handler.pom_class_attributes()
            new_attribute.the_class = self._current_class.id
            new_attribute.name = attrs["NAME"]
            new_attribute.colname = attrs["COLUMN"]
            new_attribute.colclass = attrs["CLASS"]
            new_attribute.coltype = attrs["TYPE"]
            new_attribute.colsize = int(attrs["SIZE"])
            new_attribute.colprecision = int(attrs["PRECISION"])
            new_attribute.pkey = int(attrs["PKEY"])

            self._current_class_attrs.append(new_attribute)

        elif ename == "GROUP":
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    "GROUP out of context, should be inside KLEIO element", None, loc
                )
            # <GROUP ID="coja-rol-1841" NAME="fonte"
            #        CLASS="source" ORDER="1" LEVEL="1" LINE="4">
            id = attrs["ID"]
            name = attrs["NAME"]
            the_class = attrs["CLASS"]
            order = attrs["ORDER"]
            level = attrs["LEVEL"]
            line = attrs["LINE"]

            # Mal [? porquê?]
            self._current_group = KGroup()
            self._current_group.id = id
            self._current_group._name = name
            self._current_group._pom_class_id = the_class
            self._current_group._order = int(order)
            self._current_group.level = int(level)
            self._current_group.line = int(line)
            self._context = KleioContext.GROUP

        elif ename == "ELEMENT":
            if self._context != KleioContext.GROUP:
                raise SAXParseException(
                    "ELEMENT out of context, should be inside GROUP element",
                    exception=None,
                    locator=loc,
                )
            # <ELEMENT NAME="id" CLASS="id">
            #       <core>r1775-f1-per1</core></ELEMENT>

            elname = attrs["NAME"]
            self._current_group.allow_as_element(elname)
            self._current_element = KElement(elname, None)
            self._current_element.element_class = attrs["CLASS"]
            self._context = KleioContext.ELEMENT

        elif ename == "CORE":
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "CORE out of context, should be inside ELEMENT element",
                    exception=None,
                    locator=loc,
                )
            self._context = KleioContext.CORE
            self._current_entry = ""

        elif ename == "COMMENT":
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "COMMENT out of context, should be inside ELEMENT element",
                    exception=None,
                    locator=loc,
                )
            self._context = KleioContext.COMMENT
            self._current_entry = ""

        elif ename == "ORIGINAL":
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "ORIGINAL out of context, should be inside ELEMENT element",
                    exception=None,
                    locator=loc,
                )
            self._context = KleioContext.ORIGINAL
            self._current_entry = ""

        elif ename == "RELATION":
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    "GROUP out of context, should be inside KLEIO element",
                    exception=None,
                    locator=loc,
                )
            self._kleio_handler.newRelation(attrs)
        else:
            raise SAXParseException(
                f"Unexpected element in Kleio file: {ename}",
                exception=None,
                locator=loc,
            )

    def endElement(self, name):
        ename = name.upper()

        if ename == "GROUP":
            self._kleio_handler.newGroup(self._current_group)
            self._context = KleioContext.KLEIO
            self._current_group = None

        elif ename == "CLASS":
            self._kleio_handler.newClass(self._current_class, self._current_class_attrs)
            self._context = KleioContext.KLEIO

        elif ename == "ATTRIBUTE":
            self._context = KleioContext.CLASS

        elif ename == "ELEMENT":
            self._current_group[self._current_element.name] = self._current_element

            self._context = KleioContext.GROUP

        elif ename in ["CORE", "COMMENT", "ORIGINAL"]:
            if ename == "CORE":
                if self._current_element.core is None:
                    self._current_element.core = self._current_entry
            if ename == "COMMENT":
                if self._current_element.comment is None:
                    self._current_element.comment = self._current_entry
            if ename == "ORIGINAL":
                if self._current_element.original is None:
                    self._current_element.original = self._current_entry
            self._context = KleioContext.ELEMENT

    def characters(self, content):
        self._current_entry = self._current_entry + content

    def ignorableWhitespace(self, whitespace):
        pass

    def processingInstruction(self, target, data):
        pass


class KleioHandler:
    pom_som_base_mappings = None
    pom_som_mapper = None
    pom_class_attributes = None
    entity_model = None
    person_model = None
    kleio_file_model = None
    model_type: str = None
    postponed_relations = []
    errors = []
    warnings = []
    kleio_file_origin = None
    kleio_file = None
    kleio_file_name = None
    kleio_structure = None
    kleio_translator = None
    kleio_when = None
    kleio_context = None
    pom_som_cache = dict()

    def __init__(self, session, mode="TL"):
        """
        Arguments:
            session: a SQLAlchemy session
            mode: the mode of the import, either 'TL'(Timelink) or 'MHK'

        """
        self.session = session
        if mode == "TL":
            self.pom_som_base_mappings = pom_som_base_mappingsTL
            self.pom_som_mapper = PomSomMapperTL
            self.pom_class_attributes = PomClassAttributesTL
            self.pom_class_attributes = PomClassAttributesTL
            self.entity_model = EntityTL
            self.person_model = PersonTL
            self.kleio_file_model = KleioFileTL
            self.model_type = "TL"
        elif mode == "MHK":
            self.pom_som_base_mappings = pom_som_base_mappingsMHK
            self.pom_som_mapper = PomSomMapperMHK
            self.pom_class_attributes = PomClassAttributesMHK
            self.entity_model = EntityMHK
            self.person_model = PersonMHK
            self.kleio_file_model = KleioFileMHK
            self.model_type = "MHK"
        else:
            raise ValueError(f"Unknown mode {mode}")

    def newKleioFile(self, attrs):
        # <KLEIO STRUCTURE="/kleio-home/system/conf/kleio/stru/gacto2.str"
        # SOURCE="/kleio-home/sources/soure-fontes/sources/1685-1720/baptismos/b1685.cli"
        # TRANSLATOR="gactoxml2.str"
        # WHEN="2020-8-18 17:10:32"
        # OBS="" SPACE="">

        self.session.commit()
        self.postponed_relations = []
        self.errors = []
        self.warnings = []
        self.kleio_file = attrs["SOURCE"]
        # extract name of file from path
        self.kleio_file_name = self.kleio_file.split("/")[-1]
        self.kleio_structure = attrs["STRUCTURE"]
        self.kleio_translator = attrs["TRANSLATOR"]
        self.kleio_when = attrs["WHEN"]
        self.pom_som_cache = dict()
        logging.debug("Kleio file: %s", self.kleio_file)
        logging.debug("Kleio structure: %s", self.kleio_structure)
        logging.debug("Kleio translator: %s", self.kleio_translator)
        logging.debug("Kleio when: %s", self.kleio_when)

    def newClass(
        self,
        psm: PomSomMapperTL | PomSomMapperMHK,
        attrs: List[PomClassAttributesTL | PomClassAttributesMHK],
    ):
        if psm.id in self.pom_som_base_mappings.keys():
            # we do not allow redefining of base mappings
            logging.debug("Skipping base mapping %s", psm.id)
            return

        session = self.session

        # check if we have this class defined in the database.
        existing_psm: PomSomMapperTL | PomSomMapperMHK = session.get(
            self.pom_som_mapper, psm.id
        )
        if existing_psm is not None:  # class exists: delete, insert again
            try:
                logging.debug("Deleting existing class %s", psm.id)
                session.commit()
                stmt = delete(self.pom_class_attributes).where(
                    self.pom_class_attributes.the_class == psm.id
                )
                session.execute(stmt)
                session.delete(existing_psm)
                session.commit()
            except Exception as e:
                session.rollback()
                self.errors.append(
                    f"ERROR: deleting class {psm.id}: {e.__class__.__name__}: {e}"
                )

        # now we add the new mapping
        try:
            logging.debug("Adding class %s", psm.id)
            session.add(psm)
            for class_attr in attrs:
                session.add(class_attr)
            session.commit()
        except Exception as e:
            session.rollback()
            self.errors.append(
                f"ERROR: adding class {psm.id}: {e.__class__.__name__}: {e}"
            )
        # ensure that the table and ORM classes are created
        try:
            psm.ensure_mapping(session)
            session.commit()
        except Exception as e:
            session.rollback()
            self.errors.append(
                f"ERROR: creating ORM mapping for class {psm.id}: {e.__class__.__name__}: {e}"
            )

    def newGroup(self, group: KGroup):
        # get the PomSomMapper
        # pass storeKGroup
        pom_mapper_for_group: PomSomMapperTL | PomSomMapperMHK
        try:
            if group.pom_class_id in self.pom_som_cache.keys():
                pom_mapper_for_group = self.pom_som_cache[group.pom_class_id]
            else:
                pom_mapper_for_group = self.pom_som_mapper.get_pom_class(
                    group.pom_class_id, self.session
                )
            if pom_mapper_for_group is None:
                raise ValueError(
                    f"Could not find PomSomMapper for class {group.pom_class_id}"
                )
            self.pom_som_cache[group.pom_class_id] = pom_mapper_for_group
        except Exception as exc:
            self.errors.append(
                f"ERROR: {self.kleio_file_name} {str(group.line)}"
                f" finding PomSomMapper for class "
                f"{group.pom_class_id}: {exc.__class__.__name__}: {exc}"
            )
            return

        if group.pom_class_id == "act":
            logging.debug(f"{group._name}${group.id}")

        if pom_mapper_for_group.id == "relation":
            # it can happen that the destination of a relation
            #  is not yet in the database (forward reference in relation)
            #  In this case we postpone the storing of the relation
            # until the end of file
            exits_dest_rel = self.session.get(
                self.entity_model, group.get_element_for_column("destination").core
            )
            if exits_dest_rel is None:
                self.postponed_relations.append(
                    (pom_mapper_for_group.id, copy.deepcopy(group))
                )
            else:
                try:
                    pom_mapper_for_group.store_KGroup(group, self.session)
                except Exception as exc:
                    self.session.rollback()
                    self.errors.append(
                        f"ERROR: {self.kleio_file_name} {str(group.line)} "
                        f"storing group {group.kname}${group.id}: "
                        f"{exc.__class__.__name__}: {exc}"
                    )
                    self.session.rollback()
        else:
            try:
                pom_mapper_for_group.store_KGroup(group, self.session)
            except IntegrityError as ierror:
                self.errors.append(
                    f"ERROR: {self.kleio_file_name} line {str(group.line)} "
                    f"** integrity error {group.kname}${group.id}: {ierror}"
                )
                self.session.rollback()

            except Exception as exc:
                self.session.rollback()
                self.errors.append(
                    f"ERROR: {self.kleio_file_name} line {str(group.line)} "
                    f"storing group {group.kname}${group.id}: {exc.__class__.__name__}: {exc}"
                )

    def newRelation(self, attrs):
        pass

    def endKleioFile(self):
        """Process end of file: process postponed relations"""
        # store postponed relations
        postponed = len(self.postponed_relations)
        if postponed > 0:
            log = f"Storing {postponed} postponed relations"
            logging.info(log)
        for pom_mapper_id, group in self.postponed_relations:
            pom_mapper = self.pom_som_mapper.get_pom_class(pom_mapper_id, self.session)
            try:
                pom_mapper.store_KGroup(group, self.session)
                self.session.commit()
            except IntegrityError as ierror:
                self.errors.append(
                    f"ERROR: {self.kleio_file_name} {str(group.line)} "
                    f"storing {group.to_kleio()}\n {ierror}"
                )
                self.session.rollback()
            except Exception as exc:
                self.errors.append(
                    f"ERROR: {self.kleio_file_name} {str(group.line)} "
                    f"storing {group.to_kleio()}\n {exc.__class__.__name__}: {exc}"
                )
                self.session.rollback()
        self.postponed_relations = []
        # store information on kleio file import
        kfile = self.kleio_file_model(
            path=self.kleio_file,  # TODO: #20 should remove /Kleio-home from path
            name=self.kleio_file_name,
            structure=self.kleio_structure,
            translator=self.kleio_translator,
            # convert date from "2020-8-18 17:10:32" format
            # to datetime object
            translation_date=datetime.strptime(self.kleio_when, "%Y-%m-%d %H:%M:%S"),
            nerrors=len(self.errors),
            nwarnings=len(self.warnings),
        )
        if len(self.errors) > 0:
            s = "\n\n".join(self.errors)
        else:
            s = "No errors"
        kfile.error_rpt = s
        if len(self.warnings) > 0:
            s = "\n\n".join(self.warnings)
        else:
            s = "No warnings"
        kfile.warning_rpt = s
        kfile.imported = datetime.now(timezone.utc)
        kfile.imported_string = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )
        kfile_exists = self.session.get(self.kleio_file_model, kfile.path)
        if kfile_exists is not None:
            self.session.delete(kfile_exists)
            self.session.commit()
        self.session.add(kfile)
        self.session.commit()


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
            func.count(kleio_handler.entity_model.id)
        ).scalar()
        npersons_before = session.query(
            func.count(kleio_handler.person_model.id)
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
        nentities = session.query(func.count(kleio_handler.entity_model.id)).scalar()
        npersons = session.query(func.count(kleio_handler.person_model.id)).scalar()
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
