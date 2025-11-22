"""
Pydantic models for API request/response validation.

This module demonstrates best practices for API data validation using Pydantic.
All models include proper type hints, constraints, and documentation.
"""

from typing import Optional, List, Dict
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict


class Stadtteil(BaseModel):
    """Model for Stadtteil (district) data."""
    stadtteil_nr: int = Field(..., description="District number")
    name: str = Field(..., description="District name")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")

    model_config = ConfigDict(from_attributes=True)


class PopulationByGender(BaseModel):
    """Model for population by gender data."""
    stadtteil_nr: int = Field(..., description="District number")
    datum: date = Field(..., description="Date of data")
    total: int = Field(..., description="Total population")
    male: int = Field(..., description="Male population")
    female: int = Field(..., description="Female population")


class PopulationByAge(BaseModel):
    """Model for population by age group data."""
    age_group: str = Field(..., description="Age group range")
    count: int = Field(..., description="Population count in this age group")


class DemographicData(BaseModel):
    """Model for comprehensive demographic data of a Stadtteil."""
    stadtteil_nr: int = Field(..., description="District number")
    name: str = Field(..., description="District name")
    total_population: int = Field(..., description="Total population")
    male: int = Field(..., description="Male population")
    female: int = Field(..., description="Female population")
    age_distribution: Optional[List[PopulationByAge]] = Field(None, description="Age distribution")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


class BikeStationBase(BaseModel):
    """Base model for bike sharing station data."""
    station_id: str = Field(..., description="External station ID from DonkeyRepublic")
    name: str = Field(..., min_length=1, max_length=200, description="Station name")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    bikes_available: int = Field(..., ge=0, description="Number of bikes currently available")
    cargo_bikes_available: int = Field(..., ge=0, description="Number of cargo bikes currently available")
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
    mysql: bool = Field(..., description="MySQL connection status")
    mongodb: bool = Field(..., description="MongoDB connection status")
    redis: bool = Field(..., description="Redis connection status")
    timestamp: datetime = Field(..., description="Time of health check")


class Stats(BaseModel):
    """Model for database statistics."""
    total_stadtteile: int = Field(..., description="Total districts in MySQL")
    total_population: int = Field(..., description="Total population across all districts")
    total_stations: int = Field(..., description="Total bike stations in MongoDB")
    total_bikes_available: int = Field(..., description="Total bikes currently available")
    total_cargo_bikes_available: int = Field(..., description="Total cargo bikes currently available")
    cache_hit_rate: Optional[float] = Field(None, description="Redis cache hit rate")


class ErrorResponse(BaseModel):
    """Model for error responses."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Optional error code")
