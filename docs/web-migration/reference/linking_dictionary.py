
import json
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import sessionmaker

# This is a placeholder for what would likely be your SQLAlchemy ORM models.
# You should define these based on your actual database schema.
# For this example, we'll use dictionary-like access to query results.

def save_linking_dictionary(db_connection_string: str, export_file: str, for_user: str, mhk_user: str, mhk_admin: str, db_name: str):
    """
    Exports a linking dictionary for a specific user to JSON and CLI files.

    :param db_connection_string: SQLAlchemy connection string for the database.
    :param export_file: The base path for the export files (e.g., 'path/to/export.json').
    :param for_user: The user for whom to export the dictionary.
    :param mhk_user: The current MHK user executing the function.
    :param mhk_admin: The MHK admin user.
    :param db_name: The name of the database.
    :return: The number of real entities exported.
    """
    number_of_real_entities = 0
    json_linking_dictionary = {}
    json_rentities_array = []

    engine = create_engine(db_connection_string)
    Session = sessionmaker(bind=engine)

    cli_export_file = export_file.replace(".json", ".cli")
    os.makedirs(os.path.dirname(export_file), exist_ok=True)

    try:
        with open(export_file, 'w', encoding='utf-8') as json_file, \
             open(cli_export_file, 'w', encoding='utf-8') as cli_file, \
             Session() as session:

            current_time = datetime.now(timezone.utc).isoformat()
            date_str = datetime.now().strftime("%Y%m%d")
            date_human = datetime.now().strftime("%Y-%m-%d")

            # --- Write CLI file header ---
            cli_file.write(f"kleio$gacto2.str/translator=authorities/obs=Generated from database {db_name} "
                           f"by user {mhk_user}, file date: +{date_human} Timestamp:{current_time}\n")
            ident = "   "
            cli_file.write("\n")
            cli_file.write(f"{ident}identifications$real-entities-{for_user}/Real entities, including real persons and real objects\n")
            cli_file.write(f"{ident}{ident}/dbase={db_name}\n")
            cli_file.write(f"{ident}{ident}/user={for_user}\n")
            cli_file.write(f"{ident}{ident}/date={date_str}\n")
            cli_file.write(f"{ident}{ident}/mode=backup\n\n")

            # --- Prepare main JSON object ---
            json_linking_dictionary['date'] = date_str
            json_linking_dictionary['ISO8601'] = current_time
            json_linking_dictionary['dbname'] = db_name
            json_linking_dictionary['user'] = for_user
            json_linking_dictionary['admin'] = mhk_admin

            # --- Build and execute query for real entities ---
            if mhk_user == mhk_admin and mhk_admin == for_user:
                query_str = "SELECT id FROM rentities ORDER BY description, id"
                params = {}
            else:
                query_str = "SELECT id FROM rentities WHERE \"user\" = :for_user ORDER BY description, id"
                params = {"for_user": for_user}

            json_linking_dictionary['query'] = query_str

            all_rentities_result = session.execute(text(query_str), params)

            for rentity_row in all_rentities_result:
                number_of_real_entities += 1
                re_id = rentity_row[0]

                # This part corresponds to DBREntity.getRealEntityBrief in Java.
                # It's assumed that a query can fetch all necessary fields for a real entity.
                # This might require a JOIN across rentities, rpersons, robjects etc.
                # For simplicity, we'll query for a hypothetical 'brief' view or table.
                # You will need to adjust this query.
                re_details_query = text("""
                    SELECT r.id, r.description, r.obs, r.rclass, r.sname, r.status,
                           rp.sex, ro.the_type
                    FROM rentities r
                    LEFT JOIN rpersons rp ON r.id = rp.id
                    LEFT JOIN robjects ro ON r.id = ro.id
                    WHERE r.id = :re_id
                """)
                re_details = session.execute(re_details_query, {"re_id": re_id}).mappings().first()

                if not re_details:
                    print(f"Could not find details for real entity: {re_id}")
                    continue

                # --- Write to CLI file ---
                rclass = re_details.get('rclass', '')
                cli_file.write(f"{ident}{ident}{rclass}${re_id}")
                cli_file.write(f"/{re_details.get('sname', '')}")
                if rclass == "rperson":
                    cli_file.write(f"/{re_details.get('sex', '')}")
                elif rclass == "robject":
                    cli_file.write(f"/{re_details.get('the_type', '')}")

                status = re_details.get('status', '')
                if status and status.strip():
                    cli_file.write(f"/status={status}")

                obs = re_details.get('obs', '')
                if obs and obs.strip():
                    cli_file.write(f"/obs={obs}")
                cli_file.write("\n")

                # --- Build JSON for the real entity ---
                json_real_entity = dict(re_details) # Convert Row to dict

                # --- Fetch and process links ---
                links_query = text("""
                    SELECT l.rid, l.instance, l.rule, e.class
                    FROM links l
                    LEFT OUTER JOIN entities e ON l.instance = e.id
                    WHERE l.rid = :re_id
                    ORDER BY l.instance
                """)
                links_result = session.execute(links_query, {"re_id": re_id}).mappings()

                json_link_array = []
                for link_row in links_result:
                    link_json = {
                        "instance": link_row['instance'],
                        "rule": link_row['rule']
                    }
                    missing_occ_note = ""
                    if link_row['class'] is None:
                        missing_occ_note = "WARNING: Occurrence missing"
                        link_json['obs'] = missing_occ_note

                    json_link_array.append(link_json)
                    cli_file.write(f"{ident}{ident}{ident}occ${link_row['instance']}"
                                   f"{'/obs=' + missing_occ_note if missing_occ_note else ''}\n")

                json_real_entity['links'] = json_link_array
                json_rentities_array.append(json_real_entity)
                cli_file.write("\n")

            json_linking_dictionary['real_entities'] = json_rentities_array
            json_linking_dictionary['size'] = len(json_rentities_array)

            json.dump(json_linking_dictionary, json_file, indent=4)

    except Exception as e:
        print(f"An error occurred: {e}")
        # In a real app, you'd use a proper logger
        # import logging
        # logging.error("An error occurred", exc_info=True)
        raise

    return number_of_real_entities

if __name__ == '__main__':
    # Example usage:
    # You need to replace these with your actual database details and parameters.
    # Assumes a PostgreSQL database, but you can change the connection string.
    DB_CONN_STR = "postgresql://user:password@localhost/mhk_db"
    EXPORT_FILE = "linking_dictionary_export.json"
    FOR_USER = "testuser"
    MHK_USER = "admin"
    MHK_ADMIN = "admin"
    DB_NAME = "mhk_db"

    print("Starting linking dictionary export...")
    try:
        count = save_linking_dictionary(DB_CONN_STR, EXPORT_FILE, FOR_USER, MHK_USER, MHK_ADMIN, DB_NAME)
        print(f"Successfully exported {count} real entities.")
        print(f"JSON file: {EXPORT_FILE}")
        print(f"CLI file: {EXPORT_FILE.replace('.json', '.cli')}")
    except Exception as e:
        print(f"Export failed: {e}")

