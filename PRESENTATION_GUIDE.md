# Presentation Guide - Cloud Computing Project

This guide helps you prepare a strong presentation for the Cloud Computing project. The presentation is worth **30 points** out of 100.

## Presentation Breakdown (30 points)

- **Time Management** (5 points): Stay within allocated time
- **Question Handling** (5 points): Answer technical questions confidently
- **Clarity of Explanation** (20 points): Clear, structured, and understandable

## Recommended Structure (15-20 minutes)

### 1. Introduction (2 minutes)
- **Project Title**: "Kiel City Data Platform"
- **Goal**: Demonstrate cloud computing orchestration with multiple databases
- **Key Technologies**: Docker Compose, FastAPI, MySQL, MongoDB, Redis

### 2. System Architecture (3-4 minutes)

**Show the architecture diagram** from ARCHITECTURE.md

Explain the layers:
1. **Frontend**: Streamlit dashboard (port 8501)
2. **API**: FastAPI backend (port 8000)
3. **Databases**: MySQL, MongoDB, Redis
4. **Workers**: Data loader, Cron job

**Key Points to Emphasize**:
- Why we chose each database (structured vs time-series data)
- How services communicate (Docker network)
- Dependency management (health checks)

### 3. Live Demonstration (5-6 minutes)

#### Part A: Start the System
```bash
docker-compose up --build
```

**While services start, explain**:
- Docker Compose orchestration
- Service dependencies (data-loader must finish before API starts)
- Health checks ensuring reliability

#### Part B: Show the Dashboard
1. Open http://localhost:8501
2. Show interactive map with POIs and bike stations
3. Demonstrate filters (POI type, minimum bikes)
4. Show statistics panel

**Talking Points**:
- Real-time data from DonkeyRepublic API
- Multiple data sources overlaid on map
- Auto-refresh capability

#### Part C: Show API Documentation
1. Open http://localhost:8000/docs
2. Navigate Swagger UI
3. Execute a GET request (e.g., `/api/city/pois`)
4. Show response format
5. Execute a POST request to create a POI

**Talking Points**:
- Auto-generated documentation
- Request/response validation
- Try-it-out functionality

### 4. Code Walkthrough (4-5 minutes)

#### Show Database SDK Examples

**MySQL (api/database.py)**:
```python
# Show connection pooling
conn = mysql.connector.connect(
    host='mysql', database='kiel_data',
    user='kiel_user', password='...'
)

# Show parameterized query (prevents SQL injection)
cursor.execute("SELECT * FROM pois WHERE type = %s", (poi_type,))
```

**MongoDB (api/database.py)**:
```python
# Show upsert operation
db.bike_stations.update_one(
    {'station_id': 'KIEL001'},
    {'$set': data},
    upsert=True
)
```

**Redis Caching (api/main.py)**:
```python
# Check cache first
cached = redis_cache.get(cache_key)
if cached:
    return cached

# Query database and cache result
data = mysql_db.execute_query(query)
redis_cache.set(cache_key, data, ttl=300)
```

**Key Points**:
- Connection management
- Error handling
- Why caching matters for performance

### 5. Rubric Coverage (2-3 minutes)

Show a slide or speak through how your project meets requirements:

**Mandatory (30 base points)**:
- ✅ FastAPI with POST endpoints (create POI, create bike station)
- ✅ FastAPI with GET endpoints (list POIs, list stations, search)
- ✅ Swagger documentation at /docs
- ✅ Code documentation (docstrings everywhere)
- ✅ Multiple databases (MySQL, MongoDB, Redis)
- ✅ Dashboard visualization (Streamlit)
- ✅ Docker Compose deployment (6 containers)

**Bonus Features (40 points)**:
- ✅ Pydantic models (~5 points)
- ✅ Environment variables for security (~5 points)
- ✅ Additional endpoints: search, filters, history (~10 points)
- ✅ NoSQL with good reason: time-series bike data (~15 points)
- ✅ Redis caching (~5 points)

**Total**: 30 base + 40 bonus = **70 points before presentation**

### 6. Conclusion (1 minute)

**Summary**:
- Demonstrated orchestrated cloud application
- Multiple database types with proper use cases
- Production-ready patterns (caching, validation, health checks)
- Educational example for others to learn from

