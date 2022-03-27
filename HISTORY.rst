=======
History
=======

0.3.3 (2022-03-27)
------------------
* Fix building on Travis

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
