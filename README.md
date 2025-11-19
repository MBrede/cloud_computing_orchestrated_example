# Kiel City Data Platform - Cloud Computing Orchestration Example

A comprehensive example of an orchestrated cloud computing application showcasing API development, multiple database systems, caching, and data visualization.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kiel City Data Platform                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Streamlit      │      │    FastAPI       │      │   Cron Job       │
│   Dashboard      │─────▶│    Backend       │      │   (Bike Sync)    │
│   Port: 8501     │      │    Port: 8000    │      │   Every 5 min    │
└──────────────────┘      └──────────────────┘      └──────────────────┘
                                   │                          │
                    ┌──────────────┼──────────────┬──────────┘
                    │              │              │
                    ▼              ▼              ▼
          ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
          │   Redis     │  │ MySQL  │  │   MongoDB   │
          │   Cache     │  │  Kiel Data  │  │  Bike Data  │
          │  Port: 6379 │  │ Port: 3306  │  │ Port: 27017 │
          └─────────────┘  └─────────────┘  └─────────────┘
                                   ▲
                                   │
                          ┌────────────────┐
                          │  Data Loader   │
                          │  (Init Script) │
                          └────────────────┘
```

## 📋 Features & Rubric Coverage

### Mandatory Requirements ✅

- **API Implementation (10 points)**
  - FastAPI with POST endpoints (create bike station, add city POI)
  - FastAPI with GET endpoints (list stations, get city data, search)
  - Full CRUD operations

- **Documentation (5 points)**
  - Interactive Swagger UI at `http://localhost:8000/docs`
  - Comprehensive code documentation with docstrings
  - This README with setup instructions

- **Database (5 points)**
  - MySQL for structured city data
  - MongoDB for bike-sharing time-series data
  - Redis for caching frequently accessed data

- **Data Processing Client (10 points - BONUS)**
  - Interactive Streamlit dashboard
  - Map visualization of Kiel with data overlays
  - Real-time bike availability display

- **Container Deployment (5 points)**
  - Docker Compose orchestration
  - 6 separate containers working together
  - Automated initialization and cron jobs

### Bonus Features 🌟

- **Pydantic Data Classes (~5 points)**: Type-safe API models
- **Security Best Practices (~5 points)**: `.env` file, no hardcoded secrets
- **Additional Endpoints (~10 points)**: Batch operations, search, filtering
- **NoSQL with Good Reason (~15 points)**: MongoDB for time-series bike data
- **Redis Caching (~5 points)**: Performance optimization
- **Multiple Database SDKs**: mysql-connector-python (SQL) and pymongo (MongoDB) examples

**Total Points: 30 base + 40 bonus = 70 points (before presentation)**

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Internet connection (for fetching bike data)

### Running the System

1. **Clone and navigate to the project**:
   ```bash
   cd cloud_computing_orchestrated_example
   ```

2. **Copy environment template**:
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults work out of the box)
   ```

3. **Start all services**:
   ```bash
   docker-compose up --build
   ```

4. **Wait for initialization** (~30 seconds):
   - MySQL will be populated with Kiel city data
   - MongoDB will start collecting bike-sharing data
   - All services will become available

5. **Access the applications**:
   - **Dashboard**: http://localhost:8501
   - **API Documentation**: http://localhost:8000/docs
   - **API Base**: http://localhost:8000

### Stopping the System

```bash
docker-compose down
```

To remove all data volumes:
```bash
docker-compose down -v
```

## 📚 API Documentation

### Endpoints Overview

#### City Data (MySQL)

- `GET /api/city/pois` - List all points of interest
- `GET /api/city/pois/{poi_id}` - Get specific POI
- `POST /api/city/pois` - Create new POI
- `GET /api/city/search` - Search POIs by name or type

#### Bike Sharing (MongoDB)

- `GET /api/bikes/stations` - List all bike stations (cached)
- `GET /api/bikes/stations/{station_id}` - Get specific station
- `GET /api/bikes/stations/{station_id}/history` - Get availability history
- `POST /api/bikes/stations` - Create new bike station

#### Health & Info

- `GET /health` - System health check
- `GET /api/stats` - Database statistics

### Example API Usage

**Get all POIs with caching**:
```bash
curl http://localhost:8000/api/city/pois
```

**Create a new POI**:
```bash
curl -X POST http://localhost:8000/api/city/pois \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kiel Harbor",
    "type": "landmark",
    "latitude": 54.3233,
    "longitude": 10.1394,
    "description": "Beautiful harbor area"
  }'
