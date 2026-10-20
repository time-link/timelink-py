"""Service layer for the web linking UI.

Thin, session-taking wrappers over the REntity/Link models so pages
don't manipulate Link rows directly. Mirrors the manual linking loop
of MHK (`DoSameAs.java` / `DoUnlink.java` + `rentities.sql`):
link, unlink, and listing the occurrences of a real entity.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from timelink.api.models.entity import Entity
from timelink.api.models.rentity import Link, LinkStatus, REntity


def get_rid_for(occurrence_id: str, user: str, session: Session) -> Optional[str]:
    """The rid the occurrence is linked to for this user, if any."""
    return (
        session.query(Link.rid)
        .filter(Link.entity == occurrence_id, Link.user == user)
        .scalar()
    )


def unlink_occurrence(occurrence_id: str, user: str, session: Session) -> Optional[str]:
    """Remove the user's link between occurrence and its real entity.

    Deletes the Link row; if the real entity is left with no links it
    is removed as well (MHK remove_rperson behaviour). Returns the rid
    that was unlinked, or None.
    """
    links = (
        session.query(Link)
        .filter(Link.entity == occurrence_id, Link.user == user)
        .all()
    )
    if not links:
        return None
    rid = links[0].rid
    for link in links:
        session.delete(link)
    session.flush()
    remaining = session.query(Link).filter(Link.rid == rid).count()
    if remaining == 0:
        rentity = session.get(REntity, rid)
        if rentity is not None:
            session.delete(rentity)
    session.commit()
    return rid


def same_as(
    id1: str, id2: str, user: str, session: Session, status=LinkStatus.MANUAL
) -> REntity:
    """Link two occurrences (or an occurrence and an existing rid).

    If id2 is an existing real entity id, id1 is attached to it;
    otherwise delegates to REntity.same_as.
    """
    if session.get(Entity, id2) is not None and session.get(REntity, id2) is None:
        return REntity.same_as(id1, id2, user=user, status=status, session=session)
    rentity = session.get(REntity, id2)
    if rentity is None:
        raise ValueError(f"{id2} is neither an occurrence nor a real entity id")
    rentity.attach_occurrence(id1, user=user, status=status)
    # attach_occurrence closes its own session context, detaching the
    # instance it returns; re-fetch on the caller's session instead
    return session.get(REntity, id2)


def rperson_occurrences(rid: str, session: Session) -> List[Entity]:
    """The occurrence entities linked to a real entity (any user)."""
    rentity = session.get(REntity, rid)
    if rentity is None:
        return []
    occurrences = []
    for occ_id in rentity.get_occurrences():
        entity = session.get(Entity, occ_id)
        if entity is not None:
            occurrences.append(entity)
    return occurrences


def list_rentities(
    session: Session, user: Optional[str] = None
) -> List[dict]:
    """Real entities with their link counts, for the linking management page.

    Mirrors MHK ``rentities.sql`` / ``linking_show.vm``: one row per real
    entity, optionally restricted to the identifications of one user.
    """
    query = (
        session.query(
            REntity.id,
            REntity.user,
            REntity.status,
            REntity.description,
        )
        .order_by(REntity.id)
    )
    if user is not None:
        query = query.filter(REntity.user == user)
    rows = []
    for rid, ruser, rstatus, rdescription in query.all():
        occurrences = [
            entity
            for (entity,) in session.query(Link.entity)
            .filter(Link.rid == rid)
            .order_by(Link.entity)
            .all()
        ]
        rows.append(
            {
                "rid": rid,
                "user": ruser,
                "status": str(rstatus),
                "description": rdescription,
                "occurrences": occurrences,
                "n_occurrences": len(occurrences),
            }
        )
    return rows


def rentity_links(session: Session, rid: str) -> List[dict]:
    """The link rows of one real entity, with occurrence class for display."""
    links = (
        session.query(Link, Entity.pom_class)
        .outerjoin(Entity, Link.entity == Entity.id)
        .filter(Link.rid == rid)
        .order_by(Link.entity)
        .all()
    )
    return [
        {
            "entity": link.entity,
            "class": pom_class,
            "user": link.user,
            "status": str(link.status),
            "rule": link.rule,
        }
        for link, pom_class in links
    ]
