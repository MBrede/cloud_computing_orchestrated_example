"""
Database connection management and SDK examples.

This module demonstrates proper usage of:
- mysql-connector-python for MySQL (SQL database SDK)
- pymongo for MongoDB (NoSQL database SDK)
- redis for caching

Key learning points:
1. Connection pooling for MySQL
2. Context managers for safe connection handling
3. Error handling and retries
4. Cursor management in SQL
5. Document operations in MongoDB
"""

import os
import time
import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import redis
from typing import Optional, Dict, Any, List
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MySQLDatabase:
    """
    MySQL database connection manager using mysql-connector-python.

    This class demonstrates:
    - Connection pooling for efficient resource usage
    - Proper connection lifecycle management
    - SQL query execution with parameterized queries (防止 SQL injection)
    - Transaction handling
    - Dict-based result rows for easier data access

    mysql-connector-python is the official MySQL driver from Oracle.
    It's pure Python, well-maintained, and familiar to students who use MySQL.
    """

    def __init__(self):
        """Initialize MySQL connection pool."""
        self.pool: Optional[pooling.MySQLConnectionPool] = None
        self._initialize_pool()

    def _initialize_pool(self, retries=5):
        """
        Initialize connection pool with retry logic.

        Args:
            retries: Number of connection attempts before failing
        """
        for attempt in range(retries):
            try:
                # Create connection pool
                self.pool = pooling.MySQLConnectionPool(
                    pool_name="kiel_pool",
                    pool_size=10,
                    pool_reset_session=True,
                    host=os.getenv('MYSQL_HOST', 'mysql'),
                    port=int(os.getenv('MYSQL_PORT', '3306')),
                    database=os.getenv('MYSQL_DB', 'kiel_data'),
                    user=os.getenv('MYSQL_USER', 'kiel_user'),
                    password=os.getenv('MYSQL_PASSWORD', 'kiel_secure_password_2024'),
                    autocommit=False  # Explicit transaction control
                )

                # Test connection
                conn = self.pool.get_connection()
                conn.ping(reconnect=True, attempts=3, delay=1)
                conn.close()

                logger.info("MySQL connection pool created successfully")
                return
            except MySQLError as e:
                logger.warning(f"MySQL connection attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Failed to connect to MySQL after all retries")
                    raise

    def get_connection(self):
        """
        Get a connection from the pool.

        Returns:
            mysql.connector connection object

        Example usage:
            conn = db.get_connection()
            try:
                # Use connection
            finally:
                conn.close()
        """
        if self.pool is None:
            self._initialize_pool()
        return self.pool.get_connection()

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[List[Dict]]:
        """
        Execute a SQL query with proper connection management.

        This demonstrates:
        - Parameterized queries with %s placeholders (防止 SQL injection)
        - Dictionary cursor for easy column access
        - Proper transaction handling
        - Automatic resource cleanup

        Args:
            query: SQL query string (use %s for parameters)
            params: Query parameters (prevents SQL injection)
            fetch: Whether to fetch and return results

        Returns:
            Query results as list of dicts, or None

        Example:
            results = db.execute_query(
                "SELECT * FROM points_of_interest WHERE type = %s",
                ('museum',)
            )
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)  # Return rows as dictionaries

            cursor.execute(query, params)

            if fetch:
                results = cursor.fetchall()
                cursor.close()
                return results
            else:
                conn.commit()
                cursor.close()
                return None

        except MySQLError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database query error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """
        Execute a query multiple times with different parameters (batch insert).

        This demonstrates executemany for efficient batch operations.
        Particularly useful for bulk inserts.

        Args:
            query: SQL query string
            params_list: List of parameter tuples

        Example:
            db.execute_many(
                "INSERT INTO points_of_interest (name, type, latitude, longitude) VALUES (%s, %s, %s, %s)",
                [('Museum', 'culture', 54.32, 10.13), ('Park', 'nature', 54.31, 10.12)]
            )
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.executemany(query, params_list)
            conn.commit()
            cursor.close()

        except MySQLError as e:
            if conn:
                conn.rollback()
            logger.error(f"Batch execution error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            # Connection pool doesn't have a direct close method
            # Connections are closed when they're returned to the pool
            logger.info("MySQL connection pool cleanup initiated")


class MongoDatabase:
    """
    MongoDB database connection manager using pymongo.
    
    This class demonstrates:
    - MongoDB connection with authentication
    - Document CRUD operations
    - Query filtering and projection
    - Indexing for performance
    - Time-series data handling
    """
    
    def __init__(self):
        """Initialize MongoDB connection."""
        self.client: Optional[MongoClient] = None
        self.db = None
        self._connect()
    
    def _connect(self, retries=5):
        """
        Establish MongoDB connection with retry logic.
        
        Args:
            retries: Number of connection attempts before failing
        """
        for attempt in range(retries):
            try:
                mongo_host = os.getenv('MONGO_HOST', 'mongodb')
                mongo_port = int(os.getenv('MONGO_PORT', '27017'))
                mongo_user = os.getenv('MONGO_USER', 'bike_user')
                mongo_password = os.getenv('MONGO_PASSWORD', 'bike_secure_password_2024')
                mongo_db = os.getenv('MONGO_DB', 'bike_sharing')
                
                # Connection string with authentication
                connection_string = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"
                
                self.client = MongoClient(
                    connection_string,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000
                )
                
                # Verify connection
                self.client.admin.command('ping')
                self.db = self.client[mongo_db]
                
                # Create indexes for better query performance
                self._ensure_indexes()
                
                logger.info("MongoDB connection established successfully")
                return
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Failed to connect to MongoDB after all retries")
                    raise
    
    def _ensure_indexes(self):
        """Create indexes for better query performance."""
        try:
            # Index on station_id for fast lookups
            self.db.bike_stations.create_index("station_id", unique=True)
            # Index on last_updated for time-based queries
            self.db.bike_stations.create_index("last_updated")
            # Geospatial index for location-based queries
            self.db.bike_stations.create_index([("location", "2dsphere")])
            logger.info("MongoDB indexes created")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """
        Insert a single document.
        
        Args:
            collection: Collection name
            document: Document to insert
        
        Returns:
            Inserted document ID as string
        
        Example:
            doc_id = mongo_db.insert_one('bike_stations', {
                'station_id': 'KIEL001',
                'name': 'Hauptbahnhof',
                'bikes_available': 5
            })
        """
        result = self.db[collection].insert_one(document)
        return str(result.inserted_id)
    
    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict]:
        """
        Find a single document.
        
        Args:
            collection: Collection name
            query: Query filter
        
        Returns:
            Document or None
        
        Example:
            station = mongo_db.find_one('bike_stations', {'station_id': 'KIEL001'})
        """
        result = self.db[collection].find_one(query)
        if result:
            result['_id'] = str(result['_id'])  # Convert ObjectId to string
        return result
    
    def find_many(self, collection: str, query: Dict[str, Any] = None, 
                  projection: Dict[str, int] = None, limit: int = 0) -> List[Dict]:
        """
        Find multiple documents.
        
        Args:
            collection: Collection name
            query: Query filter (None for all documents)
            projection: Fields to include/exclude
            limit: Maximum number of documents (0 for no limit)
        
        Returns:
            List of documents
        
        Example:
            stations = mongo_db.find_many(
                'bike_stations',
                {'bikes_available': {'$gt': 0}},
                limit=10
            )
        """
        cursor = self.db[collection].find(query or {}, projection)
        if limit > 0:
            cursor = cursor.limit(limit)
        
        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
            results.append(doc)
        return results
    
    def update_one(self, collection: str, query: Dict[str, Any], 
                   update: Dict[str, Any], upsert: bool = False) -> int:
        """
        Update a single document.
        
        Args:
            collection: Collection name
            query: Query filter
            update: Update operations
            upsert: Insert if not exists
        
        Returns:
            Number of modified documents
        
        Example:
            mongo_db.update_one(
                'bike_stations',
                {'station_id': 'KIEL001'},
                {'$set': {'bikes_available': 3}},
                upsert=True
            )
        """
        result = self.db[collection].update_one(query, update, upsert=upsert)
        return result.modified_count
    
    def aggregate(self, collection: str, pipeline: List[Dict]) -> List[Dict]:
        """
        Execute an aggregation pipeline.
        
        Args:
            collection: Collection name
            pipeline: Aggregation pipeline stages
        
        Returns:
            Aggregation results
        
        Example:
            # Get total bikes available
            result = mongo_db.aggregate('bike_stations', [
                {'$group': {'_id': None, 'total': {'$sum': '$bikes_available'}}}
            ])
        """
        cursor = self.db[collection].aggregate(pipeline)
        return list(cursor)
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


class RedisCache:
    """
    Redis cache manager for improving API performance.
    
    This class demonstrates:
    - Simple key-value caching
    - TTL (Time To Live) management
    - Cache invalidation strategies
    """
    
    def __init__(self):
        """Initialize Redis connection."""
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self, retries=5):
        """Establish Redis connection with retry logic."""
        for attempt in range(retries):
            try:
                self.client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'redis'),
                    port=int(os.getenv('REDIS_PORT', '6379')),
                    password=os.getenv('REDIS_PASSWORD', 'redis_secure_password_2024'),
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # Test connection
                self.client.ping()
                logger.info("Redis connection established successfully")
                return
            except redis.ConnectionError as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("Failed to connect to Redis after all retries")
                    raise
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value (automatically deserialized) or None
        """
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default 300 = 5 minutes)
        """
        try:
            self.client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete a key from cache."""
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    def clear_pattern(self, pattern: str):
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., 'bikes:*')
        """
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear pattern error: {e}")


# Global database instances
mysql_db = MySQLDatabase()
mongo_db = MongoDatabase()
redis_cache = RedisCache()
