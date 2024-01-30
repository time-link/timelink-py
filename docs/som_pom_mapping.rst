Timelink data concepts and models
=================================

.. contents:: Summary
    :depth: 2

Timelink uses a dual model to represent historical information.

- A *text-based source-oriented data model* is used to transcribe
  sources with little loss of information.
- A *person-oriented model*, that consolidates biographical data,
  handles inference of networks and reversible record linking

The ``Kleio`` notation (Manfred Thaller) is used for source-oriented
data input.

A relational database structure is used to store person-oriented data
together with original source context.

A special software, *the Kleio translator* processes text transcriptions
of the sources in ``kleio`` notation and generates data for the
the person-oriented database.

This solves the inevitable tension between a source-oriented model
and an analytical model.

The Source Oriented Model
-------------------------

Uses a containment structure of ``source->act->persons`` and ``objects``.

The *source oriented model* uses a number of key terms in a formal way:
``source``, ``act``, ``person``, ``object``, ``function``, ``attribute``
and ``relation``.


- A historical ``source`` contains one or more ``acts``.
- An ``act`` is a records of events described in the sources
  (a baptism, a marriage, a sale contact, a rental contract, ...)
- An ``act`` contains actors (``persons``) and ``objects``
  (things, properties, institutions, ...).
- ``persons`` and ``objects`` appear in ``acts`` with specific ``functions``
  (father in a baptism, owner in a sale contract, house in a rental contract).
- ``Actors`` and ``objects`` are described by ``attributes``
  (name, age, gender, price, area, ...).
- ``Actors`` and ``objects`` are linked by ``relations``. Relations are described
  by a type (kin, economical, professional), and a value
  (brother, lender, apprentice).
- Every ``act``, ``function``, ``attribute`` and ``relation`` has a date
  and a link to the point in the original source where it appeared.

Example of the Kleio notation
-----------------------------
A baptism::

    baptism$17/9/1685/parish church
        n$manuel/m
            father$jose luis
                attr$residence/casal da corujeira
            mother$domingas jorge
            gfather$francisco rodrigues/id=b1685.9.17.gf
                attr$residence/moinhos do paleao
            gmother$maria pereira
                rel$kin/wife/francisco rodrigues/b1685.9.17.gf

This example shows an ``act`` (a baptism) that contains five ``persons``:
child ("n"), father, mother, god father and god mother. Two of the people,
the father and the god father have the ``atribute`` *residence*, and the god
mother has a *kin* ``relation`` with the god father.


The Person Oriented Model
-------------------------

The `Person Oriented Model` represents a biography through 3 domains:

- Functions (the roles of the person in acts)
- Attributes
- Relations

The `Person Oriented Model` is an alternative view on the information recorded
in the sources, in a way that facilitates statistical analysis, network analysis
and prosopographies.

The previous baptism generates information as follows (*italics* show
information inferred by Timelink).


Entities
++++++++

+----------------+-------------+------------------+
| Id             | Class       | Inside           |
+================+=============+==================+
| bapt1685-1700  | source      |       ---        |
+----------------+-------------+------------------+
| *b1*           | act         | bapt1685-1700    |
+----------------+-------------+------------------+
| *b1-per1*      | person      | *b1*             |
+----------------+-------------+------------------+
| b1685.9.17.gf  |  person     | *b1*             |
+----------------+-------------+------------------+
| *b1-per2*      |  person     | *b1*             |
+----------------+-------------+------------------+
| *b1-per3*      |  person     | *b1*             |
+----------------+-------------+------------------+

Note that each *entity* has an unique
identifier: ``id``. Such identifier is necessary to refer unambiguosly
to a ``person``, ``object``, ``act`` or ``source``.

Most ``ids`` are generated
automatically by the *Kleio translator* when processing the source transcripts.
but in some circunstances they need to be explicitly given, when a link
between two entities needs to be recorded in an non ambiguous way, such as
the relation between godmother and godfather in the example above.

Persons
+++++++

+----------------+---------------------+--------+
| Id             | Nome                | Gender |
+================+=====================+========+
| *b1-per1*      | manuel              | f      |
+----------------+---------------------+--------+
| *b1-per2*      | jose luis           | *m*    |
+----------------+---------------------+--------+
| *b1-per3*      | domingas jorge      | *f*    |
+----------------+---------------------+--------+
| b1985.9.17.gf	 | francisco rodrigues | *m*    |
+----------------+---------------------+--------+
| *b1.per5*      | maria pereira       | *f*    |
+----------------+---------------------+--------+

Attributes
++++++++++

