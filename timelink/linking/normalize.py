"""Shared normalizers for record linking and database-native search.

Faithful Python ports of the MHK normalization functions
(``names.sql``, ``nvalues_info.sql`` in ``~/develop/mhk``, read-only
reference):

======================  =============================================
MHK                     here
======================  =============================================
``break_name``          :func:`break_name`
``plig``                :func:`is_name_particle`
``pligp``               :func:`is_place_particle`
``strip_commas``        :func:`strip_commas`
``strip_interrog``      :func:`strip_interrog`
``count_interrog``      :func:`count_interrog`
``normalize_place``     :func:`normalize_place`
``normalize_civil_status`` :func:`normalize_civil_status`
======================  =============================================

These are pure functions (no database access) so that the search
indexing (decision D5) and the linking engine (Phase 2b) normalize
values identically — build once, feed both.

:func:`fold_text` is the additional text normalizer for the D5 search
index: lowercase, accent-folded, whitespace-collapsed.
"""
import unicodedata
from typing import Tuple

# person-name particles (MHK plig, lang='PT'). TODO: load from a
# linking parameter (rl.pnames.stopwords.pt) like MHK intends.
NAME_PARTICLES_PT = frozenset({"da", "de", "do", "das", "dos", "a", "e", "o"})

# place particles (MHK pligp, lang='PT'). TODO: rl.places.stopwords.pt
PLACE_PARTICLES_PT = frozenset(
    {"da", "de", "do", "das", "dos", "a", "e", "o",
     "casais", "casal", "quinta", "s.", "sao", "santa"}
)


def break_name(name: str) -> Tuple[str, str]:
    """Split a name at the first space: (first_part, remainder).

    Port of MHK ``break_name``: leading whitespace is ignored, the
    remainder has leading whitespace removed; no space in the name
    yields ``(name, '')``.

    >>> break_name('joaquim carvalho')
    ('joaquim', 'carvalho')
    """
    name = name.lstrip() if name else ""
    if " " not in name:
        return name, ""
    first, rest = name.split(" ", 1)
    return first, rest.lstrip()


def is_name_particle(part: str, lang: str = "PT") -> bool:
    """True if a name token is a stop word (MHK ``plig``).

    Only Portuguese is implemented, as in MHK; other languages
    return False.
    """
    if lang == "PT":
        return part in NAME_PARTICLES_PT
    return False


def is_place_particle(part: str, lang: str = "PT") -> bool:
    """True if a place token is a stop word (MHK ``pligp``)."""
    if lang == "PT":
        return part in PLACE_PARTICLES_PT
    return False


def strip_commas(value: str) -> str:
    """Replace commas with spaces (MHK ``strip_commas``)."""
    if not value:
        return value
    return value.replace(",", " ")


def strip_interrog(value: str) -> str:
    """Remove '?' uncertainty markers (MHK ``strip_interrog``).

    In kleio sources a trailing '?' marks an uncertain value; removing
    it yields the value as if certain, :func:`count_interrog` keeps
    the uncertainty degree.
    """
    if not value:
        return value
    return value.replace("?", "")


def count_interrog(value: str) -> int:
    """Count '?' uncertainty markers (MHK ``count_interrog``)."""
    if not value:
        return 0
    return value.count("?")


def normalize_place(place: str, lang: str = "PT") -> str:
    """Normalize a place name (MHK ``normalize_place``).

    Strips commas, drops place particles, collapses whitespace.
    """
    if not place:
        return place
    words = []
    remains = strip_commas(place)
    while remains:
        particle, remains = break_name(remains)
        if not is_place_particle(particle, lang):
            words.append(particle)
    return " ".join(words)


# civil status ('ec') value prefixes -> normalized value (MHK
# normalize_civil_status: solt* -> s, cas* -> c, viuv* -> v)
CIVIL_STATUS_PREFIXES_PT = (("solt", "s"), ("cas", "c"), ("viuv", "v"))


def normalize_civil_status(value: str, lang: str = "PT") -> str:
    """Normalize a civil status ('ec') value (MHK ``normalize_civil_status``).

    MHK matches by SQL ``like 'solt%'`` etc.; here the same prefixes,
    case-insensitively. Uncertainty markers are stripped first.
    Unknown values are returned lower-cased and unchanged.
    """
    if not value:
        return value
    clean = strip_interrog(value).strip().lower()
    for prefix, normalized in CIVIL_STATUS_PREFIXES_PT:
        if clean.startswith(prefix):
            return normalized
    return clean


def split_person_name(name: str, lang: str = "PT") -> dict:
    """Break a person name into given name and surname tokens.

    Pure part of MHK's ``name_to_attributes``: the first non-particle
    token is the given name (``first_name``), the remaining
    non-particle tokens are surname parts. Particles stay attached to
    the surname token sequence ('de', 'da', ... belong between given
    name and surname).

    >>> split_person_name('joaquim de carvalho')
    {'first_name': 'joaquim', 'surname': ['de', 'carvalho']}
    """
    tokens = []
    remains = strip_commas(name or "")
    while remains:
        token, remains = break_name(remains)
        if token:
            tokens.append(token)
    first_name = None
    surname = []
    for token in tokens:
        if first_name is None and not is_name_particle(token, lang):
            first_name = token
        elif first_name is not None:
            surname.append(token)
    return {"first_name": first_name, "surname": surname}


def fold_text(text: str) -> str:
    """Normalize free text for search indexing (decision D5).

    Lowercase, accent-folded (NFKD), whitespace-collapsed — the
    Python-side equivalent of what FTS5 unicode61/trigram and
    PostgreSQL unaccent do at query time, so the indexed document and
    the linking normalizers agree on one canonical form.
    """
    if not text:
        return text
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return " ".join(folded.lower().split())
