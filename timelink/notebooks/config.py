# Configuration values related to notebooks-timelink integration

# Connection string for Timelink database
TIMELINK_CONNSTRING = None

# Object representing the Timelink Database connected to these notebooks
TIMELINK_DBSYSTEM = None

# SQLAlchemy session for Timelink database
TIMELINK_SESSION = None

# Table for fetching people and attributes
#     CREATE VIEW nattributes AS
#      SELECT
#        p.id,
#        p.name,
#        p.sex,
#        a.the_type,
#        a.the_value,
#        a.the_date,
#        p.obs AS pobs,
#        a.obs AS aobs
#      FROM attributes a, persons p
#      WHERE a.entity = p.id;
#
# This is dynamically set by functions and kept here to avoid duplication
TIMELINK_NATTRIBUTES = None

# This is the attribute table
TIMELINK_ATTRIBUTES = None

# This is the persons table
TIMELINK_PERSONS = None

# This is the relations table
TIMELINK_RELATIONS = None

# This is the named functions view
TIMELINK_NFUNCS = None
