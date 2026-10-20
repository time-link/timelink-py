"""Record linking for timelink.

Phase 2b of the web migration: this package will grow into the full
port of the MHK record-linking engine (see
docs/web-migration/record-linking-port.md). It starts with the
service layer the web linking UI needs — same-as, unlink and
occurrence listing — built on the existing REntity/Link models in
timelink.api.models.rentity.
"""
from .service import (  # noqa: F401
    get_rid_for,
    unlink_occurrence,
    same_as,
    rperson_occurrences,
)
