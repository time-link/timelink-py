""" These mappings are needed to boostrap a new database.

They are used by TimelinkDatabase to initialize a new database.

Mappings as these can be generated from existing Timelink/MHK databases with:

.. code-block:: python

   pom_classes = session.query(PomSomMapper)
                        .where(Entity.pom_clas == 'class').all()
   for pom_class in pom_classes:
        print(f"'{pom_class.id}': [")
        print(repr(pom_class),',')
        for cattr in pom_class.class_attributes:
            print(repr(cattr),',')
        print('],')

Note that the order of the mappings is important. If a mapping
extends another mapping with 'super_class', the super class mapping must be defined
before the subclass mapping.

"""

from timelink.api.models.pom_som_mapper import PomSomMapper, PomClassAttributes

pom_som_base_mappings = {}

more_mappings = {
    "acusacoes": [
        PomSomMapper(
            id="acusacoes",
            table_name="acusacoes",
            group_name="acusa",
            super_class="object",
        ),
        PomClassAttributes(
            the_class="acusacoes",
            name="id",
            colname="id",
            colclass="id",
            coltype="varchar",
            colsize="64",
            colprecision="0",
            pkey="1",
        ),
        PomClassAttributes(
            the_class="acusacoes",
            name="idcaso",
            colname="idcaso",
            colclass="idcaso",
            coltype="varchar",
            colsize="64",
            colprecision="0",
            pkey="0",
        ),
        PomClassAttributes(
            the_class="acusacoes",
            name="literal",
            colname="literal",
            colclass="literal",
            coltype="varchar",
            colsize="16000",
            colprecision="0",
            pkey="0",
        ),
        PomClassAttributes(
            the_class="acusacoes",
            name="obs",
            colname="obs",
            colclass="obs",
            coltype="varchar",
            colsize="16000",
            colprecision="0",
            pkey="0",
        ),
        PomClassAttributes(
            the_class="acusacoes",
            name="origem",
            colname="origem",
            colclass="origem",
            coltype="varchar",
            colsize="16000",
            colprecision="0",
            pkey="0",
        ),
    ],
    "caso": [
        PomSomMapper(
            id="caso", table_name="casos", group_name="caso", super_class="object"
        ),
        PomClassAttributes(
            the_class="caso",
            name="id",
            colname="id",
            colclass="id",
            coltype="varchar",
            colsize="64",
            colprecision="0",
            pkey="1",
        ),
        PomClassAttributes(
            the_class="caso",
            name="obs",
            colname="obs",
            colclass="obs",
            coltype="varchar",
            colsize="16654",
            colprecision="0",
            pkey="0",
        ),
        PomClassAttributes(
            the_class="caso",
            name="type",
            colname="the_type",
            colclass="the_type",
            coltype="varchar",
            colsize="32",
            colprecision="0",
            pkey="0",
        ),
    ],
}
