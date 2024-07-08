=======
History
=======
1.1.11 (2024-07-7)

* Implements Issue43 (adds groupname filtering to attribute_values)
* Fixes bug in pandas.styles due to deprecation of matplotlib.cm
* Fix a problem with the release process.

1.1.10 (2024-05-19)

* Fix a bug in entities_with_attribute() filter_by parameter handling.

1.1.9 (2024-05-03)
------------------

* fix bug with to_kleio() in models (bad identation)


1.1.8 (2024-05-02)
------------------

* Fix bug with export_to_kleio()
* Several minor bug fixes

1.1.7 (2024-04-28)
------------------

* Adds new eattributes views to easily access line, level, groupname of attributes
* pandas.entities_with_attribute returns attribute type,line,level and obs.
* Adds reference requirements.txt file to notebook tests
* Adds TimelinkDatabase.export_as_kleio(ids,filename

1.1.6 (2024-04-24)
------------------

Fixes regression in 1.1.5.

1.1.5 (2024-04-24)
------------------
* Comments and original wording are now stored
  in the "obs" field of entities, preceeded by
  "extra_info:".

* If obs field contained explicit observations,
  these are preserved, and "extra_info:" is appended.

* A new method in the Entity class, get_extra_info()
  fetches the extra info as a dictionnary.

* Partially implements issue #9.

1.1.4 (2024-03-16)
------------------

Skips long imports in Travis CI

1.1.3 (2024-03-16)
------------------

Fixes a bug in update_from_sources() when import_with_errors was choosen


1.1.2 (2024-02-27)
------------------

Bug fixes #16 #24 #28

1.1.1 (2024-02-26)
------------------

* Includes basic templates, better integration with Travis CI

1.0.5 (2024-02-07)
------------------

* Fix minor bugs, better interaction with Docker and Jupyter notebooks.

1.0.4 (2024-02-06)
------------------

* Improved notebook integration, new tutorial and receipts notebooks in progress.

1.0.3 (2024-02-01)
------------------

* Use new deployment method with Travis

1.0.1 (2024-01-31)
------------------

* Fix travis build

1.0.0 (2024-01-30)
------------------

First release with Jupyter notebooks integration.

0.3.10 (2022-06-07)
-------------------
* Fix to_kleio() in models: now generates quotes and
  triple quotes when necessary.

0.3.9 (2022-05-26)
------------------
*  Fix missing import in kleio.groups

0.3.8 (2022-03-28)
------------------
* Fix bug with Session import in mhk.models.db

0.3.3 to 0.3.7 (2022-03-27)
---------------------------
* Fix build on travis with auto deployment

0.3.2 (2022-03-27)
------------------
* Fixes bug in package descrition preventing release in Pypi.

0.3.1 (2022-03-25)
------------------
* All core ORM models for MHK databases
* Dynamic generation of ORM models from XML
  files produced by the Kleio translator.
* Python definition of Kleio groups allows synonyms to be defined for
  localized elements.
* Import from XML file to MHK database
* CLI interface refactored with `Typer`
* Improved documentation

Developement related changes

* `black` can be used to format code
* More and better tests, handling of MHK
  installation or lack of in CI tests

0.3.0 (2022-03-05)
------------------
* Fixes bugs related to mapping legacy MHK databases

0.2.9 (2021-09-30)
------------------
* Update requirements and docs

0.2.10 (2022-03-30)
-------------------
* Adds indexes to models
* Added sqlite test db
* Better testing, travis integration improved
* Replaced click with typer in cli interface

0.2.9 (2021-09-30)
-------------------
* Update documentation.

0.2.8 (2021-09-30)
------------------

* Add to_json() method to KGroup, enabling Kleio to JSon serialization.

0.2.7 (2021-08-29)
------------------

* Auto build on Travis, with release to pypi
* Skeleton docs on readthedocs

0.1.0 (2021-07-09)
------------------

* First release on PyPI.