+-----------------+------------+--------------------+-------------+
| Entity          |  Type      | Value              | Date        |
+=================+============+====================+=============+
| *b1-per1i*      | residence  | Casal da Corujeira | *17/9/1685* |
+-----------------+------------+--------------------+-------------+
| *b1985.9.17.gf* | residence  | Moinhos do Paleao  | *17/9/1685* |
+-----------------+------------+--------------------+-------------+

Relations
+++++++++
+------------+---------------+---------+-----------+----------------+
| Origin     | Destination   | Type    |  Value    |  Date          |
+============+===============+=========+===========+================+
| *b1-per2*  | *b1.per3*     | *kin*   | *husband* | *17/9/1685*    |
+------------+---------------+---------+-----------+----------------+
| *b1-per5*  | b1985.9.17.gf | kin     | wife      | *17/9/1685*    |
+------------+---------------+---------+-----------+----------------+
| *b1-per2*  | *b1-per1*     | *kin*   | *father*  | *17/9/1685*    |
+------------+---------------+---------+-----------+----------------+

Functions
+++++++++

Functions of people (father,mother, ...) in acts are a special case
of relations linking people to acts, with the type 'function-in-act'.
The same applies to objects, when they appear in acts.

+---------------+---------------+------------------+-----------+----------------+
| Origin        | Destination   | Type             |  Value    |  Date          |
+===============+===============+==================+===========+================+
| b1985.9.17.gf | *b1*          | function-in-act  | gfather   | *17/9/1685*    |
+---------------+---------------+------------------+-----------+----------------+
| *b1.per5*     | *b1*          | function-in-act  | gmother   | *17/9/1685*    |
+---------------+---------------+------------------+-----------+----------------+



How translation between SOM and POM works
-----------------------------------------

Timelink contains a set of basic entities: *sources*, *acts*, *persons*,
*objects*, *attributes* and *relations*. For an example such as the previous
one to work, Timelink needs to know the correspondence between the Kleio
notation and the relational database tables, as well as how to infer values
like gender and kin relations.

Terminology note
++++++++++++++++

When describing both the Source Oriented Model and the Person Oriented Model
different terms are used to describe concepts that are similar.

In both the Source Oriented Model (SOM) and the Person Oriented Model (POM), 
we have concepts for entities that existed, such as *sources*, *transcriptions of acts*, *people*, and *objects*. 

These entities have *attributes* that provide information about them, such as names, dates, and archival locations. 

Additionally, both models include the concept of *relations*, which describe the connections between entities. For example, in the relations, we can specify that person X is the father of person Y or that person Z bought property W.

But each model uses different terms for refer to the same things. For
instance in the Kleio notation "groups" are used to record entities, and
"elements" to record their attributes.

In the context of a database, entities such as *persons*, *objects*, *acts*, and *sources* are represented as rows in different database tables. Each table column corresponds to an attribute of the entities of the same type, storing information such as names, dates, and other relevant data.

At a higher level, when describing the structure of information, we will
use the terminology defined by the `Entity-Relationship-Model
<https://en.wikipedia.org/wiki/Entity–relationship_model>`_ (ER Model)

* Entity: something that existed in the real world:
    sources, acts, people, also "abstractions" like institutions and
    events like baptisms or marriages.
* Relation: relations between entities
    like kinship relations between
    people, ownership relations between people and properties, roles
    of people participating in acts
* Attribute: items of information that describe entities and relations
    (names, dates, kinship terms, prices of transactions)
* Entity-class or entity-type: a category of Entities described by the same attributes
    `person` is a entity class, `building` is
    another entity class and so is `acts`; each is described by different attributes.
* Entity instance: a specific entity of a specific class
    (the person named Galileo Galillei, the building named 'Tower of Pisa',
    the baptism that occurred in 8/7/1685 in the church of Soure, Portugal ).

We refer to the concepts above to introduce the terminology specific
to the SOM and POM models.

For the SOM the main terms are Group,Element and Aspect used by Manfred Thaller
in the Kleio notation.

- Group: corresponds to *entities*.

- Element: corresponds to *attributes*.
- Aspect: represent extra information about attributes.
    The Kleio notation allows to register not only the core value of an
    attribute but also a comment and the original wording in the document.


In Timelink Kleio groups are used also to record attributes of entities
that vary with time, like residence or profession. 

These attributes have
not just a value ("Abbey Road", "Musician") but also have associated a
date. So they have their own attributes (dates for one), like entities.
In the ER Model this type of information is called a "weak entity": they
have their own attributes like entities, but they do not correspond to
something that exists on its own in the real world, they depend on a main
entity.

