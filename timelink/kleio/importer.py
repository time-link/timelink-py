import os
import sys
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union
import platform
from xml.sax import handler, make_parser, SAXParseException

from sqlalchemy import select, func  # pylint: disable=import-error
from sqlalchemy.orm import Session   # pylint: disable=import-error

from timelink.kleio.groups import KGroup, KElement
from timelink.mhk.models.db import pom_som_base_mappings as pom_som_base_mappingsMHK
from timelink.mhk.models.pom_som_mapper import (PomSomMapper as PomSomMapperMHK,
                                                PomClassAttributes as PomClassAttributesMHK)
from timelink.mhk.models.entity import Entity as EntityMHK
from timelink.mhk.models.person import Person as PersonMHK

from timelink.api.models.base_mappings import pom_som_base_mappings as pom_som_base_mappingsTL
from timelink.api.models.pom_som_mapper import (PomSomMapper as PomSomMapperTL,
                                                PomClassAttributes as PomClassAttributesTL)
from timelink.api.models.base import Entity as EntityTL, Person as PersonTL


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
    """SAX Handler for Kleio XML files """
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
                    msg="CLASS out of context, should be inside KLEIO element"
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
                    loc
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
                    "GROUP out of context, should be inside KLEIO element",
                    None,
                    loc)
            # <GROUP ID="coja-rol-1841" NAME="fonte"
            #        CLASS="source" ORDER="1" LEVEL="1" LINE="4">
            id = attrs['ID']
            name = attrs['NAME']
            the_class = attrs['CLASS']
            order = attrs['ORDER']
            level = attrs['LEVEL']
            line = attrs['LINE']

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
                    locator=loc)
            # <ELEMENT NAME="id" CLASS="id">
            #       <core>r1775-f1-per1</core></ELEMENT>

            elname = attrs['NAME']
            self._current_group.allow_as_element(elname)
            self._current_element = KElement(elname, None)
            self._current_element.element_class = attrs["CLASS"]
            self._context = KleioContext.ELEMENT

        elif ename == "CORE":
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "CORE out of context, should be inside ELEMENT element",
                    exception=None,
                    locator=loc
                )
            self._context = KleioContext.CORE
            self._current_entry = ""

        elif ename == "COMMENT":
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "COMMENT out of context, should be inside ELEMENT element",
                    exception=None,
                    locator=loc
                )
            self._context = KleioContext.COMMENT
            self._current_entry = ""

        elif ename == "ORIGINAL":
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "ORIGINAL out of context, should be inside ELEMENT element",
                    exception=None,
                    locator=loc)
            self._context = KleioContext.ORIGINAL
            self._current_entry = ""

        elif ename == "RELATION":
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    "GROUP out of context, should be inside KLEIO element",
                    exception=None,
                    locator=loc
                )
            self._kleio_handler.newRelation(attrs)
        else:
            raise SAXParseException(
                f"Unexpected element in Kleio file: {ename}",
                exception=None,
                locator=loc)

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
    model_tpye: str = None

    def __init__(self, session, mode="TL"):
        self.session = session
        if mode == "TL":
            self.pom_som_base_mappings = pom_som_base_mappingsTL
            self.pom_som_mapper = PomSomMapperTL
            self.pom_class_attributes = PomClassAttributesTL
            self.pom_class_attributes = PomClassAttributesTL
            self.entity_model = EntityTL
            self.person_model = PersonTL
            self.model_tpye = "TL"
        elif mode == "MHK":
            self.pom_som_base_mappings = pom_som_base_mappingsMHK
            self.pom_som_mapper = PomSomMapperMHK
            self.pom_class_attributes = PomClassAttributesMHK
            self.entity_model = EntityMHK
            self.person_model = PersonMHK
            self.model_tpye = "MHK"
        else:
            raise ValueError(f"Unknown mode {mode}")

    def newKleioFile(self, attrs):
        self.session.commit()

    def newClass(self, psm: PomSomMapperTL | PomSomMapperMHK,
                 attrs: List[PomClassAttributesTL | PomClassAttributesMHK]):
        if psm.id in self.pom_som_base_mappings.keys():
            # we do not allow redefining of base mappings
            return

        session = self.session

        class_attr: self.pom_class_attributes
        # check if we have this class defined in the database.
        existing_psm: PomSomMapperTL | PomSomMapperMHK = session.get(
            self.pom_som_mapper, psm.id)
        if existing_psm is not None:  # class exists: delete, insert again
            existing_attrs: list = \
                session.execute(
                    select(self.pom_class_attributes).filter_by(the_class=psm.id))
            for class_attr in existing_attrs:
                session.delete(class_attr)
            session.delete(existing_psm)

        # now we add the new mapping
        session.add(psm)
        for class_attr in attrs:
            session.add(class_attr)

        session.commit()
        # ensure that the table and ORM classes are created
        psm.ensure_mapping(session)
        session.commit()

    def newGroup(self, group: KGroup):
        # get the PomSomMapper
        # pass storeKGroup
        str(group)  # for debugging
        pom_mapper_for_group = self.pom_som_mapper.get_pom_class(
            group.pom_class_id, self.session
        )
        pom_mapper_for_group.store_KGroup(group, self.session)

    def newRelation(self, attrs):
        pass

    def endKleioFile(self):
        self.session.close()


