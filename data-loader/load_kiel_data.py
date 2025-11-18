"""
PostgreSQL Data Loader for Kiel City Points of Interest

This script demonstrates:
1. Database connection with psycopg2
2. Table creation with SQL DDL
3. Batch data insertion
4. Error handling and retries
5. Connection lifecycle management

The script populates the database with real Kiel landmarks and POIs.
"""

import os
import time
import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_postgres(max_retries=30):
    """
    Wait for PostgreSQL to be ready.
    
    Args:
        max_retries: Maximum number of connection attempts
    
    Returns:
        psycopg2 connection object
    """
    logger.info("Waiting for PostgreSQL to be ready...")
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'postgres'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                database=os.getenv('POSTGRES_DB', 'kiel_data'),
                user=os.getenv('POSTGRES_USER', 'kiel_user'),
                password=os.getenv('POSTGRES_PASSWORD', 'kiel_secure_password_2024')
            )
            logger.info("✓ PostgreSQL is ready!")
            return conn
        except psycopg2.OperationalError as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: PostgreSQL not ready yet...")
            time.sleep(2)
    
    raise Exception("PostgreSQL did not become ready in time")


def create_table(conn):
    """
    Create the points_of_interest table.
    
    This demonstrates:
    - SQL DDL execution
    - Proper data types for geospatial data
    - Primary key and indexes
    
    Args:
        conn: psycopg2 connection object
    """
    logger.info("Creating points_of_interest table...")
    
    with conn.cursor() as cursor:
        # Drop table if exists (for clean restart)
        cursor.execute("DROP TABLE IF EXISTS points_of_interest")
        
        # Create table with appropriate columns
        cursor.execute("""
            CREATE TABLE points_of_interest (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                type VARCHAR(50) NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                description TEXT
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX idx_poi_type ON points_of_interest(type)
        """)
        cursor.execute("""
            CREATE INDEX idx_poi_name ON points_of_interest(name)
        """)
        
        conn.commit()
    
    logger.info("✓ Table created successfully")


def insert_kiel_pois(conn):
    """
    Insert Points of Interest for Kiel city.
    
    This demonstrates:
    - Batch insert with executemany
    - Parameterized queries (防止 SQL injection)
    - Real-world geospatial data
    
    Data includes actual Kiel landmarks, museums, parks, and infrastructure.
    
    Args:
        conn: psycopg2 connection object
    """
    logger.info("Inserting Kiel Points of Interest...")
    
    # Real Kiel POIs with accurate coordinates
    kiel_pois = [
        # Landmarks
        ('Kiel Hauptbahnhof', 'transport', 54.3147, 10.1318, 'Main train station of Kiel'),
        ('Kiel Rathaus', 'landmark', 54.3233, 10.1359, 'Historic city hall with tower'),
        ('Laboe Naval Memorial', 'landmark', 54.4083, 10.2278, 'Memorial for fallen sailors'),
        ('Holstenstraße', 'shopping', 54.3217, 10.1356, 'Main shopping street in Kiel'),
        ('Kiel Opera House', 'culture', 54.3208, 10.1289, 'Theater and opera venue'),
        
        # Museums
        ('Schifffahrtsmuseum', 'museum', 54.3294, 10.1478, 'Maritime Museum showcasing naval history'),
        ('Kunsthalle Kiel', 'museum', 54.3189, 10.1322, 'Art museum with modern collections'),
        ('Stadt- und Schifffahrtsmuseum Warleberger Hof', 'museum', 54.3242, 10.1389, 'City and maritime history museum'),
        ('Aquarium GEOMAR', 'museum', 54.3278, 10.1508, 'Marine research aquarium'),
        ('Zoological Museum', 'museum', 54.3414, 10.1150, 'University zoological collection'),
        
        # Parks and Nature
        ('Schrevenpark', 'park', 54.3392, 10.1244, 'Large public park with lake'),
        ('Botanical Garden Kiel', 'park', 54.3453, 10.1142, 'University botanical garden'),
        ('Forstbaumschule', 'park', 54.3147, 10.0836, 'Historic park and arboretum'),
        ('Hiroshima Park', 'park', 54.3267, 10.1450, 'Waterfront park at the fjord'),
        ('Werftpark', 'park', 54.3375, 10.1469, 'Park on former shipyard site'),
        
        # Waterfront and Beaches
        ('Kiellinie', 'waterfront', 54.3289, 10.1464, 'Popular waterfront promenade'),
        ('Falckenstein Beach', 'beach', 54.3847, 10.1872, 'Beach on the Kiel Fjord'),
        ('Strande Beach', 'beach', 54.4019, 10.1836, 'Sandy beach north of Kiel'),
        ('Schilksee Marina', 'waterfront', 54.4131, 10.1653, 'Olympic sailing marina'),
        
        # Education
        ('Kiel University', 'education', 54.3414, 10.1150, 'Christian-Albrechts-Universität zu Kiel'),
        ('GEOMAR Helmholtz Centre', 'education', 54.3278, 10.1508, 'Ocean research center'),
        ('Fachhochschule Kiel', 'education', 54.3125, 10.1331, 'University of Applied Sciences'),
        
        # Religious Buildings
        ('St. Nikolai Church', 'church', 54.3231, 10.1394, 'Historic church in city center'),
        ('Kiel Monastery', 'church', 54.3194, 10.1311, 'Former Franciscan monastery'),
        
        # Sports and Recreation
        ('Holstein-Stadion', 'sports', 54.3492, 10.1161, 'Football stadium of Holstein Kiel'),
        ('Schwentine Canoe Trail', 'sports', 54.3336, 10.0978, 'Popular kayaking route'),
        
        # Food Markets
        ('Wochenmarkt Exerzierplatz', 'market', 54.3197, 10.1336, 'Weekly farmers market'),
        ('Asmus-Bremer-Platz Market', 'market', 54.3189, 10.1267, 'Local food market'),
        
        # Historic Sites
        ('Düsternbrook Submarine Bunker', 'historic', 54.3361, 10.1528, 'WWII bunker remains'),
        ('Kiel-Holtenau Locks', 'historic', 54.3736, 10.1453, 'Locks connecting to Kiel Canal'),
    ]
    
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO points_of_interest (name, type, latitude, longitude, description)
            VALUES (%s, %s, %s, %s, %s)
            """,
            kiel_pois
        )
        conn.commit()
    
    logger.info(f"✓ Inserted {len(kiel_pois)} Points of Interest")


def verify_data(conn):
    """
    Verify that data was inserted correctly.
    
    Args:
        conn: psycopg2 connection object
    """
    logger.info("Verifying data insertion...")
    
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM points_of_interest")
        count = cursor.fetchone()[0]
        logger.info(f"✓ Total POIs in database: {count}")
        
        cursor.execute("SELECT DISTINCT type FROM points_of_interest ORDER BY type")
        types = cursor.fetchall()
        logger.info(f"✓ POI types: {', '.join([t[0] for t in types])}")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Kiel City Data Loader - PostgreSQL Initialization")
    logger.info("=" * 60)
    
    try:
        # Connect to PostgreSQL
        conn = wait_for_postgres()
        
        # Create database schema
        create_table(conn)
        
        # Insert data
        insert_kiel_pois(conn)
        
        # Verify
        verify_data(conn)
        
        # Close connection
        conn.close()
        
        logger.info("=" * 60)
        logger.info("✓ Data loading completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Error during data loading: {e}")
        raise


if __name__ == "__main__":
    main()
