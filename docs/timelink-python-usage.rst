Timelink Python Package
=======================

The Timelink Python package provides a Python interface to the 
Timelink system. It is intended to be used by clients such as
Jupyter notebooks to access the Timelink database and process 
Kleio source files.

Installation
------------

The Timelink Python package is available on PyPI and can be installed
using pip:

.. code:: bash

    pip install timelink

Interfacing with a Kleio Server
-------------------------------
A Kleio server is a separate application
that processes source files in the Kleio
notation and produces data that can be
imported into the Timelink database.

The Timelink Python package provides 
a :class:`timelink.kleio.kleio_server.KleioServer` class 
that can be used to interface with a Kleio server.

For more information on the Kleio notation,
and how it is used to produce data for the
Timelink database, see 
:doc:`/som_pom_mapping`

Starting a Kleio Server
~~~~~~~~~~~~~~~~~~~~~~~

To start a Kleio server, in the local
machine, ensure that you have `Docker installed <https://docs.docker.com/engine/install/>`_
in the local machine.

.. code-block:: python

    from timelink.kleio import KleioServer

    # Start a Kleio server using Docker
    # in the current directory

    kleio_home="."
    kserver: KleioServer = KleioServer.start(kleio_home=kleio_home)

The latest image from the Kleio Docker repository will be 
used to start the server. If the image is not available locally,
it will be downloaded from the Docker repository. So the
first run may take some time.

It is possible to specify other Docker related parameters,
see :meth:`timelink.kleio.kleio_server.start_kleio_server`

Getting status of Kleio files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Kleio server can be queried for the status of Kleio files
using the :meth:`timelink.kleio.kleio_server.KleioServer.translation_status` method.

.. code:: python

    from typing import List
    from timelink.kleio import KleioServer
    from timelink.kleio.schemas import KleioFile

    kfiles: List[KleioFile] = kserver.translation_status(path='',recurse='yes',status=None)

    for kfile in kfiles:
        print(kfile.status.value,kfile.path,kfile.modified_string, kfile.translated_string)

 >>>

    E reference_sources/varia/nommiz.cli 2023-10-17 12:22:49 2023-10-21T05:35:00+00:00
    T reference_sources/linked_data/dehergne-locations-1644.cli 2023-11-03 11:51:18 2023-11-03T04:30:00+00:00
    V reference_sources/linked_data/dehergne-a.cli 2023-10-24 12:56:44 2023-10-24T12:56:00+00:00
    W reference_sources/varia/EmpFAfonso.cli 2023-10-21 05:34:30 2023-10-21T05:34:00+00:00

The status of a Kleio file are defined in an enumeration: 
:class: `timelink.kleio.schemas.KleioFileStatus`

* T - Translation needed
* E - Translated with errors
* W - Translated with warnings
* V - Valid translation (can be imported)

