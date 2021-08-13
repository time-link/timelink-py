An Introduction to Timelink
===========================

Timelink is computer tool specially developed to support micro-historical
research with a strong emphasis on network analysis and prosopography.

Timelink provides a data models and procedures to go from historical
sources to network analysis and convers transcription of sources,
record linking, reconstitution of biographies and network inference.

Timelink is unique in that it bridges a *source-oriented* approach with
a *person-oriented* approach.

This document provides a quick overview of *Timelink*.

.. contents:: Summary
    :depth: 2



The Problem
-----------

Reconstruct individual biographies from diverse sources, mainly for network analysis.

- Few *apriori* choices on who is relevant.
- Focus is on network analysis: relations between people are as important
  as individual attributes.
- Great diversity of sources (anything with personal information can be used).
- Linking references to the same persons in different sources is essential
  (record linking).

Aims
----

Data input close to the original source
+++++++++++++++++++++++++++++++++++++++

- Information about persons should keep the original context.
- Original source structure and sequence of information should be preserved.
- Postpone decisions implying loss of information.

Late and reversible record linking
++++++++++++++++++++++++++++++++++

- Decision on who is who should be made when all available
  information is available.
- Record linking should be reversible.

Flexible interface for complex information
++++++++++++++++++++++++++++++++++++++++++

Find ways to show the complex information of biographies and networks
in a comprehensible way.

Timelink approach
-----------------

- Double approach:
    - A *text-based source-oriented data model* is used to transcribe
      sources with little loss of information.
    - A *person-oriented model*, that consolidates biographical data,
      handles inference of networks and reversible record linking

- The Kleio notation (Manfred Thaller) is used for source-oriented data input.
- A relation database structure is used to store person-oriented data
  together with original source context
- A special software, “the translator” processes text transcriptions
  of the sources and populates the person-oriented database .
- This solves the inevitable tension between a source-oriented model
   and an analytical model.

The Source Oriented Model
-------------------------

Uses a containment structure of source->act->persons and objects

- A historical source contains one or more acts.
- Acts are records of events described in the sources.
- Acts contain actors (persons) and objects (things, properties, institutions)
- Persons and objects appear in acts with specific functions
  (father in a baptism, owner in a sale contract, land object
  of a sale in a contract).
- Actors and objects are described by attributes
  (name, age, gender, price, area).
- Actors and objects are linked by relations. Relations are described
  by a type (kin, economical, professional), and a value
  (brother, lender, apprentice).
- Every act, function, attribute and relation has a date and a link to
  the point in the original source where it appeared.

Example of the Kleio notation
-----------------------------
A baptism::

    baptism$17/9/1685/parish church
    n$manuel/m
        father$jose luis
            atr$residence/casal da corujeira
        mother$domingas jorge
        gfather$francisco rodrigues/id=b1685.9.17.gf
            atr$residence/moinhos do paleao
        gmother$maria pereira
            rel$kin/wife/francisco rodrigues/b1685.9.17.gf





The Person Oriented Model
-------------------------

The `Person Oriented Model` represents a biography through 3 domains:

- Functions (the roles of the person in acts)
- Attributes
- Relations

The `Person Oriented Model` is an alternative view on the information recorded
in the sources, in a way that facilitates estatistical analysis, network analysis
and prosopographhy.

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






