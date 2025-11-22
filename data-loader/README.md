# Data Loader Scripts

This directory contains scripts for loading and enriching Kiel city data into MySQL.

## Scripts

### 1. `load_kiel_data.py` (Main Data Importer)

**Purpose**: Imports population and demographic data from the Kiel Open Data Portal into MySQL.

**Data Source**: [Kiel Open Data Portal](https://www.kiel.de/de/kiel_zukunft/statistik_kieler_zahlen/open_data/index.php)

**What it does**:
1. Connects to MySQL and waits for it to be ready
2. Creates database tables for:
   - `stadtteile` (districts)
   - `population_by_gender`
   - `population_by_age`
   - `population_by_religion`
   - `population_by_family_status`
   - `foreigners_by_nationality`
   - `households`
3. Imports CSV files from the `/data` directory
4. Verifies the import was successful

**When it runs**: Automatically executed during `docker-compose up` as part of the initialization process.

**CSV Files Used**:
- `kiel_bevoelkerung_stadtteile_einwohner_geschlecht.csv`
- `kiel_bevoelkerung_altersgruppen_stadtteile.csv`
- `kiel_bevoelkerung_einwohner_nach_religionszugehoerigkeit_in_den_stadtteilen.csv`
- `kiel_bevoelkerung_einwohner_nach_familienstand_in_den_stadtteilen.csv`
- `kiel_bevoelkerung_auslaender_nach_ausgesuchten_nationalitaeten_in_den_stadtteilen.csv`
- `kiel_bevoelkerung_haushalte_nach_haushaltstypen_und_personenanzahl_in_den_stadtteilen.csv`

### 2. `add_stadtteil_coordinates.py` (Geographic Enrichment)

**Purpose**: Adds latitude/longitude coordinates to the Stadtteile (districts) table.

**What it does**:
1. Connects to MySQL
2. Updates the `stadtteile` table with approximate center coordinates for each district
3. Verifies that coordinates were added successfully
4. (Optional) Exports enriched data to CSV

**When to run**: This script should be run **ONLY ONCE** after the initial data import.

**NOTE FOR STUDENTS**: This script has already been run! The coordinates are already in the database. You don't need to run it again unless you reset the database.

**Manual execution** (if needed):
```bash
# Inside the data-loader container
python add_stadtteil_coordinates.py

# Or from host machine
docker-compose exec data-loader python /app/add_stadtteil_coordinates.py
```

## Database Schema

### stadtteile
```sql
stadtteil_nr  INT PRIMARY KEY     -- District number (1-30)
name          VARCHAR(100)        -- District name (e.g., "Altstadt")
latitude      DOUBLE              -- Center latitude
longitude     DOUBLE              -- Center longitude
```

### population_by_gender
```sql
id            INT AUTO_INCREMENT PRIMARY KEY
stadtteil_nr  INT                 -- Foreign key to stadtteile
datum         DATE                -- Data date (e.g., 2023-12-31)
total         INT                 -- Total population
male          INT                 -- Male population
female        INT                 -- Female population
```

### population_by_age
```sql
id            INT AUTO_INCREMENT PRIMARY KEY
stadtteil_nr  INT                 -- Foreign key to stadtteile
datum         DATE                -- Data date
age_group     VARCHAR(50)         -- Age range (e.g., "25 bis unter 30")
count         INT                 -- Population in this age group
```

(Similar structure for other tables)

## Data Flow

```
CSV Files (data/)
      ↓
  load_kiel_data.py
      ↓
  MySQL Tables Created
      ↓
  Data Imported
      ↓
  add_stadtteil_coordinates.py (run once)
      ↓
  Coordinates Added
      ↓
  Ready for API/Dashboard
```

## Troubleshooting

### Data loader fails
```bash
# Check logs
docker-compose logs data-loader

# Verify CSV files exist
docker-compose exec data-loader ls -la /data

# Manually run the loader
docker-compose exec data-loader python /app/load_kiel_data.py
```

### Missing coordinates
```bash
# Run the coordinate mapping script
docker-compose exec data-loader python /app/add_stadtteil_coordinates.py
```

### Verify data in MySQL
```bash
# Connect to MySQL
docker-compose exec mysql mysql -u kiel_user -pkiel_secure_password_2024 kiel_data

# Check table counts
SELECT COUNT(*) FROM stadtteile;
SELECT COUNT(*) FROM population_by_gender;

# View districts with coordinates
SELECT stadtteil_nr, name, latitude, longitude FROM stadtteile;
```

## Development Notes

All scripts use:
- `mysql-connector-python` for database connectivity
- Environment variables for configuration (from `.env` file)
- Proper error handling and logging
- CSV processing with Python's built-in `csv` module
