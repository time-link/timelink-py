# Timelink web interface

## Purpose

- create a web interface to the Python implementation of Timelink. This web interface complements the current interface using Jupyter Notebooks and will replace the old Tomcat/Velocity/Java implementation currently available.

## Requirements

- Python centric, no Javascript front end or JS frameword like (React, Vue,...).
- Included in timelink-py package https://github.com/time-link/timelink-py adds backend functions to
	timelink-py as needed.
-  Timelink data structures should be easy to represent in the frontend (Pandas DataFrame, Maps, templates in Markdown for arbitrary information)
- Possible frameworks (evaluate with basic show case app) :
	- [[Reflex]] https://reflex.dev
	- NiceGUI https://nicegui.io
	- Posit https://posit.co
	- Shiny https://shiny.posit.co
	- Htmx https://htmx.org
- Background tasks like import data to database, update stats, entity resolution) that can be triggered in the web interface but will take long to execute.
- Templates for generating markdown, html, pdf, rtf views of entities
	- Timelink deals with complex entities, mainly people, with time varying attributes, relations with other entities and personal histories of occurrences in events. A data model exists to represent these entities. A way to generate representations in different formats for display, download, print is needed. https://timelink-py.readthedocs.io/en/v1.1.1/_modules/timelink/api/schemas.html#EntityAttrRelSchema
- Deployment
	- Lightweight mode, single user, uses sample project directory.
	- Services scenario, with installation serving different users and different projects
		- User management
    		- Needs an interface to register users and permissions. See https://github.com/aminalaee/sqladmin
			- concept of project: a combination of a historical source repository and database. Repository access is done through Kleio Server credentials (token and URL) and optionally git repository credentials. Database access through db specific credentials (SQL Alchemy urls).
			- Levels of users:
				- read only
				- read only plus "interpretations" (entity resolution, saved lists of entities)
				- database and source change
				- manage users
			- Authentication of users: use open method, work with github, google, Facebook.
			- Manage user
			- Anonymous user with read only access in specific projects
		- URI resolution of entities
			- Capability to process an URL that corresponds to a unique entity and return information in json format or others, e.g. http://timelink.uc.pt/my-project/entity/entity-id
		- Simple hosting scenarios for mainstream providers (Amazon, Google, Linode).
-

# Interface

Reference implementation MHK in Java at timelink.uc.pt
## Main menu

### Left side navigation bar

- **Overview**
- **People**, Groups and Networks
- **Families**, Genealogies and Demography
- **Calendar**
- **Linking**, Entity Resolution and Linked Data
- **Sources**
- **Search**
- **Admin**

### Overview

Gives an overview of the database and recent activity
- Entitity counts for the database
- Recent activity:
	- recent sources (translated note error) recent imports (note errors)
	- recently vued: acts, persons.
	- important: acts, persons (ids that occur a lot in recent activity)
	- recent searches:

To support this we need a logging mechanism.
`table activity (`
`when date,`
`entity_id varchar(64), // id of the entity affected`
`entity_type varchar(32), {person,rperson,....}`
`activity_type varchar(32), {view, insert, delete,----}`
`desc varchar(255)) // human readable description of the event`

### People, Groups, Networks

#### People

- people with attribute
	- Exists a timelink.pandas function entity_with_attributes
- people with relations
- full text search
- in all the searches above there is an option to save as smart group

#### Group

