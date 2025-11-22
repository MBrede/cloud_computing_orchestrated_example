"""
Kiel City Data Platform - FastAPI Application

This FastAPI application demonstrates:
1. RESTful API design with proper HTTP methods (GET, POST, PUT, DELETE)
2. Integration with multiple databases (MySQL, MongoDB, Redis)
3. Automatic API documentation (Swagger/OpenAPI)
4. Request/response validation with Pydantic
5. Error handling and status codes
6. Caching strategies for performance

Endpoints:
- City Data (MySQL): /api/city/*
- Bike Sharing (MongoDB): /api/bikes/*
- System Health: /health
- Statistics: /api/stats
"""

import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import (
    POI, POICreate, 
    BikeStation, BikeStationCreate, BikeStationHistory,
    HealthCheck, Stats, ErrorResponse
)
from database import mysql_db, mongo_db, redis_cache

# Initialize FastAPI app with metadata for Swagger documentation
app = FastAPI(
    title=os.getenv('API_TITLE', 'Kiel City Data Platform'),
    version=os.getenv('API_VERSION', '1.0.0'),
    description="""
    # Kiel City Data Platform API
    
    A comprehensive API demonstrating cloud computing concepts with multiple database systems.
    
    ## Features
    
    - **MySQL Integration**: Structured city data (Points of Interest)
    - **MongoDB Integration**: Time-series bike sharing data
    - **Redis Caching**: Performance optimization for frequently accessed data
    - **Full CRUD Operations**: Create, Read, Update, Delete for all resources
    - **Data Validation**: Automatic request/response validation with Pydantic
    
    ## Database SDKs Used

    - **mysql-connector-python**: Official MySQL driver for Python
    - **pymongo**: MongoDB driver for Python
    - **redis-py**: Redis client for Python
    
    ## Learning Objectives
    
    This API serves as a practical example for:
    - RESTful API design patterns
    - Multi-database architecture
    - Caching strategies
    - Container orchestration with Docker Compose
    - Swagger/OpenAPI documentation
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check and Statistics Endpoints
# ============================================================================

@app.get(
    "/health",
    response_model=HealthCheck,
    tags=["System"],
    summary="Check system health",
    description="Returns the health status of all connected services (MySQL, MongoDB, Redis)"
)
async def health_check():
    """
    Health check endpoint to verify all services are operational.

    Returns:
        HealthCheck: Status of all database connections
    """
    mysql_healthy = False
    mongodb_healthy = False
    redis_healthy = False

    # Check MySQL
    try:
        mysql_db.execute_query("SELECT 1", fetch=True)
        mysql_healthy = True
    except Exception as e:
        print(f"MySQL health check failed: {e}")

    # Check MongoDB
    try:
        mongo_db.client.admin.command('ping')
        mongodb_healthy = True
    except Exception as e:
        print(f"MongoDB health check failed: {e}")

    # Check Redis
    try:
        redis_cache.client.ping()
        redis_healthy = True
    except Exception as e:
        print(f"Redis health check failed: {e}")

    overall_status = "healthy" if all([mysql_healthy, mongodb_healthy, redis_healthy]) else "degraded"

    return HealthCheck(
        status=overall_status,
        mysql=mysql_healthy,
        mongodb=mongodb_healthy,
        redis=redis_healthy,
        timestamp=datetime.now()
    )


@app.get(
    "/api/stats",
    response_model=Stats,
    tags=["System"],
    summary="Get database statistics",
    description="Returns aggregated statistics from all databases"
)
async def get_stats():
    """
    Get system-wide statistics.
    
    Returns:
        Stats: Aggregated statistics from all databases
    """
    # Count POIs in MySQL
    total_pois = 0
    try:
        result = mysql_db.execute_query("SELECT COUNT(*) as count FROM points_of_interest")
        total_pois = result[0]['count'] if result else 0
    except Exception as e:
        print(f"Error counting POIs: {e}")
    
    # Count stations and bikes in MongoDB
    total_stations = 0
    total_bikes = 0
    try:
        total_stations = mongo_db.db.bike_stations.count_documents({})
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$bikes_available"}}}
        ]
        result = mongo_db.aggregate('bike_stations', pipeline)
        total_bikes = result[0]['total'] if result else 0
    except Exception as e:
        print(f"Error counting bikes: {e}")
    
    return Stats(
        total_pois=total_pois,
        total_stations=total_stations,
        total_bikes_available=total_bikes,
        cache_hit_rate=None  # Could be calculated if Redis tracking is implemented
    )


# ============================================================================
# City Data Endpoints (MySQL)
# ============================================================================

@app.get(
    "/api/city/pois",
    response_model=List[POI],
    tags=["City Data"],
    summary="List all Points of Interest",
    description="Retrieve all POIs from MySQL database. Results are cached in Redis for 5 minutes."
)
async def list_pois(
    poi_type: Optional[str] = Query(None, description="Filter by POI type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    List all Points of Interest with optional filtering.
    
    This endpoint demonstrates:
    - SQL query execution with mysql-connector-python
    - Redis caching for performance
    - Query parameters for filtering
    
    Args:
        poi_type: Optional filter by type
        limit: Maximum results to return
    
    Returns:
        List[POI]: List of points of interest
    """
    # Try cache first
    cache_key = f"pois:type:{poi_type}:limit:{limit}"
    cached = redis_cache.get(cache_key)
    if cached:
        return cached
    
    # Query MySQL
    try:
        if poi_type:
            query = "SELECT * FROM points_of_interest WHERE type = %s LIMIT %s"
            results = mysql_db.execute_query(query, (poi_type, limit))
        else:
            query = "SELECT * FROM points_of_interest LIMIT %s"
            results = mysql_db.execute_query(query, (limit,))
        
        pois = [POI(**row) for row in results]
        
        # Cache results for 5 minutes
        redis_cache.set(cache_key, [poi.model_dump() for poi in pois], ttl=300)
        
        return pois
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/api/city/pois/{poi_id}",
    response_model=POI,
    tags=["City Data"],
    summary="Get a specific POI",
    description="Retrieve a single POI by its ID"
)
async def get_poi(poi_id: int):
    """
    Get a specific Point of Interest by ID.
    
    Args:
        poi_id: The POI database ID
    
    Returns:
        POI: The requested point of interest
    
    Raises:
        HTTPException: 404 if POI not found
    """
    try:
        query = "SELECT * FROM points_of_interest WHERE id = %s"
        results = mysql_db.execute_query(query, (poi_id,))
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"POI with id {poi_id} not found"
            )
        
        return POI(**results[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/api/city/pois",
    response_model=POI,
    status_code=status.HTTP_201_CREATED,
    tags=["City Data"],
    summary="Create a new POI",
    description="Create a new Point of Interest in MySQL database"
)
async def create_poi(poi: POICreate):
    """
    Create a new Point of Interest.
    
    This endpoint demonstrates:
    - POST request handling
    - SQL INSERT with parameterized queries (prevents SQL injection)
    - Returning created resource with 201 status
    - Cache invalidation after write
    
    Args:
        poi: POI data to create
    
    Returns:
        POI: The created point of interest with assigned ID
    """
    try:
        # Insert the new POI
        insert_query = """
            INSERT INTO points_of_interest (name, type, latitude, longitude, description)
            VALUES (%s, %s, %s, %s, %s)
        """
        mysql_db.execute_query(
            insert_query,
            (poi.name, poi.type, poi.latitude, poi.longitude, poi.description),
            fetch=False
        )

        # Get the inserted POI using LAST_INSERT_ID()
        select_query = """
            SELECT id, name, type, latitude, longitude, description
            FROM points_of_interest
            WHERE id = LAST_INSERT_ID()
        """
        result = mysql_db.execute_query(select_query)

        # Invalidate related caches
        redis_cache.clear_pattern("pois:*")

        return POI(**result[0])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/api/city/search",
    response_model=List[POI],
    tags=["City Data"],
    summary="Search POIs",
    description="Search for POIs by name or type"
)
async def search_pois(
    q: str = Query(..., min_length=1, description="Search query"),
    search_field: str = Query("name", regex="^(name|type)$", description="Field to search in")
):
    """
    Search for Points of Interest.
    
    This endpoint demonstrates:
    - Full-text search with SQL LIKE
    - Query parameter validation
    - Dynamic query building
    
    Args:
        q: Search query string
        search_field: Field to search ('name' or 'type')
    
    Returns:
        List[POI]: Matching points of interest
    """
    try:
        # MySQL uses LIKE (case-insensitive by default with utf8mb4_general_ci collation)
        query = f"SELECT * FROM points_of_interest WHERE {search_field} LIKE %s LIMIT 50"
        results = mysql_db.execute_query(query, (f"%{q}%",))
        return [POI(**row) for row in results]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# ============================================================================
