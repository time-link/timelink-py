import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List
import copy

from sqlalchemy import delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from timelink.api.models.pom_som_mapper import PomSomMapper as PomSomMapperTL
from timelink.api.models.pom_som_mapper import (
    PomClassAttributes as PomClassAttributesTL,
)
from timelink.api.models.base_mappings import (
    pom_som_base_mappings as pom_som_base_mappingsTL,
)
from timelink.api.models.base import Entity as EntityTL, Person as PersonTL
from timelink.api.models.base import REntity, REntityStatus as STATUS
from timelink.api.models.system import KleioImportedFile as KleioFileTL


from timelink.mhk.models.db import pom_som_base_mappings as pom_som_base_mappingsMHK
from timelink.mhk.models.pom_som_mapper import (
    PomSomMapper as PomSomMapperMHK,
    PomClassAttributes as PomClassAttributesMHK,
)
from timelink.mhk.models.entity import Entity as EntityMHK
from timelink.mhk.models.person import Person as PersonMHK
from timelink.mhk.models.system import KleioImportedFile as KleioFileMHK

from timelink.kleio.groups import KGroup


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


class KleioHandler:
    """ This class handles the import of data from a Kleio XML file into a Timelink database.

    It implements an interface to the SAX parser that reads the XML file and
    generates Kleio events. The KleioHandler class processes these events and
    stores the data in the Timelink database.

    The events are:
        newKleioFile:  start of a new Kleio file
        newClass:  definition of a new class (mapping between SOM and POM)
        newGroup:  a new kleio Group
        newRelation:  a new meta relation between kleio groups such as same_as
        """
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

    def __init__(self, session: Session, mode="TL", user="user"):
        """
        Arguments:
            session: a SQLAlchemy session
            mode: the mode of the import, either 'TL'(Timelink) or 'MHK'
            user: the user that is importing the data, used for same as ownership

        """
        self.session = session
        self.user = user
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
        # TODO: should use a subclass for this

        self.session.commit()
        self.postponed_relations = []
        self.errors = []
        self.warnings = []
        self.kleio_file = attrs["SOURCE"]
        # extract prefix /kleio-home/ from self.kleio_file
        if self.kleio_file.startswith("/kleio-home"):
            self.kleio_file = self.kleio_file.replace("/kleio-home", "")
        # extract name of file from path
        self.kleio_file_name = self.kleio_file.split("/")[-1]
        self.kleio_structure = attrs["STRUCTURE"]
        self.kleio_translator = attrs["TRANSLATOR"]
        self.kleio_when = attrs["WHEN"]
        self.kleio_file_is_aregister = False
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
            # TODO needs rethinking see #53
            logging.debug("Skipping base mapping %s", psm.id)
            orm_class = self.entity_model.get_orm_for_pom_class(psm.id)
            if orm_class is not None:
                self.pom_som_mapper.group_orm_models[psm.group_name] = orm_class
            return

        # if we import mapping from local file we also skip those
        # the importer should check at the beggining if local mappings
        # are available before starting the file import
        # we need a function check_local_mappings() that returns a list
        # of mappings available in the local file system.
        # if psm.id in check_local_mappings(): return

        session = self.session

        # check if we have this class defined in the database.
        existing_psm: PomSomMapperTL | PomSomMapperMHK | None = session.get(
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
            self.pom_som_cache[group.pom_class_id] = pom_mapper_for_group  # TODO redundant?
        except Exception as exc:
            self.errors.append(
                f"ERROR: {self.kleio_file_name} {str(group.line)}"
                f" finding PomSomMapper for class "
                f"{group.pom_class_id}: {exc.__class__.__name__}: {exc}"
            )
            return

        # check if pom_mapper_for_group is attached to the session
        if not self.session.object_session(pom_mapper_for_group):
            self.session.add(pom_mapper_for_group)

        if group.pom_class_id == "act":  # TODO should be .extends("act")
            logging.debug(f"{group._name}${group.id}")

        if pom_mapper_for_group.id == "aregister":  # TODO should be .extends("aregister")
            self.kleio_file_is_aregister = True  # current file is an authority register

        if pom_mapper_for_group.id == "relation":  # TODO should be .extends("relation")
            # it can happen that the destination of a relation
            #  is not yet in the database (forward reference in relation)
            #  In this case we postpone the storing of the relation
            # until the end of file
            exits_dest_rel = self.session.get(
                self.entity_model, group.get_element_by_name_or_class("destination").core
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
            # we have the POM class, less check special cases
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
        """ Process a new (Meta) relation

        Currently there are two types of metadata relations,
        both related to processing same as relations:

        1. same_as:  register the same_as and xsame_as elements
                     in groups
        ```xml
        <RELATION ID="__-sa-deh-joao-barradas-rela6"
            ORG="sa-deh-joao-barradas-per1-11"
            DEST="sa-deh-matteo-ricci"
            TYPE="META"
            VALUE="same_as"/>
        ```

        2. attach_to_rentity:  used in authority registers to register
                                existing real entities to the register
        ```xml
              <RELATION ID="rp-31-occ1"
                    REGISTER="real-entities-toliveira"
                    USER="toliveira"
                    ORG="deh-paul-lieou"
                    DEST="rp-31"
                    TYPE="META"
                    VALUE="attach_to_rentity" />
        ```
        """
        rel_id = attrs["ID"]
        rel_origin = attrs["ORG"]
        rel_dest = attrs["DEST"]
        rel_value = attrs["VALUE"]
        rel_register = attrs.get("REGISTER", None)
        rel_user = attrs.get("USER", None)

        if rel_value == "same_as":
            self.session.commit()

            # register the same_as relation

            try:
                REntity.same_as(rel_origin,
                                rel_dest,
                                status=STATUS.SOURCE, rule=f"same_as('{self.kleio_file_name}')",
                                session=self.session)
                self.session.commit()
            except Exception as exc:
                self.errors.append(
                    f"ERROR: {self.kleio_file_name} "
                    f"processing same_as relation {rel_id}: {exc.__class__.__name__}: {exc}"
                )
                self.session.rollback()
                return

        elif rel_value == "attach_to_rentity":
            # register the attach_to_rentity relation
            self.session.commit()
            rentity = self.session.get(REntity, rel_dest)
            if rentity is None:
                self.errors.append(
                    f"ERROR: {self.kleio_file_name} "
                    f"processing attach_to_rentity relation {rel_id}: "
                    f"Real entity {rel_dest} not found"
                )
                self.session.rollback()
                return
            try:
                rentity.attach_occurrence(
                    occ_id=rel_origin,
                    user=rel_user,
                    status=rentity.status,
                    rule=f"attach_to_rentity('{rel_register}')"
                )
                self.session.commit()
            except Exception as exc:
                self.errors.append(
                    f"ERROR: {self.kleio_file_name} "
                    f"processing attach_to_rentity relation {rel_id}: {exc.__class__.__name__}: {exc}"
                )
                self.session.rollback()
                return

        else:  # unknown relation
            self.errors.append(
                f"ERROR: {self.kleio_file_name} "
                f"unknown relation type {rel_value}"
            )
            self.session.rollback()

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