- refresh groups (makes smart grous to be recalculated
- manage group. rename, new, add entity, remove entity, delete group.
- For smart group edit query string, rename, delete, show collective biography (like rperson information but with the group's occurences in chronological order (chronological list of acts with group members in bold)
- For normal group add, remove, rename, delete, show collective biograpy (timelink.pandas.group_attributes exists), set operations (union, intersection, diference) make network from a group (calculates all the relations linking the members of a group)

#### Networks

- Define a network
- by using rels
	- network_from_rels(filter=listOfType, listOfTuples (type,value), only_confirmed_rentities)
- by using co-occurence in acts:
	- [funcA, funcB, reltype, relvalue]
	- [funcB,funcA, reltype, relvalue]-> implies a link of rel_type,rel_value
	- network_from_functions(origin=funcA, dest=funcB, actType=type,infer=(reltype,relvalue), reverse=(ireltype,irelvalue), real_only)
		- if X has funcA in act of type T
		- and Y has funcB in same act
		- then infer
			- rel origin=X,dest=Y, type=relType, value=relValue, date=Act.date
			- rel origin=Y, dest=X, type=irelType, value=irelValue, date=Act.date
- by common attributes
	- existing funcion needs refactoring net_from_attribute
- first order star
- second order star
- always with option to save as group

### Families, Genealogies and Demography

#### Families

ver [[Timelink Processamento de famílias]]
- Search for couples
- View/manage families
- Redo family records from record linking
- Review family records
- List/search complete families
- List/search all families

#### Genealogies
- Descendents
- Ascendents

#### Demography
- Analysis of demographic information
	- mean age at marriage
	- mean age at first child
	- intergenesial intervals
	- Natality, Nuptiality and mortality.

### Calendar

- moving festivities: Easter, Lent.
- Use dates on attributes and relations, not only events and acts
- Cronologies
- Make separators for act type
- bap, cas, o, devassas

### Entity Resolution

#### Automation
- Pre-processing of attributes
- start pre-processing of attributes and values
- normalize values
- Special attribute handling (names, location, equivalent attributes, etc...)
- Manage linking queue
#### Review ER
- Review validate identifications -> this could be the same as collective identifcation with the algoritm as a special user "@auto@"
- Record linking statistics

### Sources

- This was reimplemented in the MHK2019 interface and the VS Code Extension, and the new interface will keep the same functionality. See Detail: Sources page.

### Search

- Search the index with help on the syntax
- SQL search with assistance similar to myPHPAdmin
- Save searches (both SQL and Index, and those triggered by hyperlinks)
- When viewing results that have and id field activate option to "save as a group"
- Search packages: a directory combining form, sql, listing, and description files

### Admin

- Parameters and configuration
- create remove users
- Backup and restore
- Background tasks.



**DETAILS**

**Branding (added** 2020-09-25 sexta-feira 14:36)

- The global layout of the interface should allow for some "branding" of different installations of the software, for instance, a custom logo, a custom message, a base color in the header, so that a user that visits different install get a visual clue of where it is. Some services use simple "themes" to provide such a functionality.

**Sources page:**

Input: result of translation_get calls to Kleio Server.

- keep the layout and structure of the MHK2019 / VS Code extension: main view shows only the cli files and their current status. On the side bar the list of with Errors, Warnings, Import Errors, In translation, In importing.

**Real Person view and Real Person Preview**

Input: 
- result of call getRealEntity(Id) return format to be defined

- The present main view shows occurrences chronologically with column: date, function, atributes (on that occurrence), relations (on that occurence), name. This is to be kept.
- Future View:
	- a Atribute summary before the above list; for each type of attribute, and for each value, show in a line the date of the first occurence and the last


		profissao/padre:   1706-1735
		residencia/areias  1706-1735
		residencia/casal das areias: 1707-1720


	- in the preview it would be nice if each of the attribute/value combination had a button for selecting, deselecting the respective occurrences (this is in the *Explore* view)

	- Change name, obs, rid and status: users should be able to change the rid of the real persons and also the value of the "status" character. This status was intended to distinguish automatically generated real entities from entities validated by users, which would have status "V". Currently no specific behaviour is implemented. In the future when the user changes the status for V and two real entities are merged during the identification process then the rid with status V is kept for the new real entity. If both real entities have V as status an error is generated and the user is asked to decide which id is kept. Users should also have an interface for changing the name of the Real Entity and the obs field.
		- Requires api call setRealEntity(oldId, status, sname, obs).
		- Copy URL: this would copy the url of the real entity to the clipboard. The URL should be in the short format allowed by the rewrite rules implemented by João Carvalho, [http://timelinkurl/base/id](http://timelinkurl/base/id) (?)
- Tab "Related Persons"
	- hability to generate link for all the people in the same "name section", with preview and without reloading the page. It should be possible to link "related people" quickly, by pressing a button in front of each name.