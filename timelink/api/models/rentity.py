from enum import Enum as PyEnum
import random
import math
from typing import Optional
from itertools import chain

from sqlalchemy import Enum, String, ForeignKey, update
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import object_session

from .entity import Entity
from .base_class import Base


class REntityStatus(PyEnum):
    """
    Status of a real entity.

    The following statuses are possible:

    Unlinked: unlinked entity, assumed as a real entity.
    Automatic: linked automatically by enetity resolution algorithms.
    Source: linked by the user in the source with same_as or x_same_as.
    Manual: linked manually by the user in the database after import.
    Valid: validated by the user (whatever the origin).
    N: legacy status, linked in MHK (considered valid). For importing data from MHK.

    Note that in SQLAlchemy what is persisted is the name of the enum
    "UNLINKED", "AUTOMATIC", "SOURCE", "MANUAL", "VALID", "MHK" etc...

    Note that changes to this list will require changes to the database schema in postgresql
    directly in the database.

    See: https://stackoverflow.com/questions/43519096/
                after-updating-enum-with-a-new-value-that-value-cannot-be-inserted-with-psycopg
    """

    # U=linked (single occurrence), A=Automatic, S=Source, M=Manual linked, V=Valid
    UNLINKED = "0"  # unlinked entity
    AUTOMATIC = "1"  # linked automatically
    SOURCE = "2"  # linked in the source with same_as or x_same_as
    MANUAL = "3"  # Linked manually by the user in the database after import
    VALID = "4"  # Validated by the user (whatever the origin)
    MHK = "N"  # legacy status, linked in MHK (considered valid)
    N = "MHK"  # legacy status, linked in MHK (considered valid)


class REntity(Entity):
    """
    Represents Real Entities in the database.

    Real entities are the result of entity resolution.
    They aggregate the information of several entities
    in the database that are believed to represent the same real-world entity.

    The representation supports reversing the entity resolution
    process. A mapping between the real entity and the entities
    that compose is maintained in the `links` table.

    We use the term "REntity" to avoid confusion with the term "entity",
    and often use to unlinked entities as "occurrences".

    Note that it is possible for an occurrence to be linked
    to more than one real entity. This can happen when the
    different users have different opinions about the identity
    of the entities.


    """

    __tablename__ = "rentities"
    __mapper_args__ = {"polymorphic_identity": "rentity"}

    id: Mapped[str] = mapped_column(
        String(64), ForeignKey(Entity.id, ondelete="CASCADE"), primary_key=True
    )
    user: Mapped[str] = mapped_column(
        String(64)
    )  # user that identified this real entity
    description: Mapped[str] = mapped_column(
        String(4096)
    )  # description of the real entity
    status: Mapped[REntityStatus] = mapped_column(
        Enum(REntityStatus), nullable=False
    )  # status of the real entity
    obs: Mapped[Optional[str]] = mapped_column(
        String
    )  # observations about the real entity

    occurrences: Mapped[list["Link"]] = relationship(
        "Link", back_populates="rentity"
    )  # One-to-many relationship

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"REntity(id={sr}, "
            f"user={self.user}, "
            f"description={self.description}, "
            f"status={self.status}, "
            f"obs={self.obs}"
            f")"
        )

    # introspection
    def get_user(self):
        """Get the user that identified this real entity"""
        return self.user

    def set_user(self, user):
        """Set the user that identified this real entity"""
        self.user = user

    def get_description(self):
        """Get the description of the real entity"""
        return self.description

    def set_description(self, description):
        """Set the description of the real entity"""
        self.description = description

    def get_status(self):
        """Get the status of the real entity"""
        return self.status

    def set_status(self, status):
        """Set the status of the real entity"""
        self.status = status

    def get_obs(self):
        """Get the observations about the real entity"""
        return self.obs

    def set_obs(self, obs):
        """Set the observations about the real entity"""
        self.obs = obs

    def get_occurrences(self):
        """Get the occurrences of the real entity"""
        return self.occurrences

    @property
    def contains(self):
        # get the sqlalchemy session of self
        session = object_session(self)
        # collect all the entities that are linked to this real entity and return the cones they contain
        return list(
            chain.from_iterable(
                session.get(Entity, occ.entity).contains for occ in self.occurrences
            )
        )

    @classmethod
    def get_rentity_brief(cls, rentity_id: str, session=None, db=None):
        """
        Fetch a real entity from the database
        """
        if session is not None:
            r: REntity = session.get(REntity, rentity_id)
        elif db is not None:
            with db.session() as session:
                r: REntity = session.get(REntity, rentity_id)
        else:
            raise ValueError("Error, session or db needed")
        return r

    @classmethod
    def get_rentity_full(cls, rentity_id: str, session=None, db=None):
        """
        Fetch a real entity from the database with all the
        attributes, relationships and contained objects of
        the occurrences of the real entity.

        I think this corresponds to an eager fetch in SQLAlchemy
        """

        if session is not None:
            # Fetch eargely the occurrences

            r: REntity = session.get(REntity, rentity_id)
        elif db is not None:
            with db.session() as session:
                r: REntity = session.get(REntity, rentity_id)
        else:
            raise ValueError("Error, session or db needed")

        return r

    @classmethod
    def get(cls, rentity_id: str, session=None):
        """Get a real entity from the database"""

        if session is None:
            raise ValueError("Error, session needed")

        with session:
            r: REntity = session.get(REntity, rentity_id)
        return r

    @classmethod
    def already_real(cls, occurrence: str, user="user", session=None):
        """Check if an occurrence is already linked to a real entity
        for a given user"""
        if session is None:
            raise ValueError("Error, session needed")
        with session:
            real = (
                session.query(Link)
                .filter(Link.entity == occurrence, Link.user == user)
                .all()
            )
        return len(real) > 0

    @classmethod
    def get_real_entity(cls, occurrence: str, user="user", session=None):
        """Get the real entity of an occurrence
        TODO: this should be an instance method of Entity
        """
        if session is None:
            raise ValueError("Error, session needed")
        with session:
            links = (
                session.query(Link)
                .filter(Link.entity == occurrence, Link.user == user)
                .all()
            )
            if len(links) == 0:
                return None
            return links[0].rid

    @classmethod
    def delete(cls, rentity_id: str, silent=True, session=None):
        """
        Delete a real entity from the database

        If sucessfull returns the id of the deleted real entity
        if not returns and silent=True returns None otherwise raises an exception
        """

        if session is not None:
            with session:
                # session.commit()
                # session.begin()
                # delete the real entity
                try:
                    re = session.get(REntity, rentity_id)
                    if re is None:
                        if not silent:
                            raise ValueError(f"Error, {rentity_id} does not exist")
                        return None
                    else:
                        for link in re.occurrences:
                            session.delete(link)
                        session.delete(re)
                except Exception as e:
                    session.rollback()
                    raise e

                session.commit()
        return rentity_id

    @classmethod
    def same_as(
        cls,
        id1: str,
        id2: str,
        user="user",
        status=None,
        real_id=None,
        real_id_prefix=None,
        description=None,
        rule=None,
        session=None,
    ) -> str:
        """Returns a real entity id linking id1 and id2.

        Args:
            id1: id of the first entity
            id2: id of the second entity
            user: user that linked the entities
            status: status of the link (default M)
            real_id: id of the real entity (if none a random id is generated)
            real_id_prefix: prefix of the generated real entity id
            description: description of the real entity (defaults to description or name of first entity)
            rule: rule used to link the entities
            session: database session

        if id1 and id2 are both unliked occurrences then a new real entity is created
            associated with user.  if real_id is given is not given a random id is generated.

        if id1 is a real entity and id2 is not, then id2 is added to id1 and id1 returned
        if id2 is a real entity and id1 is not, swap and do as above.
        if both id1 and id2 are real entities, merge them and keep the id of the real
            entity with higher status V->M->S->A->U

        in all the cases linking two id2 of different types or inheriting from a
        common type not equal to Entity is an error."""
        if session is None:
            raise ValueError("Error, session needed")

        with session:
            # session.commit()
            # session.begin()
            if id1 == id2:
                return cls.make_real(
                    id1,
                    user=user,
                    status=status,
                    real_id=real_id,
                    real_id_prefix=real_id_prefix,
                    description=description,
                    rule=rule,
                    session=session,
                )

            # check if Entity id1 and id2 exists and are of the same type
            eid1 = session.get(Entity, id1)
            eid2 = session.get(Entity, id2)
            if eid1 is None or eid2 is None:
                raise ValueError(f"Error, {id1} and {id2} must exist in the database")

            if eid1.pom_class != eid2.pom_class:
                raise ValueError(f"Error, {id1} and {id2} must be of the same type")

            # check if id1 and id2 are already linked
            # Query the links table for entity=id1 and user=user and return the rid
            # if it exists otherwise return None
            # if it exists return the Real Entity
            r1 = (
                session.query(Link.rid)
                .filter(Link.entity == id1, Link.user == user)
                .scalar()
            )
            r2 = (
                session.query(Link.rid)
                .filter(Link.entity == id2, Link.user == user)
                .scalar()
            )

            # if r1 and r2 are not None and equal return r1
            if r1 is not None and r2 is not None and r1 == r2:
                if real_id is not None and r1 != real_id:
                    raise ValueError(
                        f"Error, {id1} and {id2} are already linked to {r1}"
                    )

                return session.get(REntity, r1)

            if rule is None:
                rule = f"same_as('{id1}', '{id2}')"

            if status is None:
                status = REntityStatus.MANUAL

            if r1 is None and r2 is None:
                # both are unlinked occurrences

                if description is None:
                    desc = "<No description>"
                    if hasattr(eid1, "description"):
                        desc = eid1.description
                    elif hasattr(eid1, "name"):
                        desc = eid1.name  # TODO check any column of class "Name"
                else:
                    desc = description

                if real_id is None:
                    if real_id_prefix is None:
                        ridp = "r" + eid1.pom_class[0]  # we take firs
                    real_id = cls.generate_id(session=session)
                    real_id = f"{ridp}-{real_id}"
                else:
                    # check if real_id exists
                    if session.get(REntity, real_id) is not None:
                        raise ValueError(f"Error, {real_id} already exists")

                r = REntity(id=real_id, user=user, description=desc, status=status)
                session.add(r)
                session.flush()
                l1 = Link(rid=real_id, entity=id1, user=user, status=status, rule=rule)
                l2 = Link(rid=real_id, entity=id2, user=user, status=status, rule=rule)
                session.add(l1)
                session.add(l2)

            elif r1 is not None and r2 is None:
                # r1 is a real entity and r2 is an occurrence
                if real_id is not None:
                    if r1.id != real_id:
                        raise ValueError(f"Error, {id1} is already linked to {r1}, cannot change to {real_id}. "
                                         f"Use make_real('{id2}', real_id='{real_id}')")
                link = Link(rid=r1, entity=id2, user=user, status=status, rule=rule)
                session.add(link)
                r = session.get(REntity, r1)

            elif r1 is None and r2 is not None:
                # rid2 is a real entity and id1 is an occurrence
                if real_id is not None:
                    if r2 != real_id:
                        raise ValueError(f"Error, {id2} is already linked to {r2}, cannot change to {real_id}. "
                                         f"Use make_real('{id1}', real_id='{real_id}')")
                link = Link(rid=r2, entity=id1, user=user, status=status, rule=rule)
                session.add(link)
                r = session.get(REntity, r2)

            # both are real entities
            else:
                real1 = session.get(REntity, r1)
                real2 = session.get(REntity, r2)

                if real1.status.value > real2.status.value:
                    # r1 is more important
                    # update links with rid=r2 to rid=r1
                    # update with SQLALchemy update statement
                    # update links set rid = r1 where rid = r2
                    stmt = update(Link).where(Link.rid == r2).values(rid=r1, rule=rule)
                    session.execute(stmt)
                    r = real1
                    session.delete(real2)
                else:
                    # r2 is more important
                    # update links with rid=r1 to rid=r2
                    # update with SQLALchemy update statement
                    # update links set rid = r2 where rid = r1
                    stmt = update(Link).where(Link.rid == r1).values(rid=r2, rule=rule)
                    session.execute(stmt)
                    r = real2
                    session.delete(real1)

            session.commit()
        return r

    @classmethod
    def generate_id(cls, length=6, session=None):
        """Generate a random n digit id for a real entity

        Needs a section to test if already exists
        """
        if session is None:
            raise ValueError("Error, session needed")

        # storing strings in a list
        digits = [i for i in range(0, 10)]

        # initializing a string
        random_str = ""

        circuit_breaker = 1000000
        while True:
            circuit_breaker -= 1
            if circuit_breaker < 0:
                raise ValueError(
                    f"Error, could not generate a unique id with {length} digits"
                )
            random_str = ""
            for _i in range(length):
                # generating a random index
                index = math.floor(random.random() * 10)
                random_str += str(digits[index])
            # check if the id already exists
            if session.get(Entity, random_str) is None:
                break  # if not return
        return random_str

    @classmethod
    def make_real(
        cls,
        id1: str,
        user="user",
        status=REntityStatus.MANUAL,
        real_id=None,
        real_id_prefix=None,
        description=None,
        rule=None,
        session=None,
    ):
        """Make an entity a real entity

        This creates a real entity from a single occurence
        """
        if session is None:
            raise ValueError("Error, session needed")

        if rule is None:
            rule = f"make_real('{id1}')"
        with session:
            # session.commit()
            # session.begin()

            # check if id1 exists
            eid1 = session.get(Entity, id1)
            if eid1 is None:
                raise ValueError(f"Error, {id1} must exist in the database")

            # check if id1 is already linked
            r1 = (
                session.query(Link.rid)
                .filter(Link.entity == id1, Link.user == user)
                .scalar()
            )

            if r1 is not None:
                if real_id is None:
                    return r1
                else:
                    if r1 == real_id:
                        return r1
                    else:
                        raise ValueError(f"Error, {id1} is already linked to {r1}")

            if description is None:
                desc = "<No description>"
                if hasattr(eid1, "description"):
                    desc = eid1.description
                elif hasattr(eid1, "name"):
                    desc = eid1.name
            else:
                desc = description

            if real_id is None:
                if real_id_prefix is None:
                    ridp = "r" + eid1.pom_class[0]  # we take firs
                real_id = cls.generate_id(session=session)
                real_id = f"{ridp}-{real_id}"

            r = REntity(id=real_id, user=user, description=desc, status=status)
            session.add(r)
            session.flush()
            l1 = Link(rid=real_id, entity=id1, user=user, status=status, rule=rule)
            session.add(l1)
            session.commit()
            real_id = r.id
        return r

    def attach_occurrence(
        self, occ_id: str, user="user", status=REntityStatus.MANUAL, rule=None
    ) -> "REntity":
        """Attach an occurrence to a real entity

        Args:
            occ_id: id of the occurrence
            user: user that linked the occurrence
            status: status of the link
            rule: rule used to link the occurrence

        """
        if rule is None:
            rule = f"attach({self.id},'{occ_id}')"

        with object_session(self) as session:
            # check if the entiy exists
            if session.get(Entity, occ_id) is None:
                raise ValueError(f"Error, {occ_id} must exist in the database")

            link = Link(rid=self.id, entity=occ_id, user=user, status=status, rule=rule)
            self.occurrences.append(link)
            session.add(link)
            session.flush()
            session.commit()
        return self


class Link(Base):
    """
    Represents the link between a real entity and an entity.

    The link between a real entity and an entity is maintained in this table.
    """

    __tablename__ = "links"

    rid: Mapped[str] = mapped_column(
        String(64), ForeignKey(REntity.id, ondelete="CASCADE"), primary_key=True
    )
    entity: Mapped[str] = mapped_column(
        String(64), ForeignKey(Entity.id, ondelete="CASCADE"), primary_key=True
    )
    rule: Mapped[str] = mapped_column(
        String(4096)
    )  # rule used to link the entity to the real entity

    # The next two are redundant de normalized for efficiency
    user: Mapped[str] = mapped_column(
        String(64)
    )  # user that linked the entity to the real entity

    status: Mapped[REntityStatus] = mapped_column(
        Enum(REntityStatus), nullable=False
    )  # status of the link

    rentity: Mapped[REntity] = relationship(
        REntity, back_populates="occurrences", foreign_keys=[rid]
    )  # Many-to-one relationship

    def __repr__(self):
        return f"Link(rid={self.rid}, entity={self.entity}, rule={self.rule})"
