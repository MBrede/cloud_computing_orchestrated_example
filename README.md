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

- **Documentation (5 points)**
  - Interactive Swagger UI at `http://localhost:8000/docs`
  - Comprehensive code documentation with docstrings
  - This README with setup instructions

- **Database (5 points)**
  - MySQL for structured city data
  - MongoDB for bike-sharing time-series data
  - Redis for caching frequently accessed data

- **Data Processing Client (5 points + 5 bonus points)**
  - Interactive Streamlit dashboard
  - Map visualization of Kiel with data overlays
  - Real-time bike availability display
  - Additionally data-loader container

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

**Total Points: 30 base + 45 bonus = 75 points (before presentation)**

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

## 🤝 Contributing

This is an example project for educational purposes. Feel free to fork and extend!
