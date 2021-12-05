import sys, string
from enum import Enum
from typing import List

from xml.sax import saxutils, handler, make_parser, SAXParseException

from sqlalchemy import select
from sqlalchemy.orm import Session

from timelink.kleio.groups import KGroup, KElement
from timelink.mhk.models.db_system import DBSystem, pom_som_base_mappings
from timelink.mhk.models.pom_som_mapper import PomSomMapper, PomClassAttributes


class KleioContext(Enum):
    START = 1,
    KLEIO = 2,
    CLASS = 3,
    GROUP = 4,
    ELEMENT = 5,
    CORE = 6,
    COMMENT = 7
    ORIGINAL = 8


class SaxHandler(handler.ContentHandler):
    _context: str
    _current_class: PomSomMapper
    _current_class_attrs: List[PomClassAttributes]
    _current_group: KGroup
    _current_element: KElement
    _current_entry: str

    def __init__(self, kleio_handler, out=sys.stdout):
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
        ename = name.upper()
        if ename == "KLEIO":
            self._kleio_handler.newKleioFile(attrs)
            self._context = KleioContext.KLEIO
        elif ename == "CLASS":
            # <CLASS NAME="source" SUPER="entity" TABLE="sources" GROUP="fonte">
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    "CLASS out of context, should be inside KLEIO element")
            self._current_class = PomSomMapper(id=attrs['NAME'],
                                               super_class=attrs['SUPER'],
                                               table_name=attrs['TABLE'],
                                               class_group=attrs['GROUP'])
            self._context = KleioContext.CLASS

        elif ename == 'ATTRIBUTE':
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
                    "ATTRIBUTE out of context, should be inside CLASS element")
            new_attribute = PomClassAttributes()
            new_attribute.the_class = self._current_class.id
            new_attribute.name = attrs['NAME']
            new_attribute.colname = attrs['COLUMN']
            new_attribute.colclass = attrs['CLASS']
            new_attribute.coltype = attrs['TYPE']
            new_attribute.colsize = int(attrs['SIZE'])
            new_attribute.colprecision = int(attrs['PRECISION'])
            new_attribute.pkey = int(attrs['PKEY'])

            self._current_class_attrs.append(new_attribute)

        elif ename == "GROUP":
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    "GROUP out of context, should be inside KLEIO element")
            # <GROUP ID="coja-rol-1841" NAME="fonte" CLASS="source" ORDER="1" LEVEL="1" LINE="4">
            id = attrs['ID']
            name = attrs['NAME']
            the_class = attrs['CLASS']
            order = attrs['ORDER']
            level = attrs['LEVEL']
            line = attrs['LINE']

            self._current_group = KGroup.extend(name)
            self._current_group.id = id
            self._current_group._name = name
            self._current_group._pom_class_id = the_class
            self._current_group._order = int(order)
            self._current_group._level = int(level)
            self._current_group._line = int(line)
            self._context = KleioContext.GROUP

        elif ename == 'ELEMENT':
            if self._context != KleioContext.GROUP:
                raise SAXParseException(
                    "ELEMENT out of context, should be inside GROUP element")
            # <ELEMENT NAME="id" CLASS="id"><core>r1775-f1-per1</core></ELEMENT>

            elname = attrs['NAME']
            self._current_group.allow_as_element(elname)
            self._current_element = KElement(elname,None)
            self._current_element._element_class = attrs['CLASS']
            self._context = KleioContext.ELEMENT

        elif ename == 'CORE':
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "CORE out of context, should be inside ELEMENT element")
            self._context = KleioContext.CORE
            self._current_entry = ""

        elif ename == 'COMMENT':
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "COMMENT out of context, should be inside ELEMENT element")
            self._context = KleioContext.COMMENT
            self._current_entry = ""

        elif ename == 'ORIGINAL':
            if self._context != KleioContext.ELEMENT:
                raise SAXParseException(
                    "ORIGINAL out of context, should be inside ELEMENT element")
            self._context = KleioContext.ORIGINAL
            self._current_entry = ""

        elif ename == 'RELATION':
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    "GROUP out of context, should be inside KLEIO element")
            self._kleio_handler.newRelation(attrs)
        else:
            raise SAXParseException(
                f"Unexpected element in Kleio file: {ename}")

    def endElement(self, name):
        ename = name.upper()

        if ename == 'GROUP':
            self._kleio_handler.newGroup(self._current_group)
            self._context = KleioContext.KLEIO
            self._current_group = None

        elif ename == 'CLASS':
            self._kleio_handler.newClass(self._current_class,
                                         self._current_class_attrs)
            self._context = KleioContext.KLEIO

        elif ename == 'ATTRIBUTE':
            self._context = KleioContext.CLASS

        elif ename == 'ELEMENT':
            setattr(self._current_group,
                    self._current_element.name,
                    self._current_element)

            self._context = KleioContext.GROUP

        elif ename in ['CORE', 'COMMENT', 'ORIGINAL']:
            if ename == 'CORE':
                if self._current_element.core is None:
                    self._current_element.core = self._current_entry
            if ename == 'COMMENT':
                if self._current_element.comment is None:
                    self._current_element.comment = self._current_entry
            if ename == 'ORIGINAL':
                if self._current_element.original is None:
                    self._current_element.original = self._current_entry
            self._context = KleioContext.ELEMENT

    def characters(self, content):
        self._current_entry = self._current_entry + content

    def ignorableWhitespace(self, content):
        pass

    def processingInstruction(self, target, data):
        pass


