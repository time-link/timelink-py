import logging
import warnings
from typing import Optional, Type, List

# pylint: disable=import-error

from sqlalchemy import Column, String, Integer, ForeignKey, Table, Float, select
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import relationship
from sqlalchemy import exc as sa_exc

from timelink.kleio.groups import KGroup, KElement
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.entity import Entity

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
       the database (DBSystem.db_init) and updated during import,
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

    See timelink.models.base_mappings.py for the core data for
    bootstrapping of the mapping information.

    Both steps are ensured by DBSystem.init_db

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
    __allow_unmapped__ = True

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    table_name = Column(String)
    group_name = Column("group_name", String(32))
    super_class = Column("super", String)
    __mapper_args__ = {
        "polymorphic_identity": "class",
        "inherit_condition": id == Entity.id,
    }
    # stores the ORM mapper for this mapping (source, act,person...)
    orm_class: Entity
    # Class attribute stores current PomSomMappings keyed by id
    pom_classes: dict = {}

    def ensure_mapping(self, session=None):
        """
        Ensure that a table exists to support
        this SOM Mapping and an ORM class is created
        to represent data of objects from this mapping.

        Checks if there is a table definition
        to support this mapping. If not a new table
        definition is created with information from the
        class attributes.

        A new ORM class is also created for mapping the new
        table. The new ORM class will extend the superclass
        ORM mapping

        """

        if not hasattr(self, "orm_class"):
            self.orm_class = None

        # if we have ensured before return what we found then
        if self.orm_class is not None:
            return self.orm_class

        # if not check if Entity knows about an orm class
        # if so return it and save for next time
        my_orm = Entity.get_orm_for_pom_class(self.id)
        if my_orm is not None:
            self.orm_class = my_orm
            return self.orm_class

        # we have no ORM mapping for the SomPomMapper
        # First check if we have this table already mapped to some Entity.
        # This might happen if we have different kleio groups mapped to the
        # same table, in order to make the kleio transcripts more readable
        # (it happens frequently with the table 'acts').
        # If so we will reuse the existing Table class
        # It can also happen that while not having a ORM mapping the table
        # can already exist in the database as result of previous imports.
        #
        # Note that non core PomSomMappings and corresponding ORM classes,
        # which are dynamically defined during import, have to be recreated
        # from the database information each time an application runs.
        metadata_obj = type(self).metadata  # pylint: disable=no-member
        pytables = metadata_obj.tables  # these are the tables known to ORM

        dbengine: Engine = session.get_bind()
        insp = inspect(dbengine)
        dbtables = insp.get_table_names()  # these are the ones in the database

        my_table: Table
        if self.table_name in pytables.keys():
            # table is known to ORM we used the Table class there
            my_table = pytables[self.table_name]
        elif self.table_name in dbtables:
            # the table exists in the database, we introspect
            my_table = Table(self.table_name, metadata_obj, autoload_with=dbengine)
            # we need to ensure that the foreign key relation exists with super talbe
            # otherwise the ORM mapping further down will fail.
            if self.super_class not in ["root", "base"]:
                # print("Getting super class " + self.super_class)
                pom_super_class: PomSomMapper = PomSomMapper.get_pom_class(
                    self.super_class, session
                )
                if pom_super_class is not None:
                    super_class_table_id = pom_super_class.table_name + ".id"
                else:
                    message = (
                        "Creating mapping for %s super class %s not found"
                        " Default to entities as super class"
                    )
                    logger.warning(message, self.id, self.super_class)
                    super_class_table_id = "entities.id"
                pytype = my_table.c.id.type
                my_table.append_column(
                    Column(
                        "id",
                        pytype,
                        ForeignKey(super_class_table_id),
                        primary_key=True,
                    ),
                    replace_existing=True,
                )
        else:
            # Table is unknown to ORM mapper and does not exist in the database
            # This is the dynamic part, we create a table with
            # the definition the "class" and "class_attributes" tables
            # fetched by this class
            # NOTE this does not take into account that the columns
            #       may already exist in the super class or up in the
            #       class hierarchy. Not sure if this the way it is supposed
            #       to be or if it is a problem to be dealt with here.
            #       SQLAchemy will rename the columns to avoid conflict
            #       automatically
            my_table = Table(self.table_name, metadata_obj, extend_existing=True)
            cattr: Type["PomClassAttributes"]
            for cattr in self.class_attributes:  # pylint: disable=no-member
                PyType: str
                pom_type = cattr.coltype.lower()
                if pom_type == "varchar":
                    PyType = String(cattr.colsize)
                elif pom_type == "numeric" and cattr.colprecision == 0:
                    PyType = Integer
                elif pom_type == "numeric" and cattr.colprecision > 0:
                    PyType = Float
                else:
                    PyType = String
                # print(f"Inferred python type for {cattr.colname}: ", PyType)

                if cattr.pkey != 0:
                    if self.super_class not in ["root", "base"]:
                        # print("Getting super class " + self.super_class)
                        pom_super_class: PomSomMapper = PomSomMapper.get_pom_class(
                            self.super_class, session
                        )
                        if pom_super_class is not None:
                            super_class_table_id = pom_super_class.table_name + ".id"
                        else:
                            message = (
                                "Creating mapping for %s super class %s not found"
                                " Default to entities as super class"
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
                    my_table.append_column(
                        Column(cattr.colname, PyType, primary_key=False),
                        replace_existing=True,
                    )
            my_table.create(session.get_bind())
            session.commit()
            # End of creation of a dynamic mapping and table

        # we know create a new ORM mapping for this PomSomMapper
        super_orm = Entity.get_orm_for_pom_class(self.super_class)
        if super_orm is None:
            super_orm = pom_super_class.ensure_mapping(session)
        props = {
            "__table__": my_table,
            "__mapper_args__": {"polymorphic_identity": self.id},
        }
        try:
            with warnings.catch_warnings():
                # We ignore warning related to duplicate fields in
                # specialized classes (obs normally, but also the_type...)
                warnings.simplefilter("ignore", category=sa_exc.SAWarning)
                my_orm = type(self.id.capitalize(), (super_orm,), props)
        except Exception as exc:
            logger.ERROR(Exception(f"Could not create ORM mapping for {self.id}"), exc)

        self.orm_class = my_orm

        return self.orm_class

    @classmethod
    def get_pom_classes(cls, session) -> Optional[List["PomSomMapper"]]:
        """
        Get the pom_classes from database data.

        Note that this method does not ensure that a ORM mapper is created
        for each class. Use pom_class.ensure_mapping() method to dynamically
        produce the ORM class

        :return: A list of SomPomMappers object for each class in the db
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
        if cls.pom_classes and len(cls.pom_classes) > 0:
            pass
        else:
            cls.get_pom_classes(session)
        return list(cls.pom_classes.keys())

    @classmethod
    def get_pom_class(cls, pom_class_id: String, session):
        """
        Return the pom_class object for a given pom_class_id.

        See also Entity.get_orm_for_pom_class

        :param pom_class_id: the id of a pom_class
        """
        return session.get(cls, pom_class_id)

    @classmethod
    def get_pom_class_from_group(cls, group: KGroup, session=None):
        # TODO use property instead
        pom_id = getattr(group, "_pom_class_id", None)
        if pom_id is None:
            kname = group.kname
            for pom in cls.get_pom_classes(session):
                if kname == pom.group_name:
                    # TODO use a setter
                    pom_id = pom.id
                    break
        if pom_id:
            return cls.get_pom_class(pom_id, session)
        else:
            return None

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

    def element_class_to_column(self, eclass: str) -> str:
        """
        Return the column name corresponding to a group element class
        :param eclass: the class of an element (included in the export file
        :return: the name of the column corresponding to this element in the
        mapped table.
        """
        cattr: PomClassAttributes = (
            self.class_attributes.filter(  # pylint: disable=no-member
                PomClassAttributes.pom_class == eclass
            )
        )
        return cattr.colname

    @classmethod
    def kgroup_to_entity(cls, group: KGroup, session=None, with_pom=None) -> Entity:
        """
        Store a Kleio Group in the database.

        :param group: a Kleio Group
        :param with_pom: id of a PomSom class to handle storing this group
        :return: An ORM object that can store this group in the database

        To produce the ORM-POM representation of a group we need to find
        the PomSomMapper specific to that group, using the following:

            * if with_pom is given with a PomSomMapper id we fetch that
            * if the group was imported it should have _pom_class_id
            * if neither then we search for a PomSom mapper with "groupname"
               equal to the name of the group.
        """
        if with_pom is not None:
            pom_class_id = with_pom
            pom_class = cls.get_pom_class(pom_class_id, session)
        else:
            pom_class = cls.get_pom_class_from_group(group, session)

        if pom_class is None:
            raise ValueError(
                f"Could not determine PomSomMapper for this group: {group}"
            )

        pom_class.ensure_mapping(session)
        ormClass = Entity.get_orm_for_pom_class(pom_class.id)
        entity_from_group: Entity = ormClass()
        entity_from_group.groupname = group.kname
        # columns = inspect(ormClass).columns

        for cattr in pom_class.class_attributes:
            if cattr.colclass == "id":
                pass
            element: KElement = group.get_element_for_column(cattr.colclass)
            if element is not None and element.core is not None:
                try:
                    setattr(entity_from_group, cattr.colname, str(element.core))
                except Exception as exc:
                    raise ValueError(
                        f"""Error while setting column {cattr.colname}"""
                        f""" of class {pom_class.id} """
                        f"""with element {element.name}"""
                        f""" of group {group.kname}:{group.id}: {exc} """
                    ) from exc

        # positional information in the original file
        entity_from_group.the_line = group.line
        entity_from_group.the_level = group.level
        entity_from_group.the_order = group.order

        # check if we have an id from the group

        # check if this group is enclosed in another
        container_id = group.get_container_id()
        if container_id not in ["root", "None", "", None]:
            entity_from_group.inside = container_id
        return entity_from_group

    @classmethod
    def store_KGroup(cls, group: KGroup, session, with_pom=None):
        entity_from_group: Entity = cls.kgroup_to_entity(group, session)
        exists = session.get(entity_from_group.__class__, entity_from_group.id)
        if exists is not None:
            session.delete(exists)
            session.commit()

        try:
            session.add(entity_from_group)
            session.commit()
        except Exception as exc:
            print(exc)

        in_group: KGroup
        for in_group in group.includes():
            cls.store_KGroup(in_group, session)

        try:
            session.commit()
        except Exception as exc:
            print(exc)

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


class PomClassAttributes(Base):
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

    the_class = Column(String, ForeignKey("classes.id"), primary_key=True)

    pom_class = relationship(
        "PomSomMapper", foreign_keys=[the_class], backref="class_attributes"
    )
    name = Column(String(32), primary_key=True)
    colname = Column(String(32))
    colclass = Column(String(32))
    coltype = Column(String)
    colsize = Column(Integer)
    colprecision = Column(Integer)
    pkey = Column(Integer)

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
