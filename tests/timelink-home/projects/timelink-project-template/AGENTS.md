# AGENTS.md

Guidance for AI coding agents working in this repository. Humans may follow it too.

## What this repository is

A **Timelink project directory**: Kleio source files associated with a
database. It serves as `timelink-home` in single-user, single-project mode,
and can also live inside the `projects/` directory of a multi-project home,
being used either standalone or as part of it. The `.timelink-project`
marker file in the root identifies the directory.

## Layout

| directory             | content                                                     |
|-----------------------|-------------------------------------------------------------|
| `sources/`            | Kleio source files (`.cli`, `.kleio`)                       |
| `structures/`         | structure files describing each type of source              |
| `mappings/`           | mappings between Kleio groups and database tables           |
| `inferences/`         | inference rules applied when processing the sources         |
| `identifications/`    | exports of the identification (record linking) process      |
| `database/sqlite/`    | SQLite database files (generated)                           |
| `database/backups/`   | database backups (generated)                                |
| `extras/`             | auxiliary project files: working documents, scripts, derived data |
| `notebooks/`          | Jupyter notebooks working with the project data             |
| `etc/doc/`            | pointers to the documentation                               |

## Rules

* **Do not delete or rename `.timelink-project`.** `find_local_kleio_home()`
  and the `timelink` CLI detect this directory by that marker; without it,
  detection falls back to fragile heuristics.
* **Never commit generated files.** Databases, backups and Kleio translation
  byproducts (`*.err`, `*.ids`, `*.org`, `*.old`, `*.cli-renamed`, `*.rpt`,
  `*.rep`, `*.files.json`, `strs/`) are covered by `.gitignore`; do not
  force-add them.
* **Kleio sources are transcriptions.** Files in `sources/` are scholarly
  work, and each file is copyright of its transcriber. Never rewrite them
  mechanically; content changes go through the researcher. Validate
  translations with the Kleio server before importing.
* **The database is derived data.** Everything in `database/` can be rebuilt
  from `sources/` by translating and importing; treat it as disposable.

## Processing the kleio sources (`.cli` files)

Sources are translated by the Kleio server (Docker) and imported into the
project database. `TimelinkNotebook` wraps the whole pipeline and is the
entry point used by the project notebooks. Run the notebooks from this
directory or from `notebooks/` so that the project is found.

1. Set up and verify:

```python
from timelink.notebooks import TimelinkNotebook

tlnb = TimelinkNotebook()   # starts/attaches the Kleio server, connects the database
tlnb.print_info()
```

2. List the sources with their translation status
   (`translated`, `errors`, `warnings` columns):

```python
kleio_files = tlnb.get_kleio_files(recurse=True)
```

3. Translate and import. Only changed files are retranslated; import is
   per file and replaces previous data for that file, so rerunning after
   editing a source is safe:

```python
tlnb.update_from_sources()
```

Force a full retranslation of everything by first cleaning the
translations:

```python
tlnb.kleio_server.translation_clean("", recurse="yes")
tlnb.update_from_sources()
```

4. Check the results. Import errors and warnings are per file:

```python
imported_files_df = tlnb.get_import_status()
errors = imported_files_df.query("import_errors > 0 or errors > 0")
if len(errors) > 0:
    print(errors)

rpt = tlnb.get_translation_report(imported_files_df, 0)   # 0 = first file
print(rpt)
rpt = tlnb.get_import_rpt(imported_files_df, rows=[0])
print(rpt)
```

Full walkthroughs: `notebooks/02-tutorial.ipynb` (queries too),
`notebooks/A1-kleio-files.ipynb` (file processing),
`notebooks/A2-database-explore.ipynb` (database schema). Read them for
project-specific variants before inventing new code.

## Answering common data queries

All recipes use the `tlnb` from the previous section. Attribute names
below (`naturalidade`, `faculdade`) are examples — discover the actual
attribute types of this project with `attribute_values` or
`tlnb.db.describe('attribute')`.

* **People by name**:

```python
from timelink.pandas import pname_to_df

df = pname_to_df("Andrade", db=tlnb.db)             # exact/like match
df = pname_to_df("Machado", db=tlnb.db, similar=True)  # with variants
```

* **People with an attribute, optionally filtered by value** — the
  standard answer to "who has attribute X with value Y":

```python
from timelink.pandas import entities_with_attribute

df = entities_with_attribute(
    entity_type="person",
    the_type="naturalidade",
    the_value="Soure",                      # optional; SQL wildcards allowed
    show_elements=["name"],
    more_attributes=["faculdade"],          # extra columns to join in
    db=tlnb.db,
)
```

