"""
Pydantic models for API request/response validation.

This module demonstrates best practices for API data validation using Pydantic.
All models include proper type hints, constraints, and documentation.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class POIBase(BaseModel):
    """Base model for Point of Interest data."""
    name: str = Field(..., min_length=1, max_length=200, description="Name of the point of interest")
    type: str = Field(..., min_length=1, max_length=50, description="Type of POI (e.g., museum, park, restaurant)")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    description: Optional[str] = Field(None, max_length=1000, description="Detailed description")


class POICreate(POIBase):
    """Model for creating a new POI (POST request)."""
    pass


class POI(POIBase):
    """Model for POI response (includes database ID)."""
    id: int = Field(..., description="Unique identifier from database")
    
    model_config = ConfigDict(from_attributes=True)


class BikeStationBase(BaseModel):
    """Base model for bike sharing station data."""
    station_id: str = Field(..., description="External station ID from DonkeyRepublic")
    name: str = Field(..., min_length=1, max_length=200, description="Station name")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    bikes_available: int = Field(..., ge=0, description="Number of bikes currently available")
    capacity: Optional[int] = Field(None, ge=0, description="Total capacity of the station")


class BikeStationCreate(BikeStationBase):
    """Model for creating a new bike station (POST request)."""
    pass


class BikeStation(BikeStationBase):
    """Model for bike station response (includes MongoDB _id as string)."""
    id: str = Field(..., alias="_id", description="MongoDB ObjectId as string")
    last_updated: datetime = Field(..., description="Last time station data was updated")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BikeStationHistory(BaseModel):
    """Model for historical bike availability data."""
    timestamp: datetime = Field(..., description="Time of the snapshot")
    bikes_available: int = Field(..., ge=0, description="Bikes available at that time")
    capacity: Optional[int] = Field(None, ge=0, description="Station capacity")


class HealthCheck(BaseModel):
    """Model for health check response."""
    status: str = Field(..., description="Overall system status")
    postgres: bool = Field(..., description="MySQL connection status")
    mongodb: bool = Field(..., description="MongoDB connection status")
    redis: bool = Field(..., description="Redis connection status")
    timestamp: datetime = Field(..., description="Time of health check")


class Stats(BaseModel):
    """Model for database statistics."""
    total_pois: int = Field(..., description="Total points of interest in MySQL")
    total_stations: int = Field(..., description="Total bike stations in MongoDB")
    total_bikes_available: int = Field(..., description="Total bikes currently available")
    cache_hit_rate: Optional[float] = Field(None, description="Redis cache hit rate")


class ErrorResponse(BaseModel):
    """Model for error responses."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Optional error code")
