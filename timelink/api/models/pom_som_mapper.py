"""Mapping between Kleio Groups and relational database tables"""

import logging

# import pdb
import warnings
import json
from typing import Optional, Type, List

from sqlalchemy import Table, delete  # pylint: disable=import-error
from sqlalchemy import Column  # pylint: disable=import-error
from sqlalchemy import ForeignKey  # pylint: disable=import-error
from sqlalchemy import String  # pylint: disable=import-error
from sqlalchemy import Integer  # pylint: disable=import-error
from sqlalchemy import Float  # pylint: disable=import-error

from sqlalchemy import inspect  # pylint: disable=import-error
from sqlalchemy.engine import Engine  # pylint: disable=import-error
from sqlalchemy.orm import Mapped  # pylint: disable=import-error
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import exc as sa_exc
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...kleio.groups import KGroup, KElement
from .base_class import Base
from .entity import Entity

logger = logging.getLogger(__name__)


class PomSomMapper(Entity):
    """

    Represents a mapping between a Kleio Group in the
    Source Oriented Model (Som) and a relational database entity
    in the Person Oriented Model (Pom). This class corresponds
    to the table "classes" in a Timelink-MHK database,
    and the associated "class_attributes" table. Together the
    two tables describe a Som-Pom mapping, that define how
    Kleio groups are stored in the relational database.

    This class can generate tables and ORM objects that can
    store a Kleio Group in the database.

    Fields

    :id: name of this PomSomMapper, singular form
    :table_name: name of the table in Pom, plural form
    :group_name: name of Som group that maps to this table
    :super_class: name of PomSom class extended by this one
    :orm_class: ORM class that maps to this table
    :pom_classes: dictionary of all PomSomMappers (id, PomSomMapper)
    :group_orm_models: dictionary of ORM classes for each group name

    For the core kleio groups (source,act,person,object, relation,attribute)
    the mapping information is predefined at database creation time and
    the 'classes' and 'class_attributes' populated accordingly.

    The Kleio translator can provide new mappings for new groups that are
    created for specific sources. The mapping information between new groups
    and the database is embedded in the translator output of new sources in the
    form of data for the tables mapped to the PomSomMapper.

    For a mapping between a Som Group and a Pom table
    to be fully operational it is necessary that:


    1. The tables "classes" and "class_attributes" contain the mapping
       information, normally populated during the initialization process of
       the database (timelink.api.models.basemappings.py) and updated during import,
       as new sources define new mappings dynamically.

    2. A table for storing the elements of the Som Group.
       This is either a basic core table
       (persons,objects,acts,sources,...) or a table that extends
       a basic core table with extra columns.

    3. An ORM sqlalchemy model that represents the Pom model and joins
       the information of the inheritance hierarchy, by mapping to the necessary
       tables.


    The name of the table for a given group and the correspondence between
    group elements and table columns is handled by the PomSomMapper. If the
    group adds extra information then a new table
    is created  that "extends" an existing core table,
    by what is called a "joined inheritance hierarchy"
    (see https://docs.sqlalchemy.org/en/14/orm/inheritance.html)

    To ensure that all the three dimensions exist in a given context it
    is necessary that:

    1. When creating a new database, the core Pom tables should be created
    using sqlalchemy `metadata.create_all(bind=engine)`. Then the
    tables "classes" and "class_attributes" must be populated with the mapping
    of the core Som and Pom groups and entities.

    See timelink.api.models.base_mappings.py for the core data for
    bootstrapping of the mapping information.

    Both steps are ensured by TimelinkDatabase.__init__ method.

    2. When importing new sources, if a new mapping was generated at the
       translation step, it is necessary first to populate "classes" and
       "class_attributes" with the mapping information, included in the translation
       source, then generate the table for the group information (if it
       does not exist) and the ORM mapping. This step is done by the method
       PomSomMapper.ensure_mapping(session) which must be called during the
       import process.

    3. When connecting to a database created by a legacy version of MHK, it is
       necessary to ensure that all the ORM mappings are created, by examining the
       information in the "classes" table and checking if the ORM mapping and
       table representations exist. This is done by the PomClass.ensure_all_mappings()
       method.

    """

    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    group_name: Mapped[Optional[str]] = mapped_column("group_name", String(32))
    super_class: Mapped[Optional[str]] = mapped_column("super", String)

    __mapper_args__ = {
        "polymorphic_identity": "class",
        "inherit_condition": id == Entity.id,
    }
    # stores the ORM mapper for this mapping (source, act,person...)
    orm_class: Entity

    # flags this class as dynamic, created by import of a class structure
    __is_dynamic__: bool = False

    # Class attributes
    # Class attribute stores current PomSomMappings keyed by id
    pom_classes: dict = {}

    # Stores the association between group names and PomSomMapper.
    #  See get_orm_for_groupname and issue #53
    group_orm_models: dict = {}

    # Caches group to PomSomMapper mapping
    # Note that this needs updating everytime a group is imported
    # or a new mapping is created.
    group_pom_classes: dict = {}

    def is_dynamic_pom(self):
        """Return True if this class was created by a dynamic mapping

        Dynamic mappings are mappings that are created during the import
        of a Kleio group.
        """
        return getattr(self, "__dynamicpom__", False)  # this is set in PomSomClass.ensure_mapping

    def set_as_dynamic_pom(self):
        """Set this class as dynamic
        Dynamic mappings are mappings that are created during the import
        of a Kleio group.
        """
        self.__dynamicpom__ = True

    @classmethod
    def reset_cache(cls):
        """Reset cache of mappers.

        Call this when reattaching to a new database
        to avoid carry over between databases"""
        cls.pom_classes = dict()
        cls.group_orm_models = dict()
        cls.group_pom_classes = dict()

    @classmethod
    def get_pom_class(cls, pom_class_id: String, session):
        """
        Return the pom_class object for a given pom_class_id.

        See also Entity.get_orm_for_pom_class

        :param pom_class_id:
        the id of a pom_class
        """
        if pom_class_id in cls.pom_classes.keys():
            cached_pom_class = cls.pom_classes[pom_class_id]
            session.add(cached_pom_class)
            return cached_pom_class
        return session.get(cls, pom_class_id)

    @classmethod
    def import_pom_som_class(cls, pom_class: "PomSomMapper",
                             pom_class_attrs: List["PomClassAttributes"],
                             session=None):
        """
        Process a PomSomMapper class that was imported from a Kleio transcript

        This method is called after the PomSomMapper class is created
        from the Kleio transcript and before it is stored in the database.

        It is used to ensure that the ORM class and the table associated with it
        are created in the database.
        It does not change base_mappings.

        :param pom_class: a PomSomMapper object
        :param pom_class_attrs: a list of PomClassAttributes objects
        :param base_mappings: a dictionary of base mappings
        :param session: a database session

        :return: None
        """
        pom_class_id = pom_class.id
        group_name = pom_class.group_name

        # check if the pom_class is already in the database
        existing_psm = cls.get_pom_class(pom_class_id, session)
        if existing_psm is not None:  # class exists: delete, insert again
            # if it is builtin class, we do not delete it
            if not existing_psm.is_dynamic():
                return existing_psm
            else:
                # class exists and is not base class, we replace it
                try:
                    logging.debug("Deleting existing class %s", pom_class.id)
                    session.commit()
                    stmt = delete(PomClassAttributes).where(PomClassAttributes.the_class == pom_class_id)
                    session.execute(stmt)
                    session.delete(existing_psm)
                    session.commit()
                except Exception as e:
                    logger.error(f"Could not delete PomSomMapper {pom_class_id}," f"error deleting class attributes", e)
                    raise e
                # insert the new class
                try:
                    logging.debug("Adding dynamic class %s", pom_class.id)
                    pom_class.set_as_dynamic_pom()
                    session.add(pom_class)
                    for class_attr in pom_class_attrs:
                        session.add(class_attr)
                    session.commit()

                except IntegrityError as e:
                    session.rollback()
                    logger.error(f"Could not import PomSomMapper {pom_class_id}", e)
                    raise e
        else:  # this pom_class does not exist in the database
            try:
                logging.debug("Adding new class %s", pom_class.id)
                pom_class.set_as_dynamic_pom()
                session.add(pom_class)
                for class_attr in pom_class_attrs:
                    session.add(class_attr)
                session.commit()
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Could not import PomSomMapper {pom_class_id}", e)
                raise e

        # ensure that the ORM and table are created
        pom_class.ensure_mapping(session=session)
        # at this point the pom_class will have an orm_class
        orm_class = pom_class.orm_class
        # store the ORM class and the PomSom Mapper for this group
        cls.group_orm_models[group_name] = orm_class
        cls.group_pom_classes[group_name] = pom_class
        return pom_class

    def ensure_mapping(self, session=None):
        """
        Ensure that a table and ORM model exist to support
        this PomSom mappings

        Checks if there is a table definition
        to support this mapping. If not a new table
        definition is created with information from the
        class attributes.

        A new ORM class is also created for mapping the new
        table. The new ORM class will extend the superclass
        ORM mapping.


        """

        if not hasattr(self, "orm_class"):
            self.orm_class = None

        # store the existing tables known to sqlalchemy metadata
        metadata_obj = type(self).metadata
        orm_tables = metadata_obj.tables  # these are the tables known to ORM

        # we need to check the existence of the ORM class
        # and the associated table in the database.
        # The reason is that in some cases the ORM can exist
        # without the table, i.e., when in the same application
        # connection to a database with dynamic mappings is made
        # and later on a new database is created, without the
        # dynamic mappings. In this case the ORM class will exist
        # but the table will not.

        # if we have both orm and table we return the orm
        if self.orm_class is not None and self.orm_class.__mapper__.local_table.name in orm_tables.keys():
            return self.orm_class

        # if not check if Entity knows about an orm class
        my_orm = Entity.get_orm_for_pom_class(self.id)
        if my_orm is not None and my_orm.__mapper__.local_table.name in orm_tables.keys():
            # ORM model for this pom_som_mapper already exists
            # and also the table, so we return.
            # if this PomSomMapper is dynamic so is the ORM
            if self.is_dynamic_pom():
                my_orm.set_as_dynamic()  # mark as dynamic ORM
            self.orm_class = my_orm
            if self.group_name is not None and self.group_name != "na":
                # Store as "static"
                PomSomMapper.group_orm_models[self.group_name] = my_orm

            return self.orm_class

        # we have no ORM mapping for the SomPomMapper
        # or we have the ORM mapping but the table is missing.
        # First check if we have this table already mapped to some Entity.
        # This might happen if we have different kleio groups mapped to the
        # same table, in order to make the kleio transcripts more readable
        # (it happens frequently with the tables 'acts', 'persons' and 'objects').
        # If so we will reuse the existing Table class.
        #
        # It can also happen that while not having a ORM mapping the table
        # can already exist in the database as result of previous imports.
        #
        # Note that non core PomSomMappings and corresponding ORM classes,
        # which are dynamically defined during import, have to be recreated
        # from the database information each time an application runs.
        #

        dbengine: Engine = session.get_bind()
        insp = inspect(dbengine)
        dbtables = insp.get_table_names()  # these are the ones in the database

        my_table: Table
        if self.table_name in orm_tables.keys():
            # table is known to ORM we used the Table class there
            # we will extend if necessary
            my_table = orm_tables[self.table_name]
        elif self.table_name in dbtables:
            # the table exists in the database, we introspect
            my_table = Table(self.table_name, metadata_obj, autoload_with=dbengine)
            # we need to ensure that the foreign key relation exists with super talbe
            # otherwise the ORM mapping further down will fail.
            if self.super_class not in ["root", "base"]:
                # print("Getting super class " + self.super_class)
                pom_super_class: PomSomMapper = PomSomMapper.get_pom_class(self.super_class, session)
                if pom_super_class is not None:
                    super_class_table_id = pom_super_class.table_name + ".id"
                else:
                    message = "Creating mapping for %s super class %s not found" " Default to entities as super class"
                    logger.warning(message, self.id, self.super_class)
                    super_class_table_id = "entities.id"
                pytype = my_table.c.id.type
                my_table.append_column(
                    Column(
                        "id",
                        pytype,
                        ForeignKey(super_class_table_id, ondelete="CASCADE", onupdate="CASCADE"),
                        primary_key=True,
                    ),
                    replace_existing=True,
                )
        else:
            # Table is unknown to ORM mapper or does not exist in the database
            # This is the dynamic part, we create a table with
            # the definition of "class" and "class_attributes"
            # fetched by this class
            # NOTE this does not take into account that the columns
            #       may already exist in the super class or up in the
            #       class hierarchy. Not sure if this the way it is supposed
            #       to be or if it is a problem to be dealt with here.
            #       SQLAchemy will rename the columns to avoid conflict
            #       automatically
            my_table = Table(
                self.table_name,
                metadata_obj,
                info={"dynamic": True, "pom_class_id  ": self.id},  # we flag as dynamic  # this goes to metadata
                extend_existing=True,
            )
            cattr: Type["PomClassAttributes"]
            for cattr in self.class_attributes:  # pylint: disable=no-member
                PyType: str  # pylint: disable=invalid-name
                pom_type = cattr.coltype.lower()
                if pom_type == "varchar":
                    PyType = String(cattr.colsize)  # pylint: disable=invalid-name
                elif pom_type == "numeric" and cattr.colprecision == 0:
                    PyType = Integer  # pylint: disable=invalid-name
                elif pom_type == "numeric" and cattr.colprecision > 0:
                    PyType = Float
                else:
                    PyType = String
                # print(f"Inferred python type for {cattr.colname}: ", PyType)

                if cattr.pkey != 0:
                    if self.super_class not in ["root", "base"]:
                        # print("Getting super class " + self.super_class)
                        pom_super_class: PomSomMapper = PomSomMapper.get_pom_class(self.super_class, session)
                        if pom_super_class is not None:
                            super_class_table_id = pom_super_class.table_name + ".id"
                        else:
                            message = (
                                "Creating mapping for %s super class %s not found" " Default to entities as super class"
                            )
                            logger.warning(message, self.id, self.super_class)
                            super_class_table_id = "entities.id"
                        my_table.append_column(
                            Column(
                                cattr.colname,
                                PyType,
                                ForeignKey(super_class_table_id),
                                primary_key=True,
                            ),
                            replace_existing=True,
                        )
                    else:  # we are at the root of the entity hierarchy
                        my_table.append_column(
                            Column(cattr.colname, PyType, primary_key=True),
                            replace_existing=True,
                        )
                else:
                    # Here should check if column name already exists in super
                    # class. But in fact it can exist in any of the superclasses
                    # we need a function self.get_columns_of_super()
                    # and check if cattr.colname is there if it is we can
                    # append self.name + "_" + cattr.colname.
                    # but the PomClassAtributes would need to be updated to
                    # reflect the new colname.
                    my_table.append_column(
                        Column(cattr.colname, PyType, primary_key=False),
                        replace_existing=True,
                    )
            my_table.create(session.get_bind())
            session.commit()
            # End of creation of a dynamic mapping and table

        # we know create a new ORM mapping for this PomSomMapper
        # note that if a class with the same name already exists
        # it will be replaced by the new one.
        # This is the dynamic part of the ORM mapping
        super_orm = Entity.get_orm_for_pom_class(self.super_class)
        if super_orm is None:
            super_orm = pom_super_class.ensure_mapping(session)
        props = {
            "__table__": my_table,
            "__mapper_args__": {"polymorphic_identity": self.id},
        }
        # and now we create the ORM class
        try:
            with warnings.catch_warnings():
                # We ignore warning related to duplicate fields in
                # specialized classes (obs normally, but also the_type...)
                warnings.simplefilter("ignore", category=sa_exc.SAWarning)
                my_orm = type(self.id.capitalize(), (super_orm,), props)
                my_orm.set_as_dynamic()  # mark as dynamic ORM
        except Exception as e:  # pylint: disable=broad-except
            logger.ERROR(Exception(f"Could not create ORM mapping for {self.id}"), e)

        self.orm_class = my_orm
        PomSomMapper.group_orm_models[self.group_name] = my_orm

        # set this pom_class as dynamic
        # we mark this pom_class as dynamic
        self.set_as_dynamic_pom()

        return self.orm_class

    @classmethod
    def get_pom_classes(cls, session) -> Optional[List["PomSomMapper"]]:
        """
        Get the pom_classes from database data.

        Note that this method does not ensure that a ORM mapper is created
        for each class. Use pom_class.ensure_mapping() method to dynamically
        produce the ORM class

        :return: A list of PomSomMappers object for each class in the db
        """

        stmt = select(cls)
        pom_classes = session.execute(stmt).scalars().all()
        pom_class: PomSomMapper
        for pom_class in pom_classes:
            cls.pom_classes[pom_class.id] = pom_class

        return cls.pom_classes.values()

    @classmethod
    def get_pom_class_ids(cls, session):
        """
        Return all the pom_som_class ids as a list
        :return:
        """

        # stmt = select(cls.id)
        # pom_class_ids: Optional[List[str]] = session.execute(
        #     stmt).scalars().all()
        # we do not cache any longer because of the
        # changing data base problem. If this class
        # is used with diferent database it might
        # have different mappings, so we need to fetch
        # from the database.

        cls.get_pom_classes(session)
        return list(cls.pom_classes.keys())

    @classmethod
    def get_pom_class_from_group(cls, group: KGroup, session=None):
        """Returns the PomSomMapper for a given group"""
        # TODO use property instead
        pom_id = getattr(group, "_pom_class_id", None)
        if pom_id is None:
            kname = group.kname
            pom_id = cls.get_pom_id_by_group_name(session, kname)
        if pom_id:
            return cls.get_pom_class(pom_id, session)
        return None

    @classmethod
    def get_pom_id_by_group_name(cls, session, kname):
        """Returns the PomSomMapper id for a given group name"""
        if kname in cls.group_pom_classes.keys():
            return cls.group_pom_classes[kname].id
        for pom in cls.get_pom_classes(session):
            if kname == pom.group_name:
                # TODO use a getter
                return pom.id
        return None

    @classmethod
    def get_orm_for_group(cls, groupname: str):
        """
        PomSomMapper.get_orm_for_groupname("act")

        will return the ORM class corresponding to the groupname "act"
        """
        return PomSomMapper.group_orm_models.get(groupname, None)

    @classmethod
    def ensure_all_mappings(cls, session):
        """
        Ensures that every class currently defined in the database has
        a python table object and a python ORM object

        :return: None
        """

        pom_classes = cls.get_pom_classes(session=session)
        for pom_class in pom_classes:
            pom_class.ensure_mapping(session=session)

    def element_class_to_column(self, eclass: str, session: None) -> str:
        """Return the column name corresponding to a group element class.

        Args:
            eclass (str): The class of an element (included in the export file).

        Returns:
            str: The name of the column corresponding to this element in the mapped table.
        """

        cattr: PomClassAttributes = None
        for cattr in self.class_attributes:  # pylint: disable=no-member
            if cattr.colclass == eclass:
                return cattr.colname
        if self.id != "entity":
            super_class = self.get_pom_class(self.super_class, session=session)
            if super_class is not None:
                return super_class.element_class_to_column(eclass, session=session)
        return None

    def element_name_to_column(self, ename: str, session: None) -> str:
        """Return the column name corresponding to a group element name.

        Args:
            ename (str): The name of an element (included in the export file).

        Returns:
            str: The name of the column corresponding to this element in the mapped table.
        """
        cattr: PomClassAttributes = None
        for cattr in self.class_attributes:  # pylint: disable=no-member
            if cattr.colclass == ename:
                return cattr.colname
        if self.id != "entity":
            super_class = self.get_pom_class(self.super_class, session=session)
            if super_class is not None:
                return super_class.element_name_to_column(ename, session=session)
        return None

    def column_to_class_attribute(self, colname: str, session: None) -> "PomClassAttributes":
        """Return the class attribute corresponding to a column name.

        Args:
            colname (str): The name of a column in the mapped table.

        """
        for cattr in self.class_attributes:  # pylint: disable=no-member
            if cattr.colname == colname:
                return cattr
        if self.id != "entity":
            super_class = self.get_pom_class(self.super_class, session)
            if super_class is not None:
                return super_class.column_to_class_attribute(colname, session)
        return None

    @classmethod
    def kgroup_to_entity(cls, group: KGroup, session=None, with_pom=None) -> Entity:
        """
        Store a Kleio Group in the database.

        This is the main method that imports Kleio transcripts into the database.

        :param group: a Kleio Group
        :param with_pom: id of a PomSom class to handle storing this group
        :return: An ORM object that can store this group in the database

        To produce the ORM-POM representation of a group we need to find
        the PomSomMapper specific to that group, using the following:

            * if with_pom is given with a PomSomMapper id we fetch that
            * if the group was imported before it should have _pom_class_id
            * if neither then we search for a PomSom mapper with "groupname"
               equal to the name of the group.
        """
        if with_pom is not None:
            pom_class_id = with_pom
            pom_class = cls.get_pom_class(pom_class_id, session)
        else:
            pom_class = cls.get_pom_class_from_group(group, session)

        if pom_class is None:
            raise ValueError(f"Could not determine PomSomMapper for this group: {group}")

        # Not sure if this is necessary ensure mapping should have been done before
        pom_class.ensure_mapping(session)
        ormClass = pom_class.orm_class

        # store the ORM class and the PomSom Mapper for this group
        #  in the top level of the ORM model (Entity)
        # this is necessary because the Kleio export file
        # only exports a class once, but a given source can
        # have multiple groups associated with the same class.
        # That is the case with persons, for example.
        # If later we want to know which ORM class to use for
        # for a given group, we can use this dictionary.
        # which is based on the actual class associated with each
        # group in the database.
        Entity.set_orm_for_group(group.kname, ormClass)
        # Also cache the relation between group name and PomSomMapper
        # Note that many groups can be mapped to the same PomSomMapper
        # this is common with persons, objects, acts, etc.
        # where different names are given in Kleio to the same entity class.
        cls.group_pom_classes[group.kname] = pom_class

        entity_from_group: Entity = ormClass()
        entity_from_group.groupname = group.kname

        if group.kname == "caso":
            pass  # remove after DEBUG

        # extra_info =  this will store the extra information in comment and original words
        extra_info: dict = dict()  # {el1:{'core':'','comment':'','original':''},el2:...}
        group_obs = ""  # in previous versions extra info was stored in the obs column. Now it is stored in extra_info
        columns = inspect(ormClass).columns
        entity_has_extra_info_column = "extra_info" in [c.name for c in columns]
        # Certain columns are not mapped to elements, so we need to skip them
        skip_columns = [
            "the_source",
            "the_line",
            "the_level",
            "the_order",
            "indexed",
            "updated",
            "inside",
            "groupname",
            "extra_info",
        ]
        # avoid detached instance error with pom_class
        insp = inspect(pom_class)
        if insp.detached:
            session.add(pom_class)

        for column in set([c.name for c in columns]):
            if column in skip_columns:
                continue
            cattr: PomClassAttributes = pom_class.column_to_class_attribute(column, session)
            if cattr is None:  # cols as updated and indexed not mapped
                continue
            if cattr.colclass == "id":
                pass
            element: KElement = group.get_element_by_name_or_class(cattr.colclass)
            if element is not None and element.core is not None:
                # Update the association between the element and the column
                # in the Entity class so that it can be used later
                # for instance in to_kleio() methods
                group_elements_to_columns: dict = Entity.group_elements_to_columns.get(group.kname, {})
                group_elements_to_columns[element.name] = column
                Entity.group_elements_to_columns[group.kname] = group_elements_to_columns

                core_value = str(element.core)
                try:
                    # if value too long for column truncate with warning
                    if cattr.coltype != "numeric":
                        if len(element.core) > cattr.colsize:
                            # Problema que em alguns casos as colunas são números
                            warnings.warn(
                                f"""Element {element.name} of group {group.kname}:{group.id}"""
                                f""" is too long for column {cattr.colname}"""
                                f""" of class {pom_class.id}"""
                                f""" truncating to {cattr.colsize} characters""",
                                stacklevel=2,
                            )
                            core_value = element.core[: cattr.colsize]
                    if group.kname == "ls":
                        pass
                    setattr(entity_from_group, cattr.colname, core_value)
                    extra_info.update(
                        {
                            cattr.colname: {
                                "kleio_element_name": element.name,
                                "kleio_element_class": element.element_class,
                                "entity_attr_name": cattr.name,
                                "entity_column_class": cattr.colclass,
                            }
                        }
                    )
                    if cattr.colname == "obs":
                        group_obs = core_value  # we save the obs element for later
                    if element.comment is not None and element.comment.strip() != "":
                        extra_info[cattr.colname].update({"comment": element.comment.strip()})
                    if element.original is not None and element.original.strip() != "":
                        extra_info[cattr.colname].update({"original": element.original.strip()})
                except Exception as e:
                    session.rollback()
                    raise ValueError(
                        f"""Error while setting column {cattr.colname}"""
                        f""" of class {pom_class.id} """
                        f"""with element {element.name}"""
                        f""" of group {group.kname}:{group.id}: {e} """
                    ) from e

        # positional information in the original file
        entity_from_group.the_source = group.source_id
        entity_from_group.the_line = group.line
        entity_from_group.the_level = group.level
        entity_from_group.the_order = group.order
        extra_info = {k: v for k, v in extra_info.items() if v != {}}
        # for elname, extras in extra_info.items():
        #     el_obs = ''
        #     if extras.get('comment', None) is not None and extras['comment'].strip() != '':
        #         el_obs = el_obs + f"# {extras['comment']}. "
        #     if extras.get('original', None) is not None and extras['original'].strip() != '':
        #         el_obs = el_obs + f"% {extras['original']}. "
        #     if el_obs != '':
        #         group_obs = f"{group_obs} {elname} {el_obs}"
        # if group_obs.strip() != '':
        #     entity_from_group.obs = group_obs.strip()
        if len(extra_info) > 0:
            if not entity_has_extra_info_column:
                # we need to store the extra_info in the obs column
                if group_obs is not None and group_obs.strip() != "":
                    group_obs = f"{group_obs.strip()} extra_info: {json.dumps(extra_info)}"
                else:
                    group_obs = f"extra_info: {json.dumps(extra_info)}"

        # store the extra_info in the extra_info column
        entity_from_group.extra_info = extra_info
        entity_from_group.obs = group_obs

        # check if we have an id from the group
        # check if this group is enclosed in another
        container_id = group.get_container_id()
        if container_id not in ["root", "None", "", None]:
            entity_from_group.inside = container_id
        else:
            entity_from_group.inside = None

        # we have successfully created the entity from the group

        return entity_from_group

    @classmethod
    def store_KGroup(cls, group: KGroup, session=None):
        """Store a Kleio Group in the database

        Will recursively store all the groups included in this group.

        If the group is already in the database it will be deleted, as well
        as all included groups.

        This is the main method that import Kleio transcripts into the database.
        """
        if session is None:
            raise ValueError("No session provided")

        entity_from_group: Entity = cls.kgroup_to_entity(group, session)
        exists: Entity = session.get(entity_from_group.__class__, entity_from_group.id)

        if exists is not None:
            # we now delete the existong entity and all included entities
            # this is a recursive delete enabled by the cascade="all,delete-orphan
            # We need to take into account that inbound relations to this entity
            # will have the destination column set to None by SQLAlchemy configuration
            # so we need to same the id of inbound relations and restore the destination
            # id after the entity is reinserted.
            session.delete(exists)
            session.commit()  # we need to commit otherwise sqlalchemy will use the id and not delete
        try:
            session.add(entity_from_group)
            session.commit()
        except IntegrityError as e:
            session.rollback()
            logger.error(f"IntegrityError while storing group {group.id}: {e}")
            raise e  # TODO create our own Exception
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Exception while storing group {group.id}: {e}")
            session.rollback()
            raise e

        in_group: KGroup
        for in_group in group.contains():
            cls.store_KGroup(in_group, session)
        try:
            session.commit()
        except Exception as e:  # pylint: disable=broad-except
            session.rollback()
            raise e

    def __repr__(self):
        return (
            f'PomSomMapper(id="{self.id}", '
            f'table_name="{self.table_name}", '
            f'class_group="{self.group_name}", '
            f'super_class="{self.super_class}" '
            f")"
        )

    def __str__(self):
        r = f"{self.id} table {self.table_name} super {self.super_class}\n"
        for cattr in self.class_attributes:  # pylint: disable=no-member
            r = r + f"{cattr.the_class}.{cattr.name} \t"
            r = r + f"class {cattr.colclass} \t"
            r = r + f"col {cattr.colname} \ttype {cattr.coltype} "
            r = r + f"size {cattr.colsize} precision {cattr.colprecision}"
            r = r + f"primary key {cattr.pkey} \n"
        return r


