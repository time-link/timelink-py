import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List
import copy

from sqlalchemy import text, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from timelink.api.models.pom_som_mapper import PomSomMapper as PomSomMapperTL
from timelink.api.models.pom_som_mapper import (
    PomClassAttributes as PomClassAttributesTL,
)
from timelink.api.models.base_mappings import (
    pom_som_base_mappings as pom_som_base_mappingsTL,
)
from timelink.api.models.base import (
    Entity as EntityTL,
    Person as PersonTL,
    Relation as RelationTL
)
from timelink.api.models.rentity import (
    REntity as REntityTL,
    Link as LinkTL,
    BLink as BLinkTL
)

from timelink.api.models.base import REntity, LinkStatus as STATUS
from timelink.api.models.system import KleioImportedFile as KleioFileTL


from timelink.mhk.models.db import pom_som_base_mappings as pom_som_base_mappingsMHK
from timelink.mhk.models.pom_som_mapper import (
    PomSomMapper as PomSomMapperMHK,
    PomClassAttributes as PomClassAttributesMHK,
)
from timelink.mhk.models.entity import Entity as EntityMHK
from timelink.mhk.models.person import Person as PersonMHK
from timelink.mhk.models.relation import Relation as RelationMHK
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
    """This class handles the import of data from a Kleio XML file into a Timelink database.

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
    sources_in_file = []
    xrelations = {}
    xlinks = {}
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
            self.relation_model = RelationTL
            self.rentity_model = REntityTL
            self.link_model = LinkTL
            self.kleio_file_model = KleioFileTL
            self.model_type = "TL"
        elif mode == "MHK":
            self.pom_som_base_mappings = pom_som_base_mappingsMHK
            self.pom_som_mapper = PomSomMapperMHK
            self.pom_class_attributes = PomClassAttributesMHK
            self.entity_model = EntityMHK
            self.person_model = PersonMHK
            self.relation_model = RelationMHK
            self.kleio_file_model = KleioFileMHK
            self.model_type = "MHK"
        else:
            raise ValueError(f"Unknown mode {mode}")

    def save_source_context(self, source_id):
        """Save all the links and relations pointing to this
        source from other sources because they will be nulled or deleted
        when the source is deleted.

        After import we will restore them.

        This will add to the self.cross_source_references dict

        We use the follow queries to get the external relations to this source:

        ```sql
        SELECT r.id, r.origin, r.destination, r.the_type, r.the_value
                FROM relations r, entities e
                WHERE r.id = e.id
                            AND e.the_source != :source_id
                            AND r.destination IN
                                (SELECT id
                                 FROM entities e2
                                 WHERE e2.id = r.destination
                                       e2.the_source = :source_id
                                        AND e2.the_source != e.the_source)

        ```
        And to get the external links to this source:

        ```sql
        SELECT l.rid,l.entity,l.source as link_source, e.the_source as entity_source
                FROM links l, entities e
                WHERE l.entity = e.id
                AND e.the_source = :source_id
                AND link_source != e.the_source;
        """
        # Currently not implemented in MHK Mysql databases
        if self.model_type == "MHK":
            return
        # make a sql alchemy query to get the cross source relations
        # and store them in cross_source_relations
        sql = """select r.id,
                    r.origin,
                    r.destination,
                    r.the_type,
                    r.the_value,
                    r.the_date,
                    e.the_source,
                    e2.the_source as dest_source
                        FROM relations r, entities e, entities e2
                        WHERE r.id = e.id
                            AND r.destination = e2.id
                            AND e2.the_source = :source_id
                            AND e.the_source != e2.the_source
                """
        # https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html#orm-queryguide-selecting-text
        sql_query = (
            text(sql)
            .bindparams(source_id=source_id)
            .columns(
                self.relation_model.id,
                self.relation_model.origin,
                self.relation_model.destination,
                self.relation_model.the_type,
                self.relation_model.the_value,
                self.relation_model.the_date,
                self.entity_model.the_source,
                self.entity_model.the_source.label("dest_source"),
            )
        )
        xrefs = self.session.execute(sql_query).fetchall()

        self.xrelations[source_id] = xrefs

        # get the links that are going to be affected by the reimport
        sql = """
                SELECT l.id, l.rid,l.entity, l.user, l.rule, l.status, l.source as link_source, e.the_source as entity_source
                FROM links l, entities e
                WHERE l.entity = e.id
                AND e.the_source = :source_id;

        """
        sql_query = (
            text(sql)
            .bindparams(source_id=source_id)
            .columns(
                self.link_model.id,
                self.link_model.rid,
                self.link_model.entity,
                self.link_model.user,
                self.link_model.rule,
                self.link_model.status,
                self.link_model.source,
                self.entity_model.the_source.label('entity_source')
            )
        )
        xlinks = self.session.execute(sql_query).fetchall()

        # save the links that are going to be affected by the reimport
        for link_id in [link.id for link in xlinks]:
            link = self.session.get(self.link_model, link_id)

            # find a blink for the same rid, entity and user
            # if it exists we do not create a new one

            blink = self.session.query(BLinkTL).filter(
                BLinkTL.rid == link.rid,
                BLinkTL.entity == link.entity,
                BLinkTL.user == link.user
            ).first()

            if blink is None:
                # create a blink with the link information
                blink = BLinkTL(
                    rid=link.rid,
                    entity=link.entity,
                    user=link.user,
                    rule=link.rule,
                    status=link.status,
                    source=link.source,
                )
            self.session.add(blink)
            self.session.commit()

        # maybe not useful
        self.xlinks[source_id] = xlinks

    def restore_source_context(self, source_id):
        """Restore all the links and relations pointing to this
        source from other sources that were saved before the source was deleted

        TODO: is this better here or in Source entity model?
        Reasons for here: at the import level restore only
        makes sense after all the source is imported because
        at the entity level a Source is inserted empty and only
        at the end of the source import it is possible to restore
        the missing links
        """
        if self.model_type == "MHK":
            return
        relations = self.xrelations[source_id]
        for r in relations:
            # we get the relation in other sources that was affect by the reimport
            rel = self.session.get(
                self.relation_model, r.id
            )  # safe because id is on the exernal source
            if rel is not None:
                # this relation should have the destination None
                # because the destination was deleted when the current source
                # was deleted before reimport
                # check that the old destination still exists after reimport
                if rel.destination is not None:
                    # if the relation has a destination it means that it was not affected
                    # by the reimport of the source, but it should
                    # show a warning
                    self.warnings.append(
                        f"WARNING: An external relation {r.id} "
                        f"of type {r.the_type} with value {r.the_value} "
                        f"referred entity {r.destination} in source {r.dest_source} "
                        f"was not affected by reimport of source {source_id}"
                    )
                dest = self.session.get(self.entity_model, r.destination)
                if dest is not None:
                    # if so we restore the relation destination
                    rel.destination = r.destination  # set to the saved value
                    self.session.merge(rel)
                    self.session.commit()

                    # TODO: and now we should process the xsame_as relations
                    if rel.the_type == 'identification' and rel.the_value == 'same as':

                        REntity.same_as(
                            rel.origin,
                            rel.destination,
                            status=STATUS.SOURCE,
                            rule=f"same_as('{self.kleio_file_name}', 'reimported')",
                            source=source_id,
                            session=self.session,
                        )
                        pass
                else:
                    # if the destination does not exist
                    # we flag the error
                    self.errors.append(
                        f"ERRROR: An external relation {r.id} "
                        f"of type {r.the_type} with value {r.the_value} "
                        f"referred entity {r.destination} which does not exist "
                        f"after reimport of source {source_id}"
                    )
                self.session.commit()
            else:
                # The saved relation in the other source was deleted
                # this should not have happened
                self.errors.append(
                    f"ERRROR: An external relation {r.id} "
                    f"of type {r.the_type} with value {r.the_value} "
                    f"with origin {r.origin} and destination {r.destination}"
                    f"was saved before reimport of source {source_id} "
                    f"but was deleted during reimport."
                )

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
        if self.kleio_file.startswith("/kleio-home/"):
            self.kleio_file = self.kleio_file.replace("/kleio-home/", "")
        # extract name of file from path
        self.kleio_file_name = self.kleio_file.split("/")[-1]
        self.kleio_structure = attrs["STRUCTURE"]
        self.kleio_translator = attrs["TRANSLATOR"]
        self.kleio_when = attrs["WHEN"]
        self.kleio_file_is_aregister = False
        self.kleio_source_id = None
        self.aregister_id = None
        self.pom_som_cache = dict()
        self.sources_in_file = []
        self.xrefs = {}
        self.xlinks = {}
        logging.debug("Kleio file: %s", self.kleio_file)
        logging.debug("Kleio structure: %s", self.kleio_structure)
        logging.debug("Kleio translator: %s", self.kleio_translator)
        logging.debug("Kleio when: %s", self.kleio_when)
        # mark that file is being imported by nulling the imported date
        kfile = self.session.get(self.kleio_file_model, self.kleio_file)
        if kfile is not None:
            kfile.imported = None
            kfile.imported_string = None
            self.session.commit()

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
            self.pom_som_cache[group.pom_class_id] = (
                pom_mapper_for_group  # TODO redundant?
            )
        except Exception as exc:
            self.errors.append(
                f"ERROR: {self.kleio_file_name} {str(group.line)}"
                f" finding PomSomMapper for class "
                f"{group.pom_class_id}: {exc.__class__.__name__}: {exc}"
            )
            return

        # store the current source id into the group
        group.source_id = self.kleio_source_id

        # check if pom_mapper_for_group is attached to the session
        if not self.session.object_session(pom_mapper_for_group):
            self.session.add(pom_mapper_for_group)

        if group.pom_class_id == "act":  # TODO should be .extends("act")
            logging.debug(f"{group._name}${group.id}")

        if (
            pom_mapper_for_group.id == "aregister"
        ):  # TODO should be .extends("aregister")
            self.kleio_file_is_aregister = True  # current file is an authority register
            self.aregister_id = str(group.id.core)

        if pom_mapper_for_group.id == "source":  # TODO should be .extends("source")
            self.kleio_source_id = str(group.id.core)
            group.source_id = self.kleio_source_id
            self.sources_in_file.append(self.kleio_source_id)
            # We need to save all the links and relations pointing to this
            # source from other sources because they will be nulled or deleted
            # when the source is deleted
            # after import we will restore them for the entities that are restored
            # in this import
            self.save_source_context(self.kleio_source_id)

        if pom_mapper_for_group.id == "relation":  # TODO should be .extends("relation")
            # it can happen that the destination of a relation
            #  is not yet in the database (forward reference in relation)
            #  In this case we postpone the storing of the relation
            # until the end of file
            exits_dest_rel = self.session.get(
                self.entity_model,
                group.get_element_by_name_or_class("destination").core,
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
        """Process a new (Meta) relation

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
                REntity.same_as(
                    rel_origin,
                    rel_dest,
                    status=STATUS.SOURCE,
                    rule=f"same_as('{self.kleio_file_name}')",
                    source=self.kleio_source_id,
                    session=self.session,
                )
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
                error_msg = (
                    f"ERROR: {self.kleio_file_name} "
                    f"processing attach_to_rentity relation {rel_id}: "
                    f"Real entity {rel_dest} not found"
                )
                logging.error(error_msg)
                self.errors.append(error_msg)
                self.session.rollback()
                return
            try:
                rentity.attach_occurrence(
                    occ_id=rel_origin,
                    user=rel_user,
                    status=rentity.status,
                    rule=f"attach_to_rentity('{rel_register}')",
                    aregister=self.aregister_id,
                )
                self.session.commit()
            except Exception as exc:
                msg = (
                    f"ERROR: {self.kleio_file_name} "
                    f"processing attach_to_rentity relation {rel_id}: {exc.__class__.__name__}: {exc}"
                )
                logging.error(msg)
                self.errors.append(msg)
                self.session.rollback()
                return

        else:  # unknown relation
            self.errors.append(
                f"ERROR: {self.kleio_file_name} " f"unknown relation type {rel_value}"
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
                    f"ERROR: {self.kleio_file_name}: {str(group.line)} "
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

        # restore all the links and relations pointing to this
        # source(s) from other sources that were saved before the source was deleted
        # the cross references were save when a source group was processed
        # TODO: should this go here or to models.Source?
        for source_id in self.sources_in_file:
            self.restore_source_context(source_id)

        # store information on kleio file import
        kfile = self.kleio_file_model(
            path=self.kleio_file,
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
