"""
Add Latitude/Longitude Coordinates to Kiel Stadtteile

This script adds geospatial coordinates to the stadtteile table in MySQL.
It should be run ONCE after the initial data import to enrich the district data
with approximate center coordinates for each Stadtteil.

NOTE FOR STUDENTS: This script has already been run. You don't need to run it again.
The coordinates are already in the database and the data is ready to use.

Data source: Approximate center coordinates for Kiel's 30 Stadtteile
Based on OpenStreetMap and official Kiel city district boundaries.
"""

import os
import mysql.connector
from mysql.connector import Error as MySQLError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Approximate center coordinates for Kiel's Stadtteile
# These are rough approximations of the district centers
STADTTEIL_COORDINATES = {
    # City center districts
    1: (54.3233, 10.1394),   # Altstadt
    2: (54.3211, 10.1278),   # Vorstadt
    3: (54.3197, 10.1336),   # Exerzierplatz
    4: (54.3169, 10.1189),   # Damperhof
    5: (54.3194, 10.1117),   # Brunswik
    6: (54.3278, 10.1508),   # Düsternbrook
    7: (54.3267, 10.1208),   # Blücherplatz
    8: (54.3428, 10.1347),   # Wik
    9: (54.3244, 10.1006),   # Ravensberg
    10: (54.3278, 10.1094),  # Schreventeich
    11: (54.3147, 10.1119),  # Südfriedhof

    # Eastern districts
    12: (54.3094, 10.1503),  # Gaarden-Ost
    13: (54.2972, 10.1528),  # Gaarden-Süd/Kronsburg
    14: (54.3019, 10.1203),  # Hassee
    15: (54.2892, 10.1247),  # Hasseldieksdamm
    16: (54.2947, 10.1333),  # Ellerbek
    17: (54.3053, 10.1697),  # Wellingdorf

    # Northern districts
    18: (54.3736, 10.1453),  # Holtenau
    19: (54.3631, 10.1336),  # Pries
    20: (54.3847, 10.1708),  # Friedrichsort

    # Western districts
    21: (54.3508, 10.0836),  # Suchsdorf
    22: (54.3431, 10.0722),  # Steenbek-Projensdorf
    23: (54.3178, 10.0672),  # Russee

    # Southwestern districts
    24: (54.2833, 10.1092),  # Mettenhof
    25: (54.2728, 10.0944),  # Dietrichsdorf
    26: (54.2708, 10.1203),  # Oppendorf

    # Outer districts
    27: (54.4050, 10.1525),  # Schilksee
    28: (54.3525, 10.2017),  # Pries-Friedrichsort
    29: (54.3142, 10.0439),  # Hammer (estimated)
    30: (54.3397, 10.0478),  # Neumühlen-Dietrichsdorf (estimated)
}


def connect_to_mysql():
    """
    Connect to MySQL database.

    Returns:
        mysql.connector connection object
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'mysql'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            database=os.getenv('MYSQL_DB', 'kiel_data'),
            user=os.getenv('MYSQL_USER', 'kiel_user'),
            password=os.getenv('MYSQL_PASSWORD', 'kiel_secure_password_2024')
        )
        logger.info("✓ Connected to MySQL")
        return conn
    except MySQLError as e:
        logger.error(f"✗ Failed to connect to MySQL: {e}")
        raise


def update_coordinates(conn):
    """
    Update stadtteile table with latitude and longitude coordinates.

    Args:
        conn: mysql.connector connection object
    """
    logger.info("Updating Stadtteil coordinates...")

    cursor = conn.cursor()

    # Get all stadtteile to see what we have
    cursor.execute("SELECT stadtteil_nr, name FROM stadtteile ORDER BY stadtteil_nr")
    existing_stadtteile = cursor.fetchall()

    logger.info(f"Found {len(existing_stadtteile)} Stadtteile in database")

    updated_count = 0
    missing_count = 0

    for stadtteil_nr, name in existing_stadtteile:
        if stadtteil_nr in STADTTEIL_COORDINATES:
            lat, lng = STADTTEIL_COORDINATES[stadtteil_nr]
            cursor.execute(
                """UPDATE stadtteile
                   SET latitude = %s, longitude = %s
                   WHERE stadtteil_nr = %s""",
                (lat, lng, stadtteil_nr)
            )
            updated_count += 1
            logger.info(f"  ✓ Updated {stadtteil_nr}: {name} ({lat}, {lng})")
        else:
            missing_count += 1
            logger.warning(f"  ⚠ No coordinates found for {stadtteil_nr}: {name}")

    conn.commit()
    cursor.close()

    logger.info(f"✓ Updated {updated_count} Stadtteile with coordinates")
    if missing_count > 0:
        logger.warning(f"⚠ {missing_count} Stadtteile are missing coordinates")


def verify_coordinates(conn):
    """
    Verify that coordinates were added successfully.

    Args:
        conn: mysql.connector connection object
    """
    logger.info("Verifying coordinates...")

    cursor = conn.cursor()

    cursor.execute("""
        SELECT stadtteil_nr, name, latitude, longitude
        FROM stadtteile
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY stadtteil_nr
    """)

    with_coords = cursor.fetchall()
    logger.info(f"✓ {len(with_coords)} Stadtteile have coordinates")

    # Show first 5 as sample
    logger.info("Sample Stadtteile with coordinates:")
    for row in with_coords[:5]:
        logger.info(f"  {row[0]}: {row[1]} → ({row[2]}, {row[3]})")

    # Check for missing
    cursor.execute("""
        SELECT stadtteil_nr, name
        FROM stadtteile
        WHERE latitude IS NULL OR longitude IS NULL
        ORDER BY stadtteil_nr
    """)

    without_coords = cursor.fetchall()
    if without_coords:
        logger.warning(f"⚠ {len(without_coords)} Stadtteile still missing coordinates:")
        for row in without_coords:
            logger.warning(f"  {row[0]}: {row[1]}")

    cursor.close()


def export_to_csv(conn, output_file='stadtteile_with_coordinates.csv'):
    """
    Export stadtteile with coordinates to a CSV file.
    This allows students to use the enriched data if needed.

    Args:
        conn: mysql.connector connection object
        output_file: Path to output CSV file
    """
    import csv

    logger.info(f"Exporting stadtteile to {output_file}...")

    cursor = conn.cursor()
    cursor.execute("""
        SELECT stadtteil_nr, name, latitude, longitude
        FROM stadtteile
        ORDER BY stadtteil_nr
    """)

    rows = cursor.fetchall()

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Stadtteilnummer', 'Stadtteil', 'Latitude', 'Longitude'])
        writer.writerows(rows)

    cursor.close()
    logger.info(f"✓ Exported {len(rows)} Stadtteile to {output_file}")


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("Kiel Stadtteile Coordinate Mapper")
    logger.info("Adding lat/lng coordinates to district data")
    logger.info("=" * 70)
    logger.info("")
    logger.info("NOTE: This script should only be run ONCE to add coordinates.")
    logger.info("If coordinates already exist, they will be updated.")
    logger.info("")

    try:
        # Connect to MySQL
        conn = connect_to_mysql()

        # Update coordinates
        update_coordinates(conn)

        # Verify
        verify_coordinates(conn)

        # Optionally export to CSV
        # Uncomment the line below if you want to export
        # export_to_csv(conn, '/data/stadtteile_with_coordinates.csv')

        # Close connection
        conn.close()

        logger.info("=" * 70)
        logger.info("✓ Coordinate mapping completed successfully!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"✗ Error during coordinate mapping: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
