# Quick Reference Card

## Start/Stop Commands

```bash
# Start everything
docker-compose up --build

# Start in background (detached mode)
docker-compose up -d

# Stop everything
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:8501 | Interactive map visualization |
| API Docs | http://localhost:8000/docs | Swagger UI |
| API | http://localhost:8000 | REST API endpoints |

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f cron-job
docker-compose logs -f data-loader
```

### Restart Services
```bash
# Restart specific service
docker-compose restart api
docker-compose restart dashboard

# Rebuild and restart
docker-compose up -d --build api
```

### Execute Commands in Containers
```bash
# MySQL
docker-compose exec mysql mysql -u kiel_user -pkiel_secure_password_2024 kiel_data

# MongoDB
docker-compose exec mongodb mongosh -u bike_user -p bike_secure_password_2024 --authenticationDatabase admin bike_sharing

# Redis
docker-compose exec redis redis-cli -a redis_secure_password_2024

# Manually trigger bike data fetch
docker-compose exec cron-job python /app/fetch_bikes.py
```

### Check Status
```bash
# Container status
docker-compose ps

# Resource usage
docker stats

# Health check
curl http://localhost:8000/health
```

## API Endpoints Quick Reference

### City Data (MySQL)
```bash
# List all POIs
GET /api/city/pois

# Get specific POI
GET /api/city/pois/{id}

# Create POI
POST /api/city/pois

# Search POIs
GET /api/city/search?q=museum
```

### Bike Sharing (MongoDB)
```bash
# List stations
GET /api/bikes/stations

# Get specific station
GET /api/bikes/stations/{id}

# Create station
POST /api/bikes/stations

# Station history
GET /api/bikes/stations/{id}/history
```

### System
```bash
# Health check
GET /health

# Statistics
GET /api/stats
```

## Example API Calls

### Get all museums
```bash
curl "http://localhost:8000/api/city/pois?poi_type=museum"
```

### Create a new POI
```bash
curl -X POST http://localhost:8000/api/city/pois \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Location",
    "type": "landmark",
    "latitude": 54.32,
    "longitude": 10.13,
    "description": "An example point of interest"
  }'
```

### Get bike stations with at least 3 bikes
```bash
curl "http://localhost:8000/api/bikes/stations?min_bikes=3"
```

## File Structure

```
.
├── api/                 # FastAPI application
│   ├── main.py         # API endpoints
│   ├── models.py       # Pydantic models
│   ├── database.py     # DB SDK examples
│   └── Dockerfile
├── dashboard/          # Streamlit dashboard
│   ├── app.py
│   └── Dockerfile
├── data-loader/        # MySQL init
│   ├── load_kiel_data.py
│   └── Dockerfile
├── cron-job/          # Bike data sync
│   ├── fetch_bikes.py
│   ├── crontab
│   └── Dockerfile
├── docker-compose.yml  # Orchestration
├── .env               # Environment variables
└── README.md          # Main documentation
```

## Environment Variables

Located in `.env` file:

```bash
# MySQL
MYSQL_HOST=mysql
MYSQL_DB=kiel_data
MYSQL_USER=kiel_user
MYSQL_PASSWORD=kiel_secure_password_2024

# MongoDB
MONGO_HOST=mongodb
MONGO_DB=bike_sharing
MONGO_USER=bike_user
MONGO_PASSWORD=bike_secure_password_2024

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=redis_secure_password_2024
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port in use | Change port mapping in docker-compose.yml |
| Container won't start | Check logs: `docker-compose logs [service]` |
| No bike data | Check cron logs, manually run fetch_bikes.py |
| API errors | Verify databases are healthy: `docker-compose ps` |
| Dashboard won't load | Ensure API is running: `curl localhost:8000/health` |

## Database Schemas

### MySQL - points_of_interest
```sql
id          INT AUTO_INCREMENT PRIMARY KEY
name        VARCHAR(200)
type        VARCHAR(50)
latitude    DOUBLE
longitude   DOUBLE
description TEXT
```

### MongoDB - bike_stations
```javascript
{
  station_id: String,
  name: String,
  latitude: Number,
  longitude: Number,
  bikes_available: Number,
  capacity: Number,
  last_updated: Date,
  location: {
    type: "Point",
    coordinates: [longitude, latitude]
  }
}
```

## Rubric Coverage

### Mandatory (30 points)
- ✅ POST endpoint (create POI, create station)
- ✅ GET endpoint (list POIs, list stations, search)
- ✅ Swagger docs (/docs)
- ✅ Code documentation (docstrings)
- ✅ Database (MySQL, MongoDB, Redis)
- ✅ Dashboard (Streamlit visualization)
- ✅ Docker Compose (6 containers)

### Bonus (40 points)
- ✅ Pydantic models (5 pts)
- ✅ .env file (5 pts)
- ✅ Additional endpoints (10 pts)
- ✅ NoSQL for time-series (15 pts)
- ✅ Redis caching (5 pts)

**Total: 70 points + presentation**

## Presentation Tips

1. **Demo order**: Dashboard → API Docs → Code
2. **Emphasize**: Database SDKs, caching, orchestration
3. **Time**: 15-20 minutes
4. **Practice**: Test everything beforehand!

## Key Learning Points to Mention

- ✅ MySQL SDK (mysql-connector-python): Connection pooling, parameterized queries
- ✅ MongoDB SDK (pymongo): Upsert operations, aggregation
- ✅ Redis caching: TTL strategy, cache invalidation
- ✅ Docker orchestration: Health checks, dependencies
- ✅ Pydantic validation: Type safety, auto-documentation
- ✅ REST API design: Status codes, CRUD operations

## Getting Help

1. Check README.md for detailed documentation
2. Check ARCHITECTURE.md for system design
3. Check TESTING.md for testing procedures
4. Check PRESENTATION_GUIDE.md for presentation help
5. View logs: `docker-compose logs -f [service]`
6. Check health: `curl localhost:8000/health`
