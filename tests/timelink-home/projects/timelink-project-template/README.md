# Timelink project home

This is the home of a **Timelink project**: Kleio source files associated with
a database, used as `timelink-home` in single-user, single-project mode.

The `.timelink-project` marker file in the root identifies the directory as a
Timelink project directory. The same directory can also live inside the
`projects/` directory of a multi-project home and be used as part of it.

## Directory layout

```
├── database
│   ├── backups        backups of the project database
│   └── sqlite         SQLite database files
├── etc
│   └── doc            pointers to the ongoing documentation
├── extras             auxiliary project files: working documents, scripts,
│                      downloaded material and derived data
├── identifications    exports of the identification (record linking) process
├── inferences         inference rules used when processing the source files
├── mappings           mappings between Kleio groups and database tables
├── notebooks          Jupyter notebooks for working with the project data
├── sources            source files in Kleio notation (.cli, .kleio)
├── structures         structure files describing the internal structure of each
│                      type of source
└── .timelink-project  marker file: identifies this directory as a Timelink project
```

See the [Timelink documentation](https://time-link.github.io/timelink-docs/) for details.

## What is Timelink?

Timelink, formerly known as MHK (Micro History with Kleio) is an information system designed for processing person related information collected from historical sources.

Timelink provides:

* a notation (kleio) for textual transcription of historical sources, capable of capturing complex information about people and their relations in any type of historical documents.
* a text processor that extracts information from the kleio transcriptions, infers personal attributes and relations from agent roles in historical events and generates data in formats suitable for database import.
* a database management system capable of processing time varying attributes and relations, assist in reconstructing biographies and networks from fragmentary information.

Timelink is open source MIT License software available at http://github.com/joaquimrcarvalho/timelink

## Source collections included in this project

* **Describe this project collections here**

## License

Timelink software is distributed under a MIT license that includes usage for commercial purposes.

Kleio transcriptions of historical sources are not distributed under the same license.

Each Kleio transcription file is copyright of the person or persons that produced the transcription.