In the SOM model Kleio groups are also used to record relations.

In the POM we use the terminology of databases: tables and columns.

- Table: corresponds to entities
- Columns: corresponds to attributes

In the Person Oriented Model tables are also used to represent relationships
between entities and time varying attributes.

Mapping Kleio Groups to Database tables
+++++++++++++++++++++++++++++++++++++++

The correspondence between a ER Model description and the tables and columns
of a database is well defined. For a given information model described in terms
of ER Model  a set of tables and columns in a relational
database can be produced deterministically (see the reference above for details
and further references).

The correspondence between the Kleio Groups, Elements and Aspects
and tables and columns in a relational database is defined by conventions and
configuration files in Timelink.

Basic correspondence is provided by Timelink for basic entity types
like sources, acts, people, objects. This allows Timelink to process generic
Kleio transcriptions into generic tables as demonstrated in the example of
the baptism above.

In most cases a transcription closer to the source is desired, either because
of readability (we rather read baptism$ than act$ and father$ than person$)
or because the source describes entities with specific attributes (for instance
a land property being sold is an `object` which has special attributes such as
area and a typology like rural/urban).

To be able to use Kleio to record in a format closer to the source we need
to provide Timelink the following information:

- the name of the groups to be used and their relation with the core groups
    - e.g. `father` and `mother` instead of `person` or `land` instead of
      `object`
- the extra elements, if any, that the groups will include
- if extra elements are introduced how they will be stored in database tables
- if there is information to be inferred from the transcription (attributes or relations), what are the rules to be used for inference
    - e.g. the element `sex` can be inferred if groups such as `father`
      and `mother` are used instead of `person`

Currently three types of configuration files are used to provide this information:

str files
    define new groups and their relation with core groups, as well
    as extra elements that the new groups might include

mappings files
    describe how information of the new groups and elements are
    stored in the database tables

inference files
    contain rules for inference of attributes and relations
    from the groups in the transcriptions


Here we describe the content of a mapping file.

Here is an example of a mapping, in the current notation::

    mapping person to class person.
    class person super entity table persons
       with attributes
            id column id baseclass id coltype varchar colsize 64 colprecision 0 pkey 1
         and
            name column name baseclass name coltype varchar colsize 128 colprecision 0 pkey 0
         and
            sex column sex baseclass sex coltype char colsize 1 colprecision 0 pkey 0
         and
            obs column obs baseclass obs coltype varchar colsize 16654 colprecision 0 pkey 0 .

The statement::

    mapping person to class person

means that the Kleio group `person` will be stored in the database as an
entity of class `person`.

The statement::

    class person super entity table persons

means that database entity class `person` is a specialization of `entity`,
and is stored in a table named `persons`.

The subsequent lines after `with attributes` specify the mapping between the
database entity attributes, store as columns in tables and group elements.


For each attribute the following is specified:

- id : name of the attribute in the database entity class
- column id: name of the column in the database for this element
- baseclass id: the kleio reference class for this attribute
- coltype, colsize, colprecision: information used to create the column in the database
  precision only applies if coltype is "DECIMAL"
- pkey: integer,if this attribute is part of the primary key of the table, this is the order

The `baseclass` refers to certain attribute names that have special meaning.

For instance,day,month,year,id,obs, same_as are names of elements that have special
meaning in the translation of sources and mapping of data into the database.

In the mapping for portuguese act called "acta" (minutes, or
transcript, normally of a meeting):