# Bike Sharing Endpoints (MongoDB)
# ============================================================================

@app.get(
    "/api/bikes/stations",
    response_model=List[BikeStation],
    tags=["Bike Sharing"],
    summary="List all bike stations",
    description="Retrieve all bike stations from MongoDB. Results are cached in Redis for 1 minute."
)
async def list_bike_stations(
    min_bikes: int = Query(0, ge=0, description="Minimum bikes available"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results")
):
    """
    List all bike sharing stations.
    
    This endpoint demonstrates:
    - MongoDB query with pymongo
    - Redis caching with short TTL (1 minute) for dynamic data
    - Query filtering
    
    Args:
        min_bikes: Filter stations with at least this many bikes
        limit: Maximum results to return
    
    Returns:
        List[BikeStation]: List of bike stations
    """
    # Try cache first (short TTL for dynamic data)
    cache_key = f"bikes:stations:min:{min_bikes}:limit:{limit}"
    cached = redis_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        query = {"bikes_available": {"$gte": min_bikes}}
        stations = mongo_db.find_many('bike_stations', query, limit=limit)
        
        # Cache for 1 minute (bike availability changes frequently)
        redis_cache.set(cache_key, stations, ttl=60)
        
        return [BikeStation(**station) for station in stations]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/api/bikes/stations/{station_id}",
    response_model=BikeStation,
    tags=["Bike Sharing"],
    summary="Get a specific bike station",
    description="Retrieve a single bike station by its ID"
)
async def get_bike_station(station_id: str):
    """
    Get a specific bike station by ID.
    
    Args:
        station_id: The station ID
    
    Returns:
        BikeStation: The requested bike station
    
    Raises:
        HTTPException: 404 if station not found
    """
    try:
        station = mongo_db.find_one('bike_stations', {'station_id': station_id})
        
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station {station_id} not found"
            )
        
        return BikeStation(**station)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/api/bikes/stations",
    response_model=BikeStation,
    status_code=status.HTTP_201_CREATED,
    tags=["Bike Sharing"],
    summary="Create a new bike station",
    description="Create a new bike station in MongoDB"
)
async def create_bike_station(station: BikeStationCreate):
    """
    Create a new bike station.
    
    This endpoint demonstrates:
    - MongoDB document insertion with pymongo
    - Upsert operation (update if exists, insert if not)
    - Handling MongoDB ObjectId
    
    Args:
        station: Station data to create
    
    Returns:
        BikeStation: The created/updated bike station
    """
    try:
        station_doc = station.model_dump()
        station_doc['last_updated'] = datetime.now()
        
        # Use upsert to update if exists
        result = mongo_db.db.bike_stations.update_one(
            {'station_id': station.station_id},
            {'$set': station_doc},
            upsert=True
        )
        
        # Invalidate caches
        redis_cache.clear_pattern("bikes:*")
        
        # Fetch and return the created/updated station
        created_station = mongo_db.find_one('bike_stations', {'station_id': station.station_id})
        return BikeStation(**created_station)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/api/bikes/stations/{station_id}/history",
    response_model=List[BikeStationHistory],
    tags=["Bike Sharing"],
    summary="Get station availability history",
    description="Retrieve historical bike availability data for a station (simulated from current snapshot)"
)
async def get_station_history(
    station_id: str,
    limit: int = Query(10, ge=1, le=100, description="Number of historical records")
):
    """
    Get bike availability history for a station.
    
    Note: In this example, we simulate history from the current snapshot.
    In a production system, you would store historical snapshots in a separate collection.
    
    Args:
        station_id: The station ID
        limit: Number of records to return
    
    Returns:
        List[BikeStationHistory]: Historical availability data
    """
    try:
        station = mongo_db.find_one('bike_stations', {'station_id': station_id})
        
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station {station_id} not found"
            )
        
        # Simulate history (in production, query a time-series collection)
        history = [
            BikeStationHistory(
                timestamp=station['last_updated'],
                bikes_available=station['bikes_available'],
                capacity=station.get('capacity')
            )
        ]
        
        return history
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get(
    "/",
    tags=["System"],
    summary="API information",
    description="Get basic information about the API"
)
async def root():
    """
    Root endpoint providing API information and links.
    
    Returns:
        dict: API metadata and useful links
    """
    return {
        "name": "Kiel City Data Platform API",
        "version": "1.0.0",
        "description": "Cloud computing orchestration example with MySQL, MongoDB, and Redis",
        "documentation": "/docs",
        "health_check": "/health",
        "stats": "/api/stats",
        "learning_focus": [
            "MySQL SDK (mysql-connector-python)",
            "MongoDB SDK (pymongo)",
            "Redis caching",
            "FastAPI framework",
            "Docker Compose orchestration",
            "Swagger documentation"
        ]
    }


# Application startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    print("🚀 Kiel City Data Platform API starting up...")
    print("📚 Documentation available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    print("👋 Shutting down API...")
    mysql_db.close()
    mongo_db.close()
