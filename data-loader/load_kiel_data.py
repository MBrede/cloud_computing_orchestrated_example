"""
MySQL Data Loader for Kiel City Open Data

This script demonstrates:
1. Database connection with mysql-connector-python
2. Table creation with SQL DDL
3. CSV data import and processing
4. Error handling and retries
5. Connection lifecycle management

Data source: Kiel Open Data Portal
https://www.kiel.de/de/kiel_zukunft/statistik_kieler_zahlen/open_data/index.php

The script imports population and demographic data for Kiel's Stadtteile (districts).
"""

import os
import time
import csv
import mysql.connector
from mysql.connector import Error as MySQLError
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_mysql(max_retries=30):
    """
    Wait for MySQL to be ready.

    Args:
        max_retries: Maximum number of connection attempts

    Returns:
        mysql.connector connection object
    """
    logger.info("Waiting for MySQL to be ready...")

    for attempt in range(max_retries):
        try:
            conn = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'mysql'),
                port=int(os.getenv('MYSQL_PORT', '3306')),
                database=os.getenv('MYSQL_DB', 'kiel_data'),
                user=os.getenv('MYSQL_USER', 'kiel_user'),
                password=os.getenv('MYSQL_PASSWORD', 'kiel_secure_password_2024')
            )
            logger.info(">> MySQL is ready!")
            return conn
        except MySQLError as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: MySQL not ready yet... ({e})")
            time.sleep(2)

    raise Exception("MySQL did not become ready in time")


