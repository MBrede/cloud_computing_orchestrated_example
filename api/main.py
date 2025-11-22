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
    Stadtteil, DemographicData, PopulationByAge,
    BikeStation, BikeStationCreate, BikeStationHistory,
    HealthCheck, Stats, ErrorResponse
)
from database import mysql_db, mongo_db, redis_cache

description = """
# Kiel City Data Platform API

A comprehensive API demonstrating cloud computing concepts with multiple database systems.

## Features

- **MySQL Integration**: Structured demographic data (Stadtteile/Districts)
- **MongoDB Integration**: Time-series bike sharing data
- **Redis Caching**: Performance optimization for frequently accessed data
- **Demographic Data API**: Population statistics by age, gender, and district
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
"""

# Initialize FastAPI app with metadata for Swagger documentation
app = FastAPI(
    title=os.getenv('API_TITLE', 'Kiel City Data Platform'),
    version=os.getenv('API_VERSION', '1.0.0'),
    description=description,
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
    # Count Stadtteile and total population in MySQL
    total_stadtteile = 0
    total_population = 0
    try:
        result = mysql_db.execute_query("SELECT COUNT(*) as count FROM stadtteile")
        total_stadtteile = result[0]['count'] if result else 0

        pop_result = mysql_db.execute_query("SELECT SUM(total) as total FROM population_by_gender")
        total_population = pop_result[0]['total'] if pop_result and pop_result[0]['total'] else 0
    except Exception as e:
        print(f"Error counting districts: {e}")
    
    # Count stations and bikes in MongoDB
    total_stations = 0
    total_bikes = 0
    try:
        total_stations = mongo_db.db.bike_stations.count_documents({})
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$bikes_available"},
                        "total_cargo": {"$sum": "$cargo_bikes_available"}}}
        ]
        result = mongo_db.aggregate('bike_stations', pipeline)
        total_bikes = result[0]['total'] if result else 0
        total_cargo_bikes = result[0]['total_cargo'] if result else 0
    except Exception as e:
        print(f"Error counting bikes: {e}")
    
    return Stats(
        total_stadtteile=total_stadtteile,
        total_population=total_population,
        total_stations=total_stations,
        total_bikes_available=total_bikes,
        total_cargo_bikes_available=total_cargo_bikes,
        cache_hit_rate=None  # Could be calculated if Redis tracking is implemented
    )


# ============================================================================
# Demographic Data Endpoints (MySQL)
# ============================================================================