**Future Enhancements**:
- Kubernetes deployment
- OAuth2 authentication
- Historical data analysis
- Load balancing

## Anticipated Questions & Answers

### Q1: "Why did you choose MongoDB for bike data?"
**Answer**: Bike availability is time-series data that changes frequently. MongoDB's flexible schema allows us to easily store snapshots with varying fields. We can also leverage MongoDB's aggregation framework for historical analysis. MySQL would work too, but MongoDB is more natural for this use case.

### Q2: "How does the caching strategy improve performance?"
**Answer**: Redis caches frequently-accessed data in memory. POIs rarely change, so we cache them for 5 minutes. Bike data changes every 5 minutes (cron job), so we cache for 1 minute. This reduces database load by 60-90% for repeated requests. We invalidate cache on writes to ensure data freshness.

### Q3: "What happens if the DonkeyRepublic API is down?"
**Answer**: The cron job has error handling and logging. If the API fails, it logs the error and tries again in 5 minutes. The dashboard still shows the last successfully fetched data from MongoDB. We could add monitoring/alerting in production.

### Q4: "How would you scale this to production?"
**Answer**: 
1. Deploy on Kubernetes for auto-scaling
2. Add a load balancer for the API
3. Use managed database services (AWS RDS, MongoDB Atlas)
4. Implement Redis cluster for distributed caching
5. Add authentication and rate limiting
6. Set up monitoring (Prometheus, Grafana)

### Q5: "Why use both MySQL and MongoDB? Why not just one?"
**Answer**: This demonstrates understanding of different database paradigms:
- MySQL for structured, relational data with enforced schema
- MongoDB for flexible, rapidly-changing data
- Each database is optimized for its use case
In a real project, you'd choose based on requirements, but this example shows proficiency with both.

### Q6: "How do you ensure database security?"
**Answer**: 
1. All credentials in `.env` file, not hardcoded
2. Environment variables injected at runtime
3. Database authentication required
4. Parameterized queries prevent SQL injection
5. Internal Docker network isolates databases
6. Only API and dashboard exposed to host

### Q7: "Explain the dependency management in Docker Compose"
**Answer**: Services use `depends_on` with health check conditions:
- API waits for all databases to be healthy AND data-loader to complete
- Dashboard waits for API to be healthy
- This ensures services start in correct order and are ready before dependents start
- Health checks use database-specific commands (pg_isready, mongosh ping, etc.)

## Time Management Tips

**Allocate time strictly**:
- Set a timer during practice
- Have a "speedrun" version if running short
- Know what to skip if time is tight (detailed code walkthrough)

**If you have 10 minutes**:
1. Quick architecture overview (1 min)
2. Live demo (5 min)
3. Show one DB SDK example (2 min)
4. Rubric coverage (2 min)

**If you have 15 minutes**:
- Use the full structure above

**If you have 20 minutes**:
- Add detailed code walkthrough
- Show more SDK examples
- Discuss design decisions

## Presentation Materials Checklist

- [ ] Architecture diagram visible (ARCHITECTURE.md)
- [ ] System running and accessible
- [ ] Browser tabs open: Dashboard, Swagger, Logs
- [ ] Code editor open to key files: main.py, database.py, models.py
- [ ] Terminal ready for commands
- [ ] Rubric coverage slide/notes
- [ ] Practiced timing (15-20 minutes)

## Common Mistakes to Avoid

❌ Spending too much time on setup/intro  
❌ Getting lost in code details  
❌ Not showing a live demo  
❌ Ignoring the rubric requirements  
❌ Poor time management (running over/under)  
❌ Not testing demo beforehand (container issues)  
❌ Reading from slides/notes verbatim  

✅ Show working system first  
✅ Explain WHY, not just WHAT  
✅ Connect features to rubric points  
✅ Practice with a timer  
✅ Test everything before presenting  
✅ Speak confidently and naturally  

## Final Tips

1. **Practice**: Run through the presentation 3-5 times
2. **Backup Plan**: Have screenshots if live demo fails
3. **Know Your Code**: Be able to explain any line
4. **Be Honest**: If you don't know something, say so and explain how you'd find out
5. **Enthusiasm**: Show passion for what you built!

Good luck! 🍀