class PomClassAttributes(Base):  # pylint: disable=too-few-public-methods
    """
    Attribute of a PomClass. Maps kleio group element to table columns

    the_class: id of the PomSomClass this attribute is attached to.
    name     : name of of the attribute
    colname  : name of the column in the corresponding table
    colclass : class of the column (element source if different from colname)
    coltype  : type of the column
    colsize  : size of the column, int
    colprecision: precision of the column (if decimal), int
    pkey     : if > 0 order of this column in the primary key of the table

    """

    __tablename__ = "class_attributes"

    the_class: Mapped[str] = mapped_column(String, ForeignKey("classes.id"), primary_key=True)

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    colname: Mapped[str] = mapped_column(String(32))
    colclass: Mapped[str] = mapped_column(String(32))
    coltype: Mapped[str] = mapped_column(String(32))
    colsize: Mapped[int] = mapped_column(Integer)
    colprecision: Mapped[int] = mapped_column(Integer)
    pkey: Mapped[int] = mapped_column(Integer)

    pom_class: Mapped["PomSomMapper"] = relationship(
        "PomSomMapper", foreign_keys=[the_class], backref="class_attributes"
    )

    def __repr__(self):
        return (
            f'PomClassAttributes(the_class="{self.the_class}", '
            f'name="{self.name}", '
            f'colname="{self.colname}", '
            f'colclass="{self.colclass}", '
            f'coltype="{self.coltype}", '
            f'colsize="{self.colsize}", '
            f'colprecision="{self.colprecision}", '
            f'pkey="{self.pkey}" '
            f")"
        )