* **Attributes within a date window**: add `dates_in=(after, before)`,
  dates in `AAAAMMDD` form. To list the existing values of an attribute
  first (recommended before filtering by value):

```python
from timelink.pandas import attribute_values

values = attribute_values("naturalidade", db=tlnb.db)
values = attribute_values("naturalidade", dates_between=("16000101", "16501231"),
                          db=tlnb.db)
```

* **Acts at certain dates** (baptisms, marriages, deeds, ...): use the
  ORM. `Act.the_date` is a string in Kleio `AAAAMMDD` format (unknown
  parts zeroed), indexed, so range comparisons work as string
  comparisons:

```python
from sqlalchemy import select
from timelink.api.models import Act

with tlnb.db.session() as session:
    stmt = (
        select(Act)
        .where(Act.the_type == "baptismo")
        .where(Act.the_date.between("16400101", "16491231"))
    )
    acts = session.execute(stmt).scalars().all()
    for act in acts[:10]:
        print(act.id, act.the_date, act.the_type, act.loc, act.ref)
```

The DataFrame alternative for acts with attributes of participants is
`entities_with_attribute(entity_type="act", ...)`, with `name_like` to
filter by act name.

* **Deep inspection of one entity**: `entity.to_kleio()` dumps the full
  record (attributes, relations, group info) in kleio notation — much
  more informative than the table row:

```python
from timelink.api.models import Person, Attribute
from sqlalchemy import select

with tlnb.db.session() as session:
    stmt = select(Person).join(
        Person.attributes.and_(
            Attribute.the_type == "jesuita-entrada",
            Attribute.the_value.like("Coimbra"),
        )
    )
    for person in session.execute(stmt).scalars().all()[:10]:
        print(person.to_kleio())
```

* **Schema and table sizes** when facing an unfamiliar database:

```python
tlnb.table_row_count_df()                  # row counts per table
tlnb.db.get_models_ids()                   # ORM models
tlnb.db.describe("person", show=True)      # columns of a table/model
```

Dates in timelink are `AAAAMMDD` strings, possibly incomplete
(`16400000` = some month in 1640) and sometimes uncertain; compare them
as strings, not as datetime objects.

## Python environment: one shared venv, OUTSIDE this project

Do not create a virtual environment inside this repository, and do not
accept VS Code's *Create Environment* prompt — it always writes `.venv`
into the workspace root, and per-project venvs accumulate silently (one
cleanup of a multi-project home removed nine of them: 3.9 GB, ~209,000
files, created one by one over three years of accepting that prompt).

Instead, create one shared venv outside the project and register it as a
Jupyter kernel:

```bash
python3.12 -m venv ~/venvs/timelink
~/venvs/timelink/bin/pip install -U pip
~/venvs/timelink/bin/pip install timelink            # stable release, the default
# or, to exercise unreleased code:
~/venvs/timelink/bin/pip install -e /path/to/timelink-py-checkout

~/venvs/timelink/bin/python -m ipykernel install --user --name timelink \
    --display-name "Python (timelink)"
```

Kernel registrations are user-level, not per-folder: every notebook on the
machine can pick **Python (timelink)** from the kernel picker. This
replaces the per-project `.venv`.

To stop VS Code from offering to create environments, preselect the
interpreter — VS Code has no setting to relocate the `.venv` its Create
Environment button creates; preselection is what prevents the prompt. Add
to this project's `.vscode/settings.json` (not to the template: the path
is machine specific):

```json
{ "python.defaultInterpreterPath": "/ABSOLUTE/PATH/TO/venvs/timelink/bin/python" }
```

Project resolution never depended on the venv location: it depends on the
working directory. Run notebooks from this directory or from `notebooks/`;
`find_local_kleio_home()` finds the project by the marker file.

Maintenance: `~/venvs/timelink/bin/pip install -U timelink` (or `git pull`
in the checkout, for the editable form). To pin a research run to a
release, create a versioned sibling venv such as `~/venvs/timelink-1.2.0`.

## VS Code extension for Kleio

A Kleio extension for VS Code (syntax support for `.cli` files) ships in
`extras/vscode/`. Install the version provided with:

```bash
code --install-extension extras/vscode/kleio-1.0.20.vsix
```

## Project specifics

<!-- Describe here the source collections of this project, the conventions
     used by the researchers, and anything else an agent must know before
     editing sources, structures or notebooks. -->