```

**Get bike stations**:
```bash
curl http://localhost:8000/api/bikes/stations
```

## 🗄️ Database Details

### MySQL - City Data

**Schema**: Structured relational data
- Table: `points_of_interest`
- Columns: id, name, type, latitude, longitude, description
- Use case: Static city infrastructure data

**SDK Example**: `mysql-connector-python` with connection pooling

### MongoDB - Bike Sharing

**Schema**: Time-series documents
- Collection: `bike_stations`
- Documents: station info with availability snapshots
- Use case: Dynamic data that changes frequently

**SDK Example**: `pymongo` with async capabilities

### Redis - Caching

- Cache for frequently accessed endpoints
- TTL: 60 seconds for bike data, 300 seconds for city data
- Automatic invalidation

## 🔧 Project Structure

```
.
├── api/                    # FastAPI application
│   ├── main.py            # API entry point
│   ├── models.py          # Pydantic models
│   ├── database.py        # Database connections
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile
├── dashboard/             # Streamlit visualization
│   ├── app.py            # Dashboard code
│   ├── requirements.txt
│   └── Dockerfile
├── data-loader/          # MySQL initialization
│   ├── load_kiel_data.py
│   ├── requirements.txt
│   └── Dockerfile
├── cron-job/             # Bike data sync
│   ├── fetch_bikes.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── crontab
├── docker-compose.yml    # Orchestration
├── .env.example          # Environment template
└── README.md
```

## 🔒 Security Best Practices

1. **Environment Variables**: All credentials in `.env` file
2. **No Hardcoded Secrets**: Database passwords externalized
3. **Network Isolation**: Docker internal network
4. **Health Checks**: All containers monitored
5. **Least Privilege**: Service-specific database users

## ⚡ Performance Optimizations

### Fast Package Installation with uv

All Docker containers use [uv](https://github.com/astral-sh/uv) instead of pip for package installation:

- **10-100x faster** than pip for package installation
- **Written in Rust** for maximum performance
- **Drop-in replacement** for pip install
- **Production-ready** from the Astral team (creators of Ruff)

Example from `api/Dockerfile`:
```dockerfile
# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies using uv (much faster than pip)
RUN uv pip install --system --no-cache -r requirements.txt
```

Benefits:
- Faster container builds (especially during development)
- Reduced CI/CD pipeline times
- Same requirements.txt format as pip

## 📊 Dashboard Features

The Streamlit dashboard provides:

1. **Interactive Map of Kiel**
   - Points of Interest markers
   - Bike station locations
   - Real-time bike availability

2. **Data Filters**
   - Filter by POI type
   - Filter by bike availability
   - Time-based historical data

3. **Statistics**
   - Total stations and bikes
   - Database record counts
   - System health status

## 🎓 Learning Objectives

This example demonstrates:

1. **Database SDK Usage**:
   - SQL operations with mysql-connector-python
   - NoSQL operations with pymongo
   - Connection management and pooling

2. **API Development**:
   - RESTful design patterns
   - Request/response validation
   - Auto-generated documentation

3. **Containerization**:
   - Multi-container orchestration
   - Service dependencies
   - Volume management

4. **Caching Strategies**:
   - Redis integration
   - Cache invalidation
   - Performance optimization

## 🐛 Troubleshooting

### Services won't start

```bash
# Check if ports are already in use
lsof -i :8000  # API
lsof -i :8501  # Dashboard
lsof -i :3306  # MySQL
lsof -i :27017 # MongoDB

# View logs
docker-compose logs -f [service-name]
```

### Database connection errors

```bash
# Ensure databases are healthy
docker-compose ps

# Restart specific service
docker-compose restart api
```

### No bike data appearing

```bash
# Check cron job logs
docker-compose logs cron-job

# Manually trigger sync
docker-compose exec cron-job python /app/fetch_bikes.py
```

## 📝 License

Educational example for Cloud Computing course.

## 🤝 Contributing

This is an example project for educational purposes. Feel free to fork and extend!

## 📧 Questions?

Check the Swagger documentation at http://localhost:8000/docs for interactive API exploration.
