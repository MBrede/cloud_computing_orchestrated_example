"""
Kiel City Data Platform - Streamlit Dashboard

This dashboard demonstrates:
1. Interactive map visualization with Folium
2. Real-time demographic data from MySQL
3. Demographic heatmap overlays
4. Data filtering and aggregation
5. Streamlit UI components and layout
6. Integration with FastAPI backend

The dashboard displays:
- Kiel city Stadtteile (districts) with demographic data
- DonkeyRepublic bike sharing stations (from MongoDB via API)
- Demographic heatmaps (population density, age distribution, etc.)
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
import branca.colormap as cm

# Page configuration
st.set_page_config(
    page_title="Kiel City Data Platform",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL (container name in Docker network)
API_BASE_URL = "http://api:8000"

# Kiel city center coordinates
KIEL_CENTER = [54.3233, 10.1394]


@st.cache_data(ttl=300)
def fetch_stadtteile():
    """
    Fetch Stadtteile (districts) from API.

    Returns:
        list: Stadtteile data
    """
    try:
        response = requests.get(f"{API_BASE_URL}/api/stadtteile", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching Stadtteile: {e}")
        return []


@st.cache_data(ttl=300)
def fetch_stadtteil_demographics(stadtteil_nr):
    """
    Fetch demographic data for a specific Stadtteil.

    Args:
        stadtteil_nr: District number

    Returns:
        dict: Demographic data
    """
    try:
        response = requests.get(f"{API_BASE_URL}/api/stadtteile/{stadtteil_nr}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching demographics for Stadtteil {stadtteil_nr}: {e}")
        return None


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
        return {"status": "error", "mysql": False, "mongodb": False, "redis": False}


def create_map(stadtteile_with_demographics, bike_stations, show_stadtteile=True, show_bikes=True,
               heatmap_metric=None):
    """
    Create an interactive Folium map with Stadtteile and bike stations.

    Args:
        stadtteile_with_demographics: List of districts with demographic data
        bike_stations: List of bike station data
        show_stadtteile: Whether to show district markers
        show_bikes: Whether to show bike stations
        heatmap_metric: Metric to use for heatmap ('population', 'density', 'age_avg', etc.)

    Returns:
        folium.Map: Interactive map object
    """
    # Create base map
    m = folium.Map(
        location=KIEL_CENTER,
        zoom_start=12,
        tiles='OpenStreetMap'
    )

    # Add demographic heatmap if requested
    if heatmap_metric and stadtteile_with_demographics:
        # Prepare data for heatmap
        heatmap_data = []
        metric_values = []

        for district in stadtteile_with_demographics:
            if district.get('latitude') and district.get('longitude'):
                value = 0

                if heatmap_metric == 'population':
                    value = district.get('total_population', 0)
                elif heatmap_metric == 'male_ratio':
                    total = district.get('total_population', 0)
                    if total > 0:
                        value = (district.get('male', 0) / total) * 100
                elif heatmap_metric == 'female_ratio':
                    total = district.get('total_population', 0)
                    if total > 0:
                        value = (district.get('female', 0) / total) * 100

                if value > 0:
                    heatmap_data.append([district['latitude'], district['longitude'], value])
                    metric_values.append(value)

        if heatmap_data:
            # Create heatmap layer
            plugins.HeatMap(
                heatmap_data,
                name='Demographic Heatmap',
                min_opacity=0.4,
                max_opacity=0.8,
                radius=25,
                blur=20,
                gradient={
                    0.0: 'blue',
                    0.5: 'yellow',
                    0.75: 'orange',
                    1.0: 'red'
                }
            ).add_to(m)

    # Add Stadtteile markers
    if show_stadtteile and stadtteile_with_demographics:
        stadtteil_group = folium.FeatureGroup(name='Stadtteile (Districts)')

        for district in stadtteile_with_demographics:
            if district.get('latitude') and district.get('longitude'):
                # Create popup content
                popup_html = f"""
                <div style="font-family: Arial; min-width: 200px;">
                    <h4 style="margin: 0 0 10px 0;">{district['name']}</h4>
                    <table style="width: 100%;">
                        <tr><td><b>District #:</b></td><td>{district['stadtteil_nr']}</td></tr>
                        <tr><td><b>Population:</b></td><td>{district.get('total_population', 'N/A'):,}</td></tr>
                        <tr><td><b>Male:</b></td><td>{district.get('male', 'N/A'):,}</td></tr>
                        <tr><td><b>Female:</b></td><td>{district.get('female', 'N/A'):,}</td></tr>
                    </table>
                </div>
                """

                # Color based on population size
                pop = district.get('total_population', 0)
                if pop > 15000:
                    color = 'red'
                elif pop > 10000:
                    color = 'orange'
                elif pop > 5000:
                    color = 'blue'
                else:
                    color = 'gray'

                folium.Marker(
                    location=[district['latitude'], district['longitude']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{district['name']} ({district.get('total_population', 0):,})",
                    icon=folium.Icon(color=color, icon='home', prefix='fa')
                ).add_to(stadtteil_group)

        stadtteil_group.add_to(m)

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
    st.title("🏙️ Kiel City Demographic Data Platform")
    st.markdown("Interactive dashboard for exploring Kiel's demographic data and bike sharing network")

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
            mysql_icon = "✅" if health.get("mysql") else "❌"
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
    show_stadtteile = st.sidebar.checkbox("Show District Markers", value=True)
    show_bikes = st.sidebar.checkbox("Show Bike Stations", value=True)

    # Heatmap options
    st.sidebar.subheader("Heatmap Layer")
    heatmap_enabled = st.sidebar.checkbox("Enable Demographic Heatmap", value=False)
    heatmap_metric = None

    if heatmap_enabled:
        heatmap_metric = st.sidebar.selectbox(
            "Heatmap Metric",
            ["population", "male_ratio", "female_ratio"],
            format_func=lambda x: {
                "population": "Total Population",
                "male_ratio": "Male Ratio (%)",
                "female_ratio": "Female Ratio (%)"
            }[x]
        )

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
        st.sidebar.metric("Total Districts", stats.get('total_stadtteile', 0))
        st.sidebar.metric("Total Population", f"{stats.get('total_population', 0):,}")
        st.sidebar.metric("Bike Stations", stats.get('total_stations', 0))
        st.sidebar.metric("Bikes Available", stats.get('total_bikes_available', 0))

    # Main content
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("🗺️ Interactive Map")

        # Fetch data
        with st.spinner("Loading data..."):
            stadtteile = fetch_stadtteile() if show_stadtteile or heatmap_enabled else []

            # Fetch demographics for each Stadtteil
            stadtteile_with_demographics = []
            if stadtteile:
                for stadtteil in stadtteile:
                    demo = fetch_stadtteil_demographics(stadtteil['stadtteil_nr'])
                    if demo:
                        stadtteile_with_demographics.append(demo)

            bike_stations = fetch_bike_stations(min_bikes) if show_bikes else []

        # Create and display map
        m = create_map(stadtteile_with_demographics, bike_stations, show_stadtteile,
                      show_bikes, heatmap_metric if heatmap_enabled else None)
        st_folium(m, width=None, height=600)

        # Data info
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            if show_stadtteile:
                total_pop = sum(d.get('total_population', 0) for d in stadtteile_with_demographics)
                st.info(f"🏘️ Showing {len(stadtteile_with_demographics)} Districts (Pop: {total_pop:,})")
        with info_col2:
            if show_bikes:
                st.info(f"🚲 Showing {len(bike_stations)} Bike Stations")

    with col2:
        st.subheader("📋 Data Details")

        # Stadtteile table
        if show_stadtteile and stadtteile_with_demographics:
            with st.expander("Districts Population", expanded=True):
                demo_df = pd.DataFrame(stadtteile_with_demographics)[
                    ['name', 'total_population', 'male', 'female']
                ]
                demo_df.columns = ['District', 'Population', 'Male', 'Female']
                demo_df = demo_df.sort_values('Population', ascending=False)
                st.dataframe(demo_df, hide_index=True, height=250)

        # Bike stations table
        if show_bikes and bike_stations:
            with st.expander("Bike Stations", expanded=False):
                bike_df = pd.DataFrame(bike_stations)[['name', 'bikes_available', 'capacity']]
                bike_df.columns = ['Station', 'Bikes', 'Capacity']
                bike_df = bike_df.fillna({'Capacity': 'N/A'})
                st.dataframe(bike_df, hide_index=True, height=200)

        # Population distribution
        if show_stadtteile and stadtteile_with_demographics:
            st.subheader("Population by District")
            demo_df = pd.DataFrame(stadtteile_with_demographics)
            pop_chart = demo_df.set_index('name')['total_population'].sort_values(ascending=False).head(10)
            st.bar_chart(pop_chart)

        # Gender distribution
        if show_stadtteile and stadtteile_with_demographics:
            st.subheader("Gender Distribution")
            demo_df = pd.DataFrame(stadtteile_with_demographics)
            gender_data = pd.DataFrame({
                'Male': [demo_df['male'].sum()],
                'Female': [demo_df['female'].sum()]
            })
            st.bar_chart(gender_data.T)

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
