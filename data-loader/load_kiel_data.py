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


def import_stadtteile_from_csv(conn, csv_path):
    """
    Extract unique Stadtteile from a CSV file and insert into stadtteile table.

    Args:
        conn: mysql.connector connection object
        csv_path: Path to CSV file containing Stadtteil data
    """
    cursor = conn.cursor()
    stadtteile = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            stadtteil_nr = int(row['Stadtteilnummer'])
            stadtteil_name = row['Stadtteil']
            lat = row.get('lat', '').strip()
            lon = row.get('lon', '').strip()

            # Convert coordinates to float or None
            try:
                latitude = float(lat) if lat else None
                longitude = float(lon) if lon else None
            except (ValueError, TypeError):
                latitude = None
                longitude = None

            stadtteile[stadtteil_nr] = (stadtteil_name, latitude, longitude)

    # Insert stadtteile with coordinates
    for nr, (name, lat, lon) in sorted(stadtteile.items()):
        cursor.execute(
            "INSERT IGNORE INTO stadtteile (stadtteil_nr, name, latitude, longitude) VALUES (%s, %s, %s, %s)",
            (nr, name, lat, lon)
        )

    conn.commit()
    cursor.close()
    logger.info(f">> Inserted {len(stadtteile)} Stadtteile with coordinates")


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


def import_generic_data(conn, csv_path, table_name, merkmal_column):
    """
    Generic importer for CSV files with similar structure.

    Args:
        conn: mysql.connector connection object
        csv_path: Path to the CSV file
        table_name: Target table name
        merkmal_column: Name of the column containing the category/type
    """
    logger.info(f"Importing data from {csv_path} into {table_name}...")
    cursor = conn.cursor()
    count = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        headers = reader.fieldnames

        for i, row in enumerate(reader):
            try:
                datum = row['Datum'].replace('_', '-')
            except KeyError:
                datum = row['Jahr'].replace('_', '-') + "-01-01"
            try:
                stadtteil_nr = int(row['Stadtteilnummer'])
            except KeyError:
                stadtteil_nr = i
            merkmal = row.get('Merkmal', '')

            # Find data columns (skip metadata columns)
            skip_columns = ['Land', 'Stadt', 'Kategorie', 'Merkmal', 
                            'Datum','Jahr',
                           'Stadtteilnummer', 'Stadtteil']

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
                        # Skip non-numeric values
                        pass

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

    # First, import stadtteile from the gender file (has all districts)
    gender_file = data_dir / 'kiel_bevoelkerung_stadtteile_einwohner_geschlecht.csv'
    if gender_file.exists():
        import_stadtteile_from_csv(conn, gender_file)
        import_population_by_gender(conn, gender_file)

    # Import age groups
    age_file = data_dir / 'kiel_bevoelkerung_altersgruppen_stadtteile.csv'
    if age_file.exists():
        import_population_by_age(conn, age_file)

    # Import religion data
    religion_file = data_dir / 'kiel_bevoelkerung_einwohner_nach_religionszugehoerigkeit_in_den_stadtteilen.csv'
    if religion_file.exists():
        import_generic_data(conn, religion_file, 'population_by_religion', 'religion')

    # Import family status data
    family_file = data_dir / 'kiel_bevoelkerung_einwohner_nach_familienstand_in_den_stadtteilen.csv'
    if family_file.exists():
        import_generic_data(conn, family_file, 'population_by_family_status', 'family_status')

    # Import foreigners by nationality
    nationality_file = data_dir / 'kiel_bevoelkerung_auslaender_nach_ausgesuchten_nationalitaeten_in_den_stadtteilen.csv'
    if nationality_file.exists():
        import_generic_data(conn, nationality_file, 'foreigners_by_nationality', 'nationality')

    # Import households
    households_file = data_dir / 'kiel_bevoelkerung_haushalte_nach_haushaltstypen_und_personenanzahl_in_den_stadtteilen.csv'
    if households_file.exists():
        import_generic_data(conn, households_file, 'households', 'household_type')


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