class KleioHandler():

    def __init__(self, conn_string: str):
        self.db_system: DBSystem = DBSystem(conn_string)

    def newKleioFile(self, attrs):
        self.session = Session(bind=self.db_system.engine())
        self.session.commit()

    def newClass(self, psm: PomSomMapper, attrs: List[PomClassAttributes]):
        if psm.id in pom_som_base_mappings.keys():
            # we do not allow redefining of base mappings
            return

        session = self.session

        class_attr: PomClassAttributes
        # check if we have this class defined in the database.
        existing_psm: PomSomMapper = session.get(PomSomMapper,psm.id)
        if existing_psm is not None:     # class exists we delete it and insert again
            existing_attrs: List[PomClassAttributes] = \
                session.execute(
                    select(PomClassAttributes).filter_by(the_class=psm.id))
            for class_attr in existing_attrs:
                session.delete(class_attr)
            session.delete(existing_psm)

        # now we add the new mapping
        session.add(psm)
        for class_attr in attrs:
            session.add(class_attr)

        session.flush()
        session.commit()
        # ensure that the table and ORM classes are created
        psm.ensure_mapping(session)
        session.commit()


    def newGroup(self, group: KGroup):
        # get the PomSomMapper
        # pass storeKGroup
        pom_mapper_for_group = PomSomMapper.get_pom_class(group._pom_class_id,
                                                          self.session)



        pom_mapper_for_group.store_KGroup(group,self.session)

    def newRelation(self, attrs):
        pass

    def endKleioFile(self):
        pass


def import_from_xml(filespec: str, conn_string: str, options: dict = None):
    """
    Import data from file or url into a timelink-mhk database

    :param filespec: file path or URL of data file.
    :param conn_string: SQLAlchemy connection string to database.
    :param options: a dictionnary with options, currently:
            'kleio_url': the url of kleio server;
            'kleio_token': the authorization token for the kleio server.

    :return:
    """
    sax_handler = SaxHandler(KleioHandler(conn_string))
    parser = make_parser()
    parser.setContentHandler(sax_handler)
    parser.parse(filespec)

if __name__ == '__main__':
    parser = make_parser()
    parser.setContentHandler(SaxHandler())
    parser.parse(sys.argv[1])
