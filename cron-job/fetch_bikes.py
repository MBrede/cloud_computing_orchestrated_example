"""
DonkeyRepublic Bike Data Fetcher for MongoDB

This script demonstrates:
1. REST API consumption with requests
2. MongoDB document insertion with pymongo
3. Time-series data handling
4. Error handling and retries
5. Upsert operations (update or insert)

The script fetches current bike availability from DonkeyRepublic API
and stores it in MongoDB for the Kiel City Data Platform.
"""

import os
import time
import requests
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_mongodb(max_retries=30):
    """
    Wait for MongoDB to be ready.
    
    Args:
        max_retries: Maximum number of connection attempts
    
    Returns:
        MongoDB database object
    """
    logger.info("Waiting for MongoDB to be ready...")
    
    mongo_host = os.getenv('MONGO_HOST', 'mongodb')
    mongo_port = int(os.getenv('MONGO_PORT', '27017'))
    mongo_user = os.getenv('MONGO_USER', 'bike_user')
    mongo_password = os.getenv('MONGO_PASSWORD', 'bike_secure_password_2024')
    mongo_db = os.getenv('MONGO_DB', 'bike_sharing')
    
    for attempt in range(max_retries):
        try:
            connection_string = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"
            client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            client.admin.command('ping')
            logger.info("✓ MongoDB is ready!")
            return client[mongo_db]
        except ConnectionFailure as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: MongoDB not ready yet...")
            time.sleep(2)
    
    raise Exception("MongoDB did not become ready in time")


def fetch_donkey_bikes():
    """
    Fetch bike stations from DonkeyRepublic API.
    
    This demonstrates:
    - HTTP GET request with headers
    - JSON parsing
    - Error handling for API calls
    
    Returns:
        list: Bike stations data
    """
    logger.info("Fetching bike data from DonkeyRepublic API...")
    
    api_url = os.getenv('DONKEY_API_URL', 'https://stables.donkey.bike/api/public/nearby')
    api_header = os.getenv('DONKEY_API_HEADER', 'application/com.donkeyrepublic.v7')
    
    # Kiel bounding box coordinates
    top_right = os.getenv('KIEL_BBOX_TOP_RIGHT', '54.406143,10.262604')
    bottom_left = os.getenv('KIEL_BBOX_BOTTOM_LEFT', '54.272041,10.006485')
    
    try:
        response = requests.get(
            api_url,
            headers={'Accept': api_header},
            params={
                'top_right': top_right,
                'bottom_left': bottom_left,
                'filter_type': 'box'
            },
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"✓ Fetched data successfully")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ Error fetching bike data: {e}")
        return None


def parse_station_data(api_data):
    """
    Parse DonkeyRepublic API response into our data model.
    
    Args:
        api_data: Raw API response
    
    Returns:
        list: Parsed station documents
    """
    stations = []
    
    # The API returns different structures, adapt as needed
    # This handles the 'hubs' structure from DonkeyRepublic
    if isinstance(api_data, dict):
        hubs = api_data.get('hubs', [])
        
        for hub in hubs:
            try:
                # Extract station information
                station = {
                    'station_id': str(hub.get('id', hub.get('name', 'unknown'))),
                    'name': hub.get('name', 'Unknown Station'),
                    'latitude': hub.get('latitude') or hub.get('lat', 0.0),
                    'longitude': hub.get('longitude') or hub.get('lng', 0.0),
                    'bikes_available': hub.get('available_bikes', 0),
                    'capacity': hub.get('max_bikes') or hub.get('capacity'),
                    'last_updated': datetime.now(),
                    'location': {
                        'type': 'Point',
                        'coordinates': [
                            hub.get('longitude') or hub.get('lng', 0.0),
                            hub.get('latitude') or hub.get('lat', 0.0)
                        ]
                    }
                }
                stations.append(station)
            except Exception as e:
                logger.warning(f"Error parsing station: {e}")
                continue
    
    logger.info(f"✓ Parsed {len(stations)} stations")
    return stations


def update_mongodb(db, stations):
    """
    Update MongoDB with current bike station data.
    
    This demonstrates:
    - Upsert operations (update if exists, insert if not)
    - Bulk write operations for efficiency
    - MongoDB update operators ($set, $currentDate, etc.)
    
    Args:
        db: MongoDB database object
        stations: List of station documents
    """
    if not stations:
        logger.warning("No stations to update")
        return
    
    logger.info(f"Updating MongoDB with {len(stations)} stations...")
    
    collection = db.bike_stations
    updated_count = 0
    
    for station in stations:
        try:
            # Upsert: update if exists, insert if not
            result = collection.update_one(
                {'station_id': station['station_id']},
                {'$set': station},
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                updated_count += 1
                
        except Exception as e:
            logger.error(f"Error updating station {station['station_id']}: {e}")
            continue
    
    logger.info(f"✓ Updated {updated_count} stations in MongoDB")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("DonkeyRepublic Bike Data Sync - MongoDB Update")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        # Connect to MongoDB
        db = wait_for_mongodb()
        
        # Fetch bike data from API
        api_data = fetch_donkey_bikes()
        
        if api_data:
            # Parse the data
            stations = parse_station_data(api_data)
            
            # Update MongoDB
            update_mongodb(db, stations)
            
            # Get statistics
            total_stations = db.bike_stations.count_documents({})
            total_bikes = sum(
                station.get('bikes_available', 0)
                for station in db.bike_stations.find({})
            )
            
            logger.info(f"✓ Total stations in database: {total_stations}")
            logger.info(f"✓ Total bikes available: {total_bikes}")
        else:
            logger.warning("No data fetched, skipping update")
        
        logger.info("=" * 60)
        logger.info("✓ Bike data sync completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Error during bike data sync: {e}")
        raise


if __name__ == "__main__":
    main()
