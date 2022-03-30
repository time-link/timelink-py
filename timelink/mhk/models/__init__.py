""" Handling of Database persistence for the Person Oriented Model (POM).

The classes on this module represent the core entities in the POM: entities,sources,
acts, people, objects, attributes and relations. SQLAlchemy is used as the
underlying ORM library.

They allow storage and query and also dynamic mapping of new types of
entities defined in ``kleio`` source files, through the PomSomMapper class.

For a detailed description of *Timelink* data models see: :doc:`som_pom_mapping`.

Also check  :class:`timelink.mhk.models.pom_som_mapper.PomSomMapper`

(c) Joaquim Carvalho 2021.
MIT License, no warranties.

"""