def create_tables(conn):
    """
    Create database tables for Kiel open data.

    Creates tables for:
    - stadtteile: Districts with optional lat/lng coordinates
    - population_by_gender: Population counts by gender
    - population_by_age: Population counts by age groups
    - population_by_religion: Population by religious affiliation
    - population_by_family_status: Population by marital status
    - foreigners_by_nationality: Foreign residents by nationality
    - households: Household statistics

    Args:
        conn: mysql.connector connection object
    """
    logger.info("Creating database tables...")

    cursor = conn.cursor()

    # Drop tables if they exist
    tables_to_drop = [
        'population_by_gender',
        'population_by_age',
        'population_by_religion',
        'population_by_family_status',
        'foreigners_by_nationality',
        'households',
        'stadtteile'
    ]

    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # Create stadtteile (districts) table
    cursor.execute("""
        CREATE TABLE stadtteile (
            stadtteil_nr INT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            latitude DOUBLE,
            longitude DOUBLE,
            UNIQUE KEY uk_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Create population by gender table
    cursor.execute("""
        CREATE TABLE population_by_gender (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stadtteil_nr INT NOT NULL,
            datum DATE NOT NULL,
            total INT NOT NULL,
            male INT NOT NULL,
            female INT NOT NULL,
            FOREIGN KEY (stadtteil_nr) REFERENCES stadtteile(stadtteil_nr),
            UNIQUE KEY uk_stadtteil_date (stadtteil_nr, datum)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Create population by age groups table
    cursor.execute("""
        CREATE TABLE population_by_age (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stadtteil_nr INT NOT NULL,
            datum DATE NOT NULL,
            age_group VARCHAR(50) NOT NULL,
            count INT NOT NULL,
            FOREIGN KEY (stadtteil_nr) REFERENCES stadtteile(stadtteil_nr),
            UNIQUE KEY uk_stadtteil_date_age (stadtteil_nr, datum, age_group)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Create population by religion table
    cursor.execute("""
        CREATE TABLE population_by_religion (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stadtteil_nr INT NOT NULL,
            datum DATE NOT NULL,
            religion VARCHAR(100) NOT NULL,
            count INT NOT NULL,
            FOREIGN KEY (stadtteil_nr) REFERENCES stadtteile(stadtteil_nr),
            UNIQUE KEY uk_stadtteil_date_religion (stadtteil_nr, datum, religion)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Create population by family status table
    cursor.execute("""
        CREATE TABLE population_by_family_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stadtteil_nr INT NOT NULL,
            datum DATE NOT NULL,
            family_status VARCHAR(100) NOT NULL,
            count INT NOT NULL,
            FOREIGN KEY (stadtteil_nr) REFERENCES stadtteile(stadtteil_nr),
            UNIQUE KEY uk_stadtteil_date_status (stadtteil_nr, datum, family_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Create foreigners by nationality table
    cursor.execute("""
        CREATE TABLE foreigners_by_nationality (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stadtteil_nr INT NOT NULL,
            datum DATE NOT NULL,
            nationality VARCHAR(100) NOT NULL,
            count INT NOT NULL,
            FOREIGN KEY (stadtteil_nr) REFERENCES stadtteile(stadtteil_nr),
            UNIQUE KEY uk_stadtteil_date_nationality (stadtteil_nr, datum, nationality)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Create households table
    cursor.execute("""
        CREATE TABLE households (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stadtteil_nr INT NOT NULL,
            datum DATE NOT NULL,
            household_type VARCHAR(100) NOT NULL,
            count INT NOT NULL,
            FOREIGN KEY (stadtteil_nr) REFERENCES stadtteile(stadtteil_nr),
            UNIQUE KEY uk_stadtteil_date_type (stadtteil_nr, datum, household_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conn.commit()
    cursor.close()

    logger.info(">> Tables created successfully")


def import_stadtteile_from_all_csvs(conn, data_dir):
    """
    Scan all CSV files to collect unique Stadtteile and insert into stadtteile table.
    This ensures we have a complete districts table before importing demographic data.

    Args:
        conn: mysql.connector connection object
        data_dir: Path to directory containing CSV files
    """
    cursor = conn.cursor()
    stadtteile_map = {}  # Map: stadtteil_nr -> (name, lat, lon)

    # First pass: collect all stadtteile with numbers (from files that have Stadtteilnummer)
    csv_files = list(Path(data_dir).glob('*.csv'))

    for csv_file in csv_files:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            headers = reader.fieldnames

            # Check if this CSV has Stadtteilnummer
            if 'Stadtteilnummer' in headers:
                for row in reader:
                    stadtteil_nr = int(row['Stadtteilnummer'])
                    stadtteil_name = row['Stadtteil'].strip()
                    lat = row.get('lat', '').strip()
                    lon = row.get('lon', '').strip()

                    # Convert coordinates to float or None
                    try:
                        latitude = float(lat) if lat else None
                        longitude = float(lon) if lon else None
                    except (ValueError, TypeError):
                        latitude = None
                        longitude = None

                    stadtteile_map[stadtteil_nr] = (stadtteil_name, latitude, longitude)

    # Second pass: collect stadtteile without numbers (from files that only have Stadtteil name)
    # We'll need to create a name-to-number mapping
    stadtteile_by_name = {name: nr for nr, (name, _, _) in stadtteile_map.items()}
    next_nr = max(stadtteile_map.keys()) + 1 if stadtteile_map else 1

    for csv_file in csv_files:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            headers = reader.fieldnames

            # Check if this CSV has Stadtteil but NOT Stadtteilnummer
            stadtteil_col = None
            if 'Stadtteil' in headers and 'Stadtteilnummer' not in headers:
                stadtteil_col = 'Stadtteil'
            elif 'Stadtteile' in headers:
                stadtteil_col = 'Stadtteile'

            if stadtteil_col:
                for row in reader:
                    stadtteil_name = row[stadtteil_col].strip()

                    # Skip if already in map
                    if stadtteil_name in stadtteile_by_name:
                        continue

                    # Get coordinates
                    lat = row.get('lat', '').strip()
                    lon = row.get('lon', '').strip()

                    try:
                        latitude = float(lat) if lat else None
                        longitude = float(lon) if lon else None
                    except (ValueError, TypeError):
                        latitude = None
                        longitude = None

                    # Assign a new number
                    stadtteile_map[next_nr] = (stadtteil_name, latitude, longitude)
                    stadtteile_by_name[stadtteil_name] = next_nr
                    next_nr += 1

    # Insert all stadtteile into the database
    for nr, (name, lat, lon) in sorted(stadtteile_map.items()):
        cursor.execute(
            "INSERT IGNORE INTO stadtteile (stadtteil_nr, name, latitude, longitude) VALUES (%s, %s, %s, %s)",
            (nr, name, lat, lon)
        )

    conn.commit()
    cursor.close()
    logger.info(f">> Inserted {len(stadtteile_map)} Stadtteile with coordinates")

    # Query database to get actual list of valid stadtteil numbers
    # (some might have been skipped during insert due to missing data)
    cursor = conn.cursor()
    cursor.execute("SELECT stadtteil_nr FROM stadtteile")
    valid_stadtteile_nrs = set(row[0] for row in cursor.fetchall())
    cursor.close()

    # Return both name-to-number mapping and set of valid numbers for validation
    return stadtteile_by_name, valid_stadtteile_nrs


def get_stadtteil_nr(conn, stadtteil_name):
    """
    Get stadtteil_nr for a given district name.

    Args:
        conn: mysql.connector connection object
        stadtteil_name: Name of the district

    Returns:
        int: stadtteil_nr or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("SELECT stadtteil_nr FROM stadtteile WHERE name = %s", (stadtteil_name.strip(),))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else None


def import_population_by_gender(conn, csv_path):
    """
    Import population by gender data from CSV.

    Args:
        conn: mysql.connector connection object
        csv_path: Path to the CSV file
    """
    logger.info(f"Importing population by gender from {csv_path}...")
    cursor = conn.cursor()
    count = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            datum = row['Datum'].replace('_', '-')
            stadtteil_nr = int(row['Stadtteilnummer'])
            total = int(row['insgesamt'])
            male = int(row['maennlich'])
            female = int(row['weiblich'])

            cursor.execute(
                """INSERT INTO population_by_gender
                   (stadtteil_nr, datum, total, male, female)
                   VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE total=%s, male=%s, female=%s""",
                (stadtteil_nr, datum, total, male, female, total, male, female)
            )
            count += 1

    conn.commit()
    cursor.close()
    logger.info(f">> Imported {count} population by gender records")


def import_population_by_age(conn, csv_path):
    """
    Import population by age groups data from CSV.

    Args:
        conn: mysql.connector connection object
        csv_path: Path to the CSV file
    """
    logger.info(f"Importing population by age from {csv_path}...")
    cursor = conn.cursor()
    count = 0

    # Age group column names from the CSV
    age_groups = [
        '0 bis unter 3', '3 bis unter 6', ' 6 bis unter 10', '10 bis unter 12',
        '12 bis unter 15', '15 bis unter 18', '18 bis unter 21', '21 bis unter 25',
        '25 bis unter 30', '30 bis unter 35', '35 bis unter 40', '40 bis unter 45',
        '45 bis unter 50', '50 bis unter 55', '55 bis unter 60', '60 bis unter 65',
        '65 bis unter 70', '70 bis unter 75', '75 bis unter 80', '80 und aelter'
    ]

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            datum = row['Datum'].replace('_', '-')
            stadtteil_nr = int(row['Stadtteilnummer'])

            # Insert each age group as a separate row
            for age_group in age_groups:
                if age_group in row and row[age_group]:
                    group_count = int(row[age_group])
                    try:
                        cursor.execute(
                            """INSERT INTO population_by_age
                            (stadtteil_nr, datum, age_group, count)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE count=%s""",
                            (stadtteil_nr, datum, age_group.strip(), group_count, group_count)
                        )
                        count += 1
                    except Exception:
                        continue

    conn.commit()
    cursor.close()
    logger.info(f">> Imported {count} population by age records")


def import_generic_data(conn, csv_path, table_name, merkmal_column, stadtteile_map, valid_stadtteile_nrs):
    """
    Generic importer for CSV files with similar structure.
    Handles CSVs with or without Stadtteilnummer by looking up district names.

    Args:
        conn: mysql.connector connection object
        csv_path: Path to the CSV file
        table_name: Target table name
        merkmal_column: Name of the column containing the category/type
        stadtteile_map: Dict mapping district names to numbers
        valid_stadtteile_nrs: Set of valid stadtteil numbers for validation
    """
    logger.info(f"Importing data from {Path(csv_path).name} into {table_name}...")
    cursor = conn.cursor()
    count = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        headers = reader.fieldnames

        # Detect stadtteil column
        stadtteil_col = None
        has_number = False
        if 'Stadtteilnummer' in headers:
            has_number = True
        elif 'Stadtteil' in headers:
            stadtteil_col = 'Stadtteil'
        elif 'Stadtteile' in headers:
            stadtteil_col = 'Stadtteile'

        # Skip metadata columns
        skip_columns = {'Land', 'Stadt', 'Kategorie', 'Merkmal', 'Datum', 'Jahr',
                       'Stadtteilnummer', 'Stadtteil', 'Stadtteile', 'lat', 'lon'}

        for row in reader:
            # Get stadtteil_nr
            if has_number:
                stadtteil_nr = int(row['Stadtteilnummer'])
                # Validate that this stadtteil_nr exists in stadtteile table
                if stadtteil_nr not in valid_stadtteile_nrs:
                    continue  # Skip if district doesn't exist
            elif stadtteil_col:
                stadtteil_name = row[stadtteil_col].strip()
                stadtteil_nr = stadtteile_map.get(stadtteil_name)
                if not stadtteil_nr:
                    continue  # Skip unknown districts
            else:
                continue  # No district info, skip

            # Get date
            try:
                datum = row['Datum'].replace('_', '-')
            except KeyError:
                jahr_value = row.get('Jahr', '2023')
                # If Jahr contains underscores/dashes or is longer than 4 chars, it's a full date
                if '_' in jahr_value or '-' in jahr_value or len(jahr_value) > 4:
                    # Parse DD-MM-YYYY or DD_MM_YYYY and convert to YYYY-MM-DD for MySQL
                    date_str = jahr_value.replace('_', '-')
                    try:
                        # Try parsing as DD-MM-YYYY
                        from datetime import datetime
                        dt = datetime.strptime(date_str, '%d-%m-%Y')
                        datum = dt.strftime('%Y-%m-%d')
                    except ValueError:
                        # If that fails, assume it's already in correct format
                        datum = date_str
                else:
                    # It's just a year, append -01-01
                    datum = jahr_value + "-01-01"

            # Import data columns
            for header in headers:
                if header not in skip_columns and row.get(header):
                    try:
                        value = int(row[header])
                        cursor.execute(
                            f"""INSERT INTO {table_name}
                               (stadtteil_nr, datum, {merkmal_column}, count)
                               VALUES (%s, %s, %s, %s)
                               ON DUPLICATE KEY UPDATE count=%s""",
                            (stadtteil_nr, datum, header, value, value)
                        )
                        count += 1
                    except ValueError:
                        pass  # Skip non-numeric values

    conn.commit()
    cursor.close()
    logger.info(f">> Imported {count} records into {table_name}")


def import_all_csv_data(conn):
    """
    Import all CSV files from the data directory.

    Args:
        conn: mysql.connector connection object
    """
    data_dir = Path('/data')

    if not data_dir.exists():
        logger.warning("Data directory /data not found, trying local ./data")
        data_dir = Path('./data')

    if not data_dir.exists():
        logger.error("No data directory found!")
        return

    # STEP 1: Build complete stadtteile table from all CSVs
    logger.info("==> Building complete stadtteile table from all CSVs")
    stadtteile_map, valid_stadtteile_nrs = import_stadtteile_from_all_csvs(conn, data_dir)

    # STEP 2: Import demographic data using the stadtteile mapping
    csv_configs = [
        ('kiel_bevoelkerung_stadtteile_einwohner_geschlecht.csv', None, None),  # Special handler
        ('kiel_bevoelkerung_altersgruppen_stadtteile.csv', None, None),  # Special handler
        ('kiel_bevoelkerung_einwohner_nach_religionszugehoerigkeit_in_den_stadtteilen.csv',
         'population_by_religion', 'religion'),
        ('kiel_bevoelkerung_einwohner_nach_familienstand_in_den_stadtteilen.csv',
         'population_by_family_status', 'family_status'),
        ('kiel_bevoelkerung_auslaender_nach_ausgesuchten_nationalitaeten_in_den_stadtteilen.csv',
         'foreigners_by_nationality', 'nationality'),
        ('kiel_bevoelkerung_haushalte_nach_haushaltstypen_und_personenanzahl_in_den_stadtteilen.csv',
         'households', 'household_type'),
    ]

    for filename, table_name, column_name in csv_configs:
        file_path = data_dir / filename
        if not file_path.exists():
            logger.warning(f"File not found: {filename}")
            continue

        # Use special handlers for gender and age data (they have different structures)
        if filename == 'kiel_bevoelkerung_stadtteile_einwohner_geschlecht.csv':
            import_population_by_gender(conn, file_path)
        elif filename == 'kiel_bevoelkerung_altersgruppen_stadtteile.csv':
            import_population_by_age(conn, file_path)
        else:
            import_generic_data(conn, file_path, table_name, column_name, stadtteile_map, valid_stadtteile_nrs)


def verify_data(conn):
    """
    Verify that data was imported correctly.

    Args:
        conn: mysql.connector connection object
    """
    logger.info("Verifying data import...")

    cursor = conn.cursor()

    tables = [
        'stadtteile',
        'population_by_gender',
        'population_by_age',
        'population_by_religion',
        'population_by_family_status',
        'foreigners_by_nationality',
        'households'
    ]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        logger.info(f">> {table}: {count} records")

    # Show sample Stadtteile
    cursor.execute("SELECT stadtteil_nr, name FROM stadtteile ORDER BY stadtteil_nr LIMIT 5")
    logger.info("Sample Stadtteile:")
    for row in cursor.fetchall():
        logger.info(f"  {row[0]}: {row[1]}")

    cursor.close()


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Kiel City Open Data Loader - MySQL Import")
    logger.info("Data source: https://www.kiel.de/.../open_data/")
    logger.info("=" * 60)

    try:
        # Connect to MySQL
        conn = wait_for_mysql()

        # Create database schema
        create_tables(conn)

        # Import CSV data
        import_all_csv_data(conn)

        # Verify
        verify_data(conn)

        # Close connection
        conn.close()

        logger.info("=" * 60)
        logger.info(">> Data loading completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"ERROR: Error during data loading: {e}")
        import traceback
        traceback.print_exc()
        pass


if __name__ == "__main__":
    main()
