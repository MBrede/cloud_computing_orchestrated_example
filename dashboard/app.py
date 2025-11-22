"""
Kiel City Data Platform - Streamlit Dashboard

This dashboard demonstrates:
1. Interactive map visualization with Folium
2. Real-time data from multiple APIs and databases
3. Data filtering and aggregation
4. Streamlit UI components and layout
5. Integration with FastAPI backend

The dashboard displays:
- Kiel city Points of Interest (from MySQL via API)
- DonkeyRepublic bike sharing stations (from MongoDB via API)
- Interactive filters and statistics
"""

import streamlit as st
import requests
import pandas as pd
import folium
from folium import plugins
from streamlit_folium import st_folium
import time
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Kiel City Data Platform",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL (container name in Docker network)
API_BASE_URL = "http://api:8000"

# Kiel city center coordinates
KIEL_CENTER = [54.3233, 10.1394]


@st.cache_data(ttl=60)
def fetch_pois(poi_type=None):
    """
    Fetch Points of Interest from API.
    
    Args:
        poi_type: Optional filter by POI type
    
    Returns:
        list: POIs data
    """
    try:
        params = {}
        if poi_type:
            params['poi_type'] = poi_type
        
        response = requests.get(f"{API_BASE_URL}/api/city/pois", params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching POIs: {e}")
        return []


@st.cache_data(ttl=30)
def fetch_bike_stations(min_bikes=0):
    """
    Fetch bike stations from API.
    
    Args:
        min_bikes: Minimum bikes available filter
    
    Returns:
        list: Bike stations data
    """
    try:
        params = {'min_bikes': min_bikes}
        response = requests.get(f"{API_BASE_URL}/api/bikes/stations", params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching bike stations: {e}")
        return []


@st.cache_data(ttl=60)
def fetch_stats():
    """
    Fetch system statistics from API.
    
    Returns:
        dict: Statistics data
    """
    try:
        response = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return {}


def fetch_health():
    """
    Fetch system health status.
    
    Returns:
        dict: Health check data
    """
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": "error", "postgres": False, "mongodb": False, "redis": False}  # Note: 'postgres' field name kept for API compatibility


def create_map(pois, bike_stations, show_pois=True, show_bikes=True):
    """
    Create an interactive Folium map with POIs and bike stations.
    
    Args:
        pois: List of POI data
        bike_stations: List of bike station data
        show_pois: Whether to show POIs
        show_bikes: Whether to show bike stations
    
    Returns:
        folium.Map: Interactive map object
    """
    # Create base map
    m = folium.Map(
        location=KIEL_CENTER,
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Add POIs
    if show_pois and pois:
        poi_group = folium.FeatureGroup(name='Points of Interest')
        
        # Define colors for different POI types
        type_colors = {
            'museum': 'purple',
            'park': 'green',
            'landmark': 'red',
            'transport': 'blue',
            'shopping': 'orange',
            'culture': 'pink',
            'waterfront': 'lightblue',
            'beach': 'beige',
            'education': 'darkblue',
            'church': 'gray',
            'sports': 'darkgreen',
            'market': 'lightgreen',
            'historic': 'darkred'
        }
        
        for poi in pois:
            color = type_colors.get(poi.get('type', 'unknown'), 'gray')
            
            folium.Marker(
                location=[poi['latitude'], poi['longitude']],
                popup=folium.Popup(
                    f"<b>{poi['name']}</b><br>"
                    f"Type: {poi['type']}<br>"
                    f"{poi.get('description', '')}",
                    max_width=300
                ),
                tooltip=poi['name'],
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(poi_group)
        
        poi_group.add_to(m)
    
    # Add bike stations
    if show_bikes and bike_stations:
        bike_group = folium.FeatureGroup(name='Bike Stations')
        
        for station in bike_stations:
            bikes = station.get('bikes_available', 0)
            
            # Color based on availability
            if bikes == 0:
                color = 'red'
                icon = 'remove'
            elif bikes < 3:
                color = 'orange'
                icon = 'exclamation-sign'
            else:
                color = 'green'
                icon = 'ok-sign'
            
            folium.Marker(
                location=[station['latitude'], station['longitude']],
                popup=folium.Popup(
                    f"<b>🚲 {station['name']}</b><br>"
                    f"Bikes available: {bikes}<br>"
                    f"Capacity: {station.get('capacity', 'N/A')}<br>"
                    f"Last updated: {station.get('last_updated', 'N/A')}",
                    max_width=300
                ),
                tooltip=f"{station['name']} ({bikes} bikes)",
                icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
            ).add_to(bike_group)
        
        bike_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(m)
    
    return m


def main():
    """Main dashboard function."""
    
    # Header
    st.title("🏙️ Kiel City Data Platform")
    st.markdown("Interactive dashboard for exploring Kiel's Points of Interest and bike sharing network")
    
    # Sidebar
    st.sidebar.header("⚙️ Settings")
    
    # System health status
    with st.sidebar:
        st.subheader("System Health")
        health = fetch_health()
        
        status_icon = "✅" if health.get("status") == "healthy" else "⚠️"
        st.markdown(f"**Status:** {status_icon} {health.get('status', 'unknown').upper()}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            mysql_icon = "✅" if health.get("postgres") else "❌"
            st.markdown(f"{mysql_icon} MySQL")
        with col2:
            mg_icon = "✅" if health.get("mongodb") else "❌"
            st.markdown(f"{mg_icon} Mongo")
        with col3:
            rd_icon = "✅" if health.get("redis") else "❌"
            st.markdown(f"{rd_icon} Redis")
        
        st.divider()
    
    # Display options
    st.sidebar.subheader("Display Options")
    show_pois = st.sidebar.checkbox("Show Points of Interest", value=True)
    show_bikes = st.sidebar.checkbox("Show Bike Stations", value=True)
    
    # POI filters
    if show_pois:
        st.sidebar.subheader("POI Filters")
        poi_type_filter = st.sidebar.selectbox(
            "Filter by type",
            ["All"] + ["museum", "park", "landmark", "transport", "culture", "waterfront", 
                       "beach", "education", "church", "sports", "market", "historic", "shopping"]
        )
        poi_type = None if poi_type_filter == "All" else poi_type_filter
    else:
        poi_type = None
    
    # Bike filters
    if show_bikes:
        st.sidebar.subheader("Bike Station Filters")
        min_bikes = st.sidebar.slider("Minimum bikes available", 0, 10, 0)
    else:
        min_bikes = 0
    
    # Auto-refresh
    st.sidebar.subheader("Auto-refresh")
    auto_refresh = st.sidebar.checkbox("Enable auto-refresh (30s)", value=False)
    
    # Statistics
    st.sidebar.divider()
    st.sidebar.subheader("📊 Statistics")
    stats = fetch_stats()
    
    if stats:
        st.sidebar.metric("Total POIs", stats.get('total_pois', 0))
        st.sidebar.metric("Total Stations", stats.get('total_stations', 0))
        st.sidebar.metric("Bikes Available", stats.get('total_bikes_available', 0))
    
    # Main content
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🗺️ Interactive Map")
        
        # Fetch data
        with st.spinner("Loading data..."):
            pois = fetch_pois(poi_type) if show_pois else []
            bike_stations = fetch_bike_stations(min_bikes) if show_bikes else []
        
        # Create and display map
        m = create_map(pois, bike_stations, show_pois, show_bikes)
        st_folium(m, width=None, height=600)
        
        # Data info
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            if show_pois:
                st.info(f"📍 Showing {len(pois)} Points of Interest")
        with info_col2:
            if show_bikes:
                st.info(f"🚲 Showing {len(bike_stations)} Bike Stations")
    
    with col2:
        st.subheader("📋 Data Details")
        
        # POI table
        if show_pois and pois:
            with st.expander("Points of Interest", expanded=False):
                poi_df = pd.DataFrame(pois)[['name', 'type', 'latitude', 'longitude']]
                st.dataframe(poi_df, hide_index=True, height=200)
        
        # Bike stations table
        if show_bikes and bike_stations:
            with st.expander("Bike Stations", expanded=False):
                bike_df = pd.DataFrame(bike_stations)[['name', 'bikes_available', 'capacity']]
                bike_df = bike_df.fillna({'capacity': 'N/A'})
                st.dataframe(bike_df, hide_index=True, height=200)
        
        # Type distribution
        if show_pois and pois:
            st.subheader("POI Type Distribution")
            poi_df = pd.DataFrame(pois)
            type_counts = poi_df['type'].value_counts()
            st.bar_chart(type_counts)
        
        # Bike availability distribution
        if show_bikes and bike_stations:
            st.subheader("Bike Availability")
            bike_df = pd.DataFrame(bike_stations)
            availability_ranges = pd.cut(
                bike_df['bikes_available'],
                bins=[0, 1, 3, 5, 100],
                labels=['0', '1-2', '3-4', '5+'],
                right=False
            )
            avail_counts = availability_ranges.value_counts()
            st.bar_chart(avail_counts)
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**API Documentation:** [Swagger UI](http://localhost:8000/docs)")
    with col2:
        st.markdown(f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col3:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