def import_from_xml(
    filespec: Union[str, Path], session: Session, options: dict = None
) -> dict:
    """Import data from file or url into a timelink-mhk database.

    The data file must be a XML file in the format exported by the ``kleio``
    translator.

    Arguments:
        filespec (str,Path): a file path or URL of a data file.
        conn_string (str): SQLAlchemy connection string to database.
        options (dict): a dictionnary with options

           - 'stats':  if True import stats will be returned
           - 'kleio_url':  the url of kleio server;
           - 'kleio_token':  the authorization token for the kleio server.
           - 'mode':  the mode of the import, either 'TL'(Timelink) or 'MHK'

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
        }


    Warning:
        The option to fetch the file from a ``kleio`` server with an
        authorization token is not implemented.

    """
    collect_stats = False
    mode = "TL"  # determines the database model TL=Timelink, MHK=MHK
    nentities_before = 0
    npersons_before = 0
    now = datetime.now()
    if options is not None and options.get("return_stats", False):
        collect_stats = True
    if options is not None and options.get("mode", None) is not None:
        mode = options.get("mode")

    kh = KleioHandler(session, mode=mode)
    sax_handler = SaxHandler(kh)
    parser = make_parser()
    parser.setContentHandler(sax_handler)
    start = time.time()
    if collect_stats:
        nentities_before = session.query(func.count(kh.entity_model.id)).scalar()
        npersons_before = session.query(func.count(kh.person_model.id)).scalar()

    # TODO implement fetching from kleio server
    if isinstance(filespec, os.PathLike):
        source = os.fspath(filespec)
    else:
        source = filespec

    parser.parse(source)

    end = time.time()
    if collect_stats:
        machine = platform.node()
        nentities = session.query(func.count(kh.entity_model.id)).scalar()
        npersons = session.query(func.count(kh.person_model.id)).scalar()
        erate = (nentities - nentities_before) / (end - start)
        prate = (npersons - npersons_before) / (end - start)
        stats = {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "machine": machine,
            "file": filespec,
            "import_time_seconds": end - start,
            "entities_processed": nentities - nentities_before,
            "entity_rate": erate,
            "person_rate": prate,
        }
        return stats


if __name__ == "__main__":  # Not sure this works, where is the session for KleioHandler?
    parser = make_parser()
    kh = KleioHandler(None, mode="TL")
    parser.setContentHandler(SaxHandler(kh))
    parser.parse(sys.argv[1])