.. code-block::

    part name=historical-act;
         guaranteed=id,type,date;
         position=id,type,date;
         also=loc,ref,obs,day,month,year;
         arbitrary=person,object,geoentity,abstraction,ls,atr,rel

    element name=day; type=number
    element name=month; type=number
    element name=year; type=number
    element name=date;type=number

    part name=pt-acto; source=historical-act;
         arbitrary=celebrante,actorm,
             actorf,object,abstraction,ls,rel;
         position=id,dia,mes,ano;
         guaranteed=id,dia,mes,ano;
         also=ref,loc,obs

    element name=dia; source=day
    element name=mes; source=month
    element name=ano; source=year
    element name=data; source=date

    part name=amz;
     source=pt-acto;
     repeat=eleito,eleitor,referido;
     guaranteed=id,dia,mes,ano,fol;
     position=id,dia,mes,ano,fol;
     also=resumo,obs


    mapping 'historical-act' to class act.
    class act super entity table acts
       with attributes
            id column id baseclass id coltype varchar colsize 64 colprecision 0 pkey 1
         and
            date column the_date baseclass date coltype varchar colsize 24 colprecision 0 pkey 0
         and
            type column the_type baseclass type coltype varchar colsize 32 colprecision 0 pkey 0
         and
            loc column loc baseclass loc coltype varchar colsize 64 colprecision 0 pkey 0
         and
            ref column ref baseclass ref coltype varchar colsize 64 colprecision 0 pkey 0
         and
            obs column obs baseclass obs coltype varchar colsize 16654 colprecision 0 pkey 0 .


     mapping amz to class acta.
     class acta super act table actas
        with attributes
            id column id baseclass id coltype varchar colsize 64 colprecision 0 pkey 1
         and
            dia column the_day baseclass day coltype numeric colsize 2 colprecision 0 pkey 0
         and
            mes column the_month baseclass month coltype numeric colsize 2 colprecision 0 pkey 0
         and
            ano column the_year baseclass year coltype numeric colsize 4 colprecision 0 pkey 0
         and
            fol column fol baseclass fol coltype varchar colsize 64 colprecision 0 pkey 0
         and
            resumo column resumo baseclass resumo coltype varchar colsize 1024 colprecision 0 pkey 0
         and
            obs column obs baseclass obs coltype varchar colsize 16654 colprecision 0 pkey 0 .

..

The attributes names in Portuguese (dia,mes,ano) are mapped to standard
classes (day,month,year) and conform column names
that do not conflict with reserved words in database systems
(the_day, the_month, the_year).

.. code-block::

    amz$amz1/3/10/1683/fol=2
        /resumo=nomeacao de capelao que se fez na casa desta
                vila de soure por morte do padre simao homem de oliveira


This is the way the above transcription is exported by the translator

::

    <GROUP ID="amz1" NAME="amz" CLASS="acta" ORDER="2" LEVEL="2" LINE="6">
        <ELEMENT NAME="line" CLASS="line"><core>6</core></ELEMENT>
        <ELEMENT NAME="id" CLASS="id"><core>amz1</core></ELEMENT>
        <ELEMENT NAME="groupname" CLASS="groupname"><core>amz</core></ELEMENT>
        <ELEMENT NAME="inside" CLASS="inside"><core>mis-mesa-1</core></ELEMENT>
        <ELEMENT NAME="class" CLASS="class"><core>acta</core></ELEMENT>
        <ELEMENT NAME="order" CLASS="order"><core>2</core></ELEMENT>
        <ELEMENT NAME="level" CLASS="level"><core>2</core></ELEMENT>
        <ELEMENT NAME="dia" CLASS="day">
        <core><![CDATA[3]]></core>   </ELEMENT>
        <ELEMENT NAME="mes" CLASS="month">
        <core><![CDATA[10]]></core>   </ELEMENT>
        <ELEMENT NAME="ano" CLASS="year">
        <core><![CDATA[1683]]></core>   </ELEMENT>
        <ELEMENT NAME="fol" CLASS="fol">
        <core><![CDATA[2]]></core>   </ELEMENT>
        <ELEMENT NAME="resumo" CLASS="resumo">
        <core><![CDATA[nomeacao de capelao que se fez na casa desta vila de soure por morte do padre simao homem de oliveira]]></core>
        </ELEMENT>
        <ELEMENT NAME="date" CLASS="date">
        <core><![CDATA[16831003]]></core>   </ELEMENT>
        <ELEMENT NAME="type" CLASS="type">
        <core><![CDATA[amz]]></core>   </ELEMENT>
    </GROUP>

Note that the elements of the group are exported in XML with class derived
from the elements source parameter:

::

    element name=dia; source=day
    element name=mes; source=month
    element name=ano; source=year

Which generates the `CLASS` attribute in XML

::

       <ELEMENT NAME="dia" CLASS="day">
             <core><![CDATA[3]]></core>   </ELEMENT>
       <ELEMENT NAME="mes" CLASS="month">
             <core><![CDATA[10]]></core>   </ELEMENT>
       <ELEMENT NAME="ano" CLASS="year">

During import Timelink will determine the mapping information to be used
for the incoming Kleio group, from the group XML information:

::

    <GROUP ID="amz1" NAME="amz" CLASS="acta" ORDER="2" LEVEL="2" LINE="6">


It will then go through each of the attributes of database class `acta`
and fetch the group element with CLASS equal to the attribute baseclass. The
value of the element is used to set the corresponding column in the table
`actas`.

Note that the mapping allows for the usage of a Kleio group with a evocative
name "amz" while using a more generic table name `actas`.


