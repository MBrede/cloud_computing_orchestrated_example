# System Architecture Documentation

## Overview

The Kiel City Data Platform is a microservices-based application demonstrating cloud computing orchestration with Docker Compose. It integrates multiple database systems, caching, and provides both API and visual interfaces.

## Architecture Diagram

```
                                    ┌─────────────────────────┐
                                    │   User / Developer      │
                                    └───────────┬─────────────┘
                                                │
                         ┌──────────────────────┼──────────────────────┐
                         │                      │                      │
                         ▼                      ▼                      ▼
              ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
              │   Dashboard      │   │   Swagger UI     │   │   Direct API     │
              │   (Streamlit)    │   │   /docs          │   │   Access         │
              │   Port 8501      │   │                  │   │                  │
              └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
                       │                      │                      │
                       └──────────────────────┼──────────────────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │   FastAPI Backend  │
                                    │   Port 8000        │
                                    │   - REST Endpoints │
                                    │   - Request Valid. │
                                    │   - Auth (future)  │
                                    └─────────┬──────────┘
                                              │
                       ┌──────────────────────┼──────────────────────┐
                       │                      │                      │
                       ▼                      ▼                      ▼
            ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
            │   MySQL          │   │   MongoDB        │   │   Redis          │
            │   Port 3306      │   │   Port 27017     │   │   Port 6379      │
            │   - Population Data     │   │   - Bike Data    │   │   - Caching      │
            │   - Structured   │   │   - Time-Series  │   │   - Session Mgmt │
            └──────────────────┘   └────────┬─────────┘   └──────────────────┘
                       ▲                      ▲
                       │                      │
                       │            ┌─────────▼──────────┐
            ┌──────────┴─────────┐  │   Cron Job         │
            │   Data Loader      │  │   - DonkeyRepublic │
            │   - Init Script    │  │   - Every 5 min    │
            │   - Runs Once      │  │   - Data Sync      │
            └────────────────────┘  └────────────────────┘
```

## Component Details

### 1. Frontend Layer

#### Streamlit Dashboard (dashboard/)
- **Purpose**: Interactive web interface for data visualization
- **Technology**: Streamlit with Folium for maps
- **Port**: 8501
- **Features**:
  - Interactive map of Kiel with population Data
  - Real-time bike station availability
  - Data filtering and statistics
  - Auto-refresh capability

### 2. Application Layer

#### FastAPI Backend (api/)
- **Purpose**: RESTful API for data access and manipulation
- **Technology**: FastAPI with Pydantic validation
- **Port**: 8000
- **Key Files**:
  - `main.py`: API endpoints and routing
  - `models.py`: Pydantic data models
  - `database.py`: Database SDK implementations
- **Features**:
  - Automatic OpenAPI/Swagger documentation
  - Request/response validation
  - Redis caching for performance
  - Error handling with proper HTTP status codes

### 3. Data Layer

#### MySQL (mysql)
- **Purpose**: Relational database for structured population data
- **Use Case**: Static or slowly-changing data (POIs)
- **SDK**: mysql-connector-python with connection pooling


#### MongoDB (mongodb)
- **Purpose**: NoSQL database for "time-series" bike data
- **Use Case**: Frequently-changing data with flexible schema
- **SDK**: pymongo
- **Collections**:
  - `bike_stations`: Current bike availability
  - Future: `bike_history`: Historical snapshots

#### Redis (redis)
- **Purpose**: In-memory cache for API responses
- **Use Case**: Reduce database load, improve response times
- **SDK**: redis-py
- **Strategy**:
  - POI data: 5-minute TTL
  - Bike data: 1-minute TTL (more dynamic)

### 4. Worker Services

#### Data Loader (data-loader/)
- **Purpose**: Initialize MySQL with Kiel population data
- **Lifecycle**: Runs once at startup, then exits
- **Process**:
  1. Wait for MySQL to be ready
  2. Create database schema
  3. Insert population data
  4. Verify data integrity
  5. Exit

#### Cron Job (cron-job/)
- **Purpose**: Periodically fetch bike data from DonkeyRepublic
- **Schedule**: Every 5 minutes
- **Process**:
  1. Fetch data from DonkeyRepublic API
  2. Parse and normalize response
  3. Upsert to MongoDB
  4. Log results

## Data Flow

### 1. Initial Startup
```
docker-compose up
  └─> Start MySQL, MongoDB, Redis
      └─> Run data-loader (waits for MySQL)
          └─> Populate POI data
              └─> Start API (waits for all DBs + data-loader)
                  └─> Start Dashboard (waits for API)
                  └─> Start Cron Job (waits for MongoDB)
                      └─> Fetch initial bike data
```

### 2. API Request Flow (with caching)
```
User/Dashboard → API Endpoint
                   ├─> Check Redis cache
                   │   ├─> Cache hit: Return cached data
                   │   └─> Cache miss: Query database
                   │       └─> Store in Redis with TTL
                   └─> Return response
```

### 3. Data Update Flow
```
DonkeyRepublic API → Cron Job (every 5 min)
                       └─> Parse bike data
                           └─> Upsert to MongoDB
                               └─> Invalidate Redis cache
                                   └─> Next API request fetches fresh data
```

## Network Architecture

All services run in a custom Docker bridge network (`kiel-network`):
- Internal DNS resolution (services accessible by name)
- Isolated from host network
- Only API and Dashboard exposed to host via port mapping

## Security Considerations

1. **Environment Variables**: All credentials in `.env` file
2. **No Hardcoded Secrets**: Use environment variables everywhere
3. **Network Isolation**: Internal services not exposed to host
4. **Database Authentication**: All databases require authentication
5. **Parameterized Queries**: Prevent SQL injection
6. **Input Validation**: Pydantic models validate all API inputs

## Monitoring and Health Checks

Each service has health checks:
- **MySQL**: `mysqladmin ping`
- **MongoDB**: `mongosh ping`
- **Redis**: `redis-cli ping`
- **API**: HTTP GET `/health`

Docker Compose dependency management:
```yaml
depends_on:
  mysql:
    condition: service_healthy  # Wait for health check
  data-loader:
    condition: service_completed_successfully  # Wait for exit
```