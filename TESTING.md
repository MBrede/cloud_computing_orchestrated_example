# Testing Guide

This guide helps you test the Kiel City Data Platform to ensure everything works correctly.

## Prerequisites

- Docker installed and running
- Docker Compose installed
- At least 4GB of free RAM
- Ports 8000, 8501, 3306, 27017, 6379 available

## Quick Test

```bash
# Start the system
./start.sh
# or
docker-compose up --build

# Wait about 30-60 seconds for all services to start

# Access the applications
# Dashboard: http://localhost:8501
# API Docs: http://localhost:8000/docs
# API: http://localhost:8000

# Stop the system
./stop.sh
# or
docker-compose down
```

## Detailed Testing Checklist

### 1. Service Health Checks

```bash
# Check all containers are running
docker-compose ps

# Expected output: 6 containers
# - kiel-mysql (healthy)
# - kiel-mongodb (healthy)
# - kiel-redis (healthy)
# - kiel-api (healthy)
# - kiel-dashboard (running)
# - kiel-cron-job (running)
# - kiel-data-loader (exited 0)
```

### 2. Database Initialization

**MySQL:**
```bash
# Check MySQL logs
docker-compose logs data-loader

# Should see:
# ✓ MySQL is ready!
# ✓ Table created successfully
# ✓ Inserted 30 Points of Interest
# ✓ Data loading completed successfully!
```

**MongoDB:**
```bash
# Check cron job logs
docker-compose logs cron-job

# Should see:
# ✓ MongoDB is ready!
# ✓ Fetched data successfully
# ✓ Bike data sync completed successfully!
```

### 3. API Testing

**Method 1: Swagger UI (Interactive)**

1. Open http://localhost:8000/docs
2. Test GET endpoint:
   - Click on `GET /api/city/pois`
   - Click "Try it out"
   - Click "Execute"
   - Should see list of POIs with 200 status
3. Test POST endpoint:
   - Click on `POST /api/city/pois`
   - Click "Try it out"
   - Enter test data:
     ```json
     {
       "name": "Test Location",
       "type": "test",
       "latitude": 54.32,
       "longitude": 10.13,
       "description": "Test POI"
     }
     ```
   - Click "Execute"
   - Should see 201 Created status

**Method 2: curl (Command Line)**

```bash
# Health check
curl http://localhost:8000/health

# Get all POIs
curl http://localhost:8000/api/city/pois

# Get POIs of specific type
curl "http://localhost:8000/api/city/pois?poi_type=museum"

# Search POIs
curl "http://localhost:8000/api/city/search?q=Kiel&search_field=name"

# Get bike stations
curl http://localhost:8000/api/bikes/stations

# Get bike stations with minimum bikes
curl "http://localhost:8000/api/bikes/stations?min_bikes=2"

# Get statistics
curl http://localhost:8000/api/stats

# Create a new POI
curl -X POST http://localhost:8000/api/city/pois \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kiel Fjord",
    "type": "waterfront",
    "latitude": 54.3267,
    "longitude": 10.1450,
    "description": "Beautiful fjord view"
  }'
```

### 4. Dashboard Testing

1. Open http://localhost:8501
2. **Verify map loads**: Should see Kiel map with markers
3. **Test POI display**:
   - Check "Show Points of Interest" is enabled
   - Should see colored markers for different POI types
   - Click on a marker - popup should show POI details
4. **Test bike station display**:
   - Check "Show Bike Stations" is enabled
   - Should see bike station markers
   - Different colors based on availability (green = available, orange = low, red = empty)
5. **Test filters**:
   - Select "museum" from POI type filter
   - Map should update to show only museums
   - Select "All" - all POIs should reappear
6. **Test bike filter**:
   - Move "Minimum bikes available" slider to 3
   - Only stations with 3+ bikes should show
7. **Verify statistics**:
   - Sidebar should show total POIs, stations, bikes
   - Numbers should match API `/api/stats`
8. **Test refresh**:
   - Click "🔄 Refresh Data" button
   - Data should reload

### 5. Cache Testing

**Test cache is working:**

```bash
# First request (cache miss)
time curl http://localhost:8000/api/city/pois > /dev/null

# Second request (cache hit - should be faster)
time curl http://localhost:8000/api/city/pois > /dev/null

# Check Redis
docker-compose exec redis redis-cli -a redis_secure_password_2024 KEYS "*"
# Should see cache keys like "pois:type:None:limit:100"
```

### 6. Cron Job Testing

**Verify cron job runs every 5 minutes:**

```bash
# Watch cron job logs
docker-compose logs -f cron-job

# Wait 5 minutes, should see new log entries
# Or manually trigger:
docker-compose exec cron-job python /app/fetch_bikes.py
```

### 7. Database SDK Testing

**MySQL Connection:**
```bash
# Connect to MySQL
docker-compose exec mysql mysql -u kiel_user -p kiel_data

# Run queries
SELECT COUNT(*) FROM points_of_interest;
SELECT type, COUNT(*) FROM points_of_interest GROUP BY type;
\q
```

**MongoDB Connection:**
```bash
# Connect to MongoDB
docker-compose exec mongodb mongosh -u bike_user -p bike_secure_password_2024 --authenticationDatabase admin bike_sharing

# Run queries
db.bike_stations.count()
db.bike_stations.find().limit(3).pretty()
exit
```

**Redis Connection:**
```bash
# Connect to Redis
docker-compose exec redis redis-cli -a redis_secure_password_2024

# Check cache
KEYS *
TTL "pois:type:None:limit:100"
GET "pois:type:None:limit:100"
exit
```

## Expected Results Summary

✅ **All containers running** (mysql, mongodb, redis, api, dashboard, cron-job)  
✅ **Data loader completed successfully** (30 POIs in MySQL)  
✅ **Bike data fetched** (stations in MongoDB)  
✅ **API responding** (200 OK for GET, 201 Created for POST)  
✅ **Dashboard loads** (map with markers visible)  
✅ **Caching works** (Redis keys present, faster second request)  
✅ **Swagger documentation** (http://localhost:8000/docs accessible)  

## Troubleshooting Common Issues

### Issue: "Port already in use"

**Solution:**
```bash
# Find process using the port
lsof -i :8000  # or :8501, :5432, etc.

# Kill the process or stop other containers
docker-compose down

# Use different ports (edit docker-compose.yml)
```

### Issue: "Connection refused" to database

**Solution:**
```bash
# Check database health
docker-compose ps

# View database logs
docker-compose logs mysql
docker-compose logs mongodb

# Restart services
docker-compose restart mysql
docker-compose restart api
```

### Issue: "No bike data appearing"

**Solution:**
```bash
# Check cron job logs for errors
docker-compose logs cron-job

# Manually trigger bike data fetch
docker-compose exec cron-job python /app/fetch_bikes.py

# Check if DonkeyRepublic API is accessible
curl -H "Accept: application/com.donkeyrepublic.v7" \
  "https://stables.donkey.bike/api/public/nearby?top_right=54.406143,10.262604&bottom_left=54.272041,10.006485&filter_type=box"
```

### Issue: "Dashboard won't connect to API"

**Solution:**
```bash
# Check API health
curl http://localhost:8000/health

# Check Docker network
docker network ls
docker network inspect kiel-network

# Restart dashboard
docker-compose restart dashboard
```

### Issue: "Out of memory"

**Solution:**
```bash
# Check Docker resource usage
docker stats

# Increase Docker memory limit (Docker Desktop settings)
# Or reduce service resource usage in docker-compose.yml
```

## Performance Benchmarks

**Expected response times:**
- Health check: < 100ms
- GET /api/city/pois (cached): < 50ms
- GET /api/city/pois (uncached): < 200ms
- GET /api/bikes/stations (cached): < 50ms
- POST /api/city/pois: < 300ms

**Resource usage:**
- Total memory: ~1.5-2GB
- MySQL: ~50MB
- MongoDB: ~100MB
- Redis: ~10MB
- API: ~100MB
- Dashboard: ~200MB

## Integration Test Script

```bash
#!/bin/bash
# Save as test_integration.sh

set -e

echo "Starting integration tests..."

# Test API health
echo "Testing API health..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $STATUS -eq 200 ]; then
    echo "✓ API health check passed"
else
    echo "✗ API health check failed (status: $STATUS)"
    exit 1
fi

# Test POI endpoint
echo "Testing POI endpoint..."
POIS=$(curl -s http://localhost:8000/api/city/pois | jq length)
if [ $POIS -gt 0 ]; then
    echo "✓ POI endpoint returned $POIS items"
else
    echo "✗ POI endpoint returned no data"
    exit 1
fi

# Test bike endpoint
echo "Testing bike endpoint..."
STATIONS=$(curl -s http://localhost:8000/api/bikes/stations | jq length)
if [ $STATIONS -ge 0 ]; then
    echo "✓ Bike endpoint returned $STATIONS items"
else
    echo "✗ Bike endpoint failed"
    exit 1
fi

# Test POST endpoint
echo "Testing POST endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/city/pois \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","type":"test","latitude":54.32,"longitude":10.13,"description":"Test"}' \
  | jq -r '.name')
if [ "$RESPONSE" = "Test" ]; then
    echo "✓ POST endpoint works"
else
    echo "✗ POST endpoint failed"
    exit 1
fi

echo ""
echo "======================================"
echo "  All integration tests passed! ✓"
echo "======================================"
```

Run with:
```bash
chmod +x test_integration.sh
./test_integration.sh
```

## Clean Up

```bash
# Stop all services
docker-compose down

# Remove all data (fresh start)
docker-compose down -v

# Remove all images (full rebuild)
docker-compose down --rmi all -v
```

## Success Criteria

Your system is working correctly if:

1. ✅ All 6 containers start successfully
2. ✅ Data loader populates PostgreSQL with 30 POIs
3. ✅ Cron job fetches bike data into MongoDB
4. ✅ API responds to all endpoints with correct status codes
5. ✅ Dashboard displays map with POI and bike markers
6. ✅ Swagger documentation is accessible and functional
7. ✅ Redis caching improves response times
8. ✅ Health check returns "healthy" status

If all criteria are met, your system is ready for demonstration! 🎉
