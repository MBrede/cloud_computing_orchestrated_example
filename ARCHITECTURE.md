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
            │   - POI Data     │   │   - Bike Data    │   │   - Caching      │
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
  - Interactive map of Kiel with POI markers
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
- **Purpose**: Relational database for structured city data
- **Use Case**: Static or slowly-changing data (POIs)
- **SDK**: mysql-connector-python with connection pooling
- **Schema**:
  ```sql
  CREATE TABLE points_of_interest (
      id SERIAL PRIMARY KEY,
      name VARCHAR(200) NOT NULL,
      type VARCHAR(50) NOT NULL,
      latitude DOUBLE PRECISION NOT NULL,
      longitude DOUBLE PRECISION NOT NULL,
      description TEXT
  );
  ```

#### MongoDB (mongodb)
- **Purpose**: NoSQL database for time-series bike data
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
- **Purpose**: Initialize MySQL with Kiel POI data
- **Lifecycle**: Runs once at startup, then exits
- **Process**:
  1. Wait for MySQL to be ready
  2. Create database schema
  3. Insert 30+ Kiel POIs
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

## Database SDK Examples

### MySQL (mysql-connector-python)

**Connection Pooling:**
```python
pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name='kiel_pool',
    pool_size=10,
    host='mysql', database='kiel_data',
    user='kiel_user', password='***'
)
```

**Parameterized Query (防止 SQL injection):**
```python
cursor.execute(
    "SELECT * FROM points_of_interest WHERE type = %s",
    ('museum',)
)
```

**Batch Insert:**
```python
cursor.executemany(
    "INSERT INTO points_of_interest (name, type, lat, lon) VALUES (%s, %s, %s, %s)",
    [('Museum', 'culture', 54.32, 10.13), ...]
)
```

### MongoDB (pymongo)

**Connection:**
```python
client = MongoClient(
    f"mongodb://{user}:{password}@{host}:{port}/{db}?authSource=admin"
)
db = client[db_name]
```

**Upsert (update or insert):**
```python
db.bike_stations.update_one(
    {'station_id': 'KIEL001'},
    {'$set': station_data},
    upsert=True
)
```

**Aggregation:**
```python
result = db.bike_stations.aggregate([
    {'$group': {'_id': None, 'total': {'$sum': '$bikes_available'}}}
])
```

### Redis (redis-py)

**Set with TTL:**
```python
redis_client.setex(
    'pois:all',
    300,  # 5 minutes
    json.dumps(poi_data)
)
```

**Get and deserialize:**
```python
cached = redis_client.get('pois:all')
if cached:
    data = json.loads(cached)
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

## Scalability Considerations

### Current Limitations
- Single instance per service
- In-memory cache (Redis) on single node
- No load balancing

### Future Enhancements
- Horizontal scaling with Docker Swarm or Kubernetes
- Distributed Redis cluster
- Database read replicas
- API load balancer
- Message queue for async tasks

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

## Development vs Production

### Development (Current)
- Single `.env` file
- Volumes for data persistence
- Auto-reload enabled (API)
- Debug logging

### Production Recommendations
- Secrets management (Docker Secrets, Vault)
- Environment-specific configs
- Production WSGI server (Gunicorn)
- SSL/TLS termination
- Rate limiting
- Request authentication
- Backup strategies

## Performance Optimization

1. **Caching Strategy**:
   - Static data (POIs): 5-minute TTL
   - Dynamic data (bikes): 1-minute TTL
   - Cache invalidation on writes

2. **Database Indexes**:
   - MySQL: Indexes on `type` and `name`
   - MongoDB: Indexes on `station_id`, `last_updated`, geospatial

3. **Connection Pooling**:
   - MySQL pool: 1-10 connections
   - Reuse connections instead of creating new ones

## Learning Objectives Demonstrated

✅ RESTful API design with FastAPI
✅ SQL database operations (mysql-connector-python)
✅ NoSQL database operations (pymongo)  
✅ Caching with Redis  
✅ Docker containerization  
✅ Docker Compose orchestration  
✅ Service dependencies and health checks  
✅ Data validation with Pydantic  
✅ API documentation (Swagger/OpenAPI)  
✅ Environment-based configuration  
✅ Cron jobs in containers  
✅ Interactive data visualization  

## Troubleshooting

See README.md for common issues and solutions.
