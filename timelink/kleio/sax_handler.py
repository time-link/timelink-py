from typing import Optional, List
from xml.sax import handler, SAXParseException

from timelink.api.models import PomSomMapper as PomSomMapperTL, PomClassAttributes as PomClassAttributesTL
from timelink.kleio.groups import KGroup, KElement
from timelink.kleio.kleio_handler import KleioContext
from timelink.mhk.models import PomSomMapper as PomSomMapperMHK, PomClassAttributes as PomClassAttributesMHK


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

        elif ename == "RELATION":
            # <RELATION ID="sa-deh-joao-barradas-rela6"
            #   ORG="sa-deh-joao-barradas-per1-11"
            #   DEST="sa-deh-matteo-ricci"
            #   TYPE="META" VALUE="same_as"/>
            if self._context != KleioContext.KLEIO:
                raise SAXParseException(
                    "RELATION out of context, should be inside KLEIO element",
                    None,
                    loc,
                )
            self._kleio_handler.newRelation(attrs)

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
            gid = attrs["ID"]
            name = attrs["NAME"]
            the_class = attrs["CLASS"]
            order = attrs["ORDER"]
            level = attrs["LEVEL"]
            line = attrs["LINE"]

            # Mal [? porquê?]
            self._current_group = KGroup()
            self._current_group.id = gid
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