@app.get(
    "/api/stadtteile",
    response_model=List[Stadtteil],
    tags=["Demographics"],
    summary="List all Stadtteile (districts)",
    description="Retrieve all districts from MySQL database. Results are cached in Redis for 5 minutes."
)
async def list_stadtteile():
    """
    List all Stadtteile (districts) in Kiel.

    This endpoint demonstrates:
    - SQL query execution with mysql-connector-python
    - Redis caching for performance
    - Returning structured district data with coordinates

    Returns:
        List[Stadtteil]: List of districts
    """
    # Try cache first
    cache_key = "stadtteile:all"
    cached = redis_cache.get(cache_key)
    if cached:
        return cached

    # Query MySQL
    try:
        query = "SELECT stadtteil_nr, name, latitude, longitude FROM stadtteile ORDER BY stadtteil_nr"
        results = mysql_db.execute_query(query)

        stadtteile = [Stadtteil(**row) for row in results]

        # Cache results for 5 minutes
        redis_cache.set(cache_key, [s.model_dump() for s in stadtteile], ttl=300)

        return stadtteile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/api/stadtteile/{stadtteil_nr}",
    response_model=DemographicData,
    tags=["Demographics"],
    summary="Get demographic data for a specific Stadtteil",
    description="Retrieve comprehensive demographic information for a district"
)
async def get_stadtteil_demographics(stadtteil_nr: int):
    """
    Get comprehensive demographic data for a specific Stadtteil.

    This endpoint demonstrates:
    - Complex SQL queries joining multiple tables
    - Aggregating demographic data
    - Structured response with nested data

    Args:
        stadtteil_nr: The district number

    Returns:
        DemographicData: Complete demographic information

    Raises:
        HTTPException: 404 if district not found
    """
    # Try cache first
    cache_key = f"stadtteil:demographics:{stadtteil_nr}"
    cached = redis_cache.get(cache_key)
    if cached:
        return DemographicData(**cached)

    try:
        # Get basic Stadtteil info
        stadtteil_query = "SELECT stadtteil_nr, name, latitude, longitude FROM stadtteile WHERE stadtteil_nr = %s"
        stadtteil_result = mysql_db.execute_query(stadtteil_query, (stadtteil_nr,))

        if not stadtteil_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stadtteil with number {stadtteil_nr} not found"
            )

        stadtteil = stadtteil_result[0]

        # Get population by gender (latest date)
        gender_query = """
            SELECT total, male, female
            FROM population_by_gender
            WHERE stadtteil_nr = %s
            ORDER BY datum DESC
            LIMIT 1
        """
        gender_result = mysql_db.execute_query(gender_query, (stadtteil_nr,))

        total_pop = gender_result[0]['total'] if gender_result else 0
        male_pop = gender_result[0]['male'] if gender_result else 0
        female_pop = gender_result[0]['female'] if gender_result else 0

        # Get age distribution (latest date)
        age_query = """
            SELECT age_group, count
            FROM population_by_age
            WHERE stadtteil_nr = %s
            AND datum = (SELECT MAX(datum) FROM population_by_age WHERE stadtteil_nr = %s)
            ORDER BY age_group
        """
        age_results = mysql_db.execute_query(age_query, (stadtteil_nr, stadtteil_nr))
        age_distribution = [PopulationByAge(age_group=row['age_group'], count=row['count']) for row in age_results]

        demographic_data = DemographicData(
            stadtteil_nr=stadtteil['stadtteil_nr'],
            name=stadtteil['name'],
            total_population=total_pop,
            male=male_pop,
            female=female_pop,
            age_distribution=age_distribution if age_results else None,
            latitude=stadtteil.get('latitude'),
            longitude=stadtteil.get('longitude')
        )

        # Cache for 5 minutes
        redis_cache.set(cache_key, demographic_data.model_dump(), ttl=300)

        return demographic_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/api/stadtteile/{stadtteil_nr}/population",
    tags=["Demographics"],
    summary="Get population summary for a Stadtteil",
    description="Retrieve population count by gender for a specific district"
)
async def get_stadtteil_population(stadtteil_nr: int):
    """
    Get population summary for a Stadtteil.

    Args:
        stadtteil_nr: The district number

    Returns:
        dict: Population summary with total, male, and female counts
    """
    try:
        query = """
            SELECT s.stadtteil_nr, s.name, p.total, p.male, p.female, p.datum
            FROM stadtteile s
            LEFT JOIN population_by_gender p ON s.stadtteil_nr = p.stadtteil_nr
            WHERE s.stadtteil_nr = %s
            ORDER BY p.datum DESC
            LIMIT 1
        """
        result = mysql_db.execute_query(query, (stadtteil_nr,))

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stadtteil with number {stadtteil_nr} not found"
            )

        return result[0]
    except HTTPException:
        raise
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
    min_cargo_bikes: int = Query(0, ge=0, description="Minimum cargo bikes available"),
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
    cache_key = f"bikes:stations:min:{min_bikes}:min_cargo:{min_cargo_bikes}:limit:{limit}"
    cached = redis_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        query = {"bikes_available": {"$gte": min_bikes},
                 "cargo_bikes_available": {"$gte": min_cargo_bikes}}
        stations = mongo_db.find_many('bike_stations', query, limit=limit)

        # Convert MongoDB documents to BikeStation models
        # Handle string lat/lon and convert _id ObjectId to string
        result = []
        for station in stations:
            # Convert _id ObjectId to string
            station['_id'] = str(station['_id'])
            # Convert string lat/lon to float
            station['latitude'] = float(station['latitude'])
            station['longitude'] = float(station['longitude'])
            # Remove extra fields not in model
            station.pop('location', None)

            result.append(BikeStation(**station))

        # Cache the result models (they're now JSON-serializable)
        redis_cache.set(cache_key, [s.model_dump() for s in result], ttl=60)

        return result
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
