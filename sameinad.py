#----------------------------------------------------------------------------------------------------
# Setup and Environment Configuration
#----------------------------------------------------------------------------------------------------

from sqlalchemy import create_engine
from shiny import App, render, ui
import pandas as pd
import geopandas as gpd
from shapely import wkt
import folium
from folium.plugins import MarkerCluster
from matplotlib import cm, colors
import numpy as np
import plotly.express as px
from shinywidgets import output_widget, render_widget
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Fetch database credentials from environment variables
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Check if all variables are set
if not all([db_user, db_password, db_host, db_port, db_name]):
    raise ValueError("One or more environment variables are not set.")

# Create the database engine
engine = create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")


#----------------------------------------------------------------------------------------------------
# Data Fetching and Processing
#----------------------------------------------------------------------------------------------------

# Function to fetch houses and kingdoms data with explicit mapping
def fetch_houses_and_kingdoms():
    query = """
    SELECT 
        h.name AS house_name,
        CASE
            WHEN h.region IN ('The North', 'The Neck', 'Beyond the Wall') THEN 'The North'
            WHEN h.region = 'The Vale' THEN 'The Vale'
            WHEN h.region = 'Iron Islands' THEN 'Iron Islands'
            WHEN h.region = 'The Riverlands' THEN 'The Riverlands'
            WHEN h.region = 'The Westerlands' THEN 'The Westerlands'
            WHEN h.region = 'The Stormlands' THEN 'The Stormlands'
            WHEN h.region = 'The Crownlands' THEN 'The Crownlands'
            WHEN h.region = 'The Reach' THEN 'The Reach'
            WHEN h.region = 'Dorne' THEN 'Dorne'
            ELSE 'Other Regions'
        END AS kingdom_name
    FROM 
        got.houses h
    """
    df = pd.read_sql_query(query, engine)
    df["house_name"] = df["house_name"].str.replace("^House ", "", regex=True)
    df.columns = ["House Name", "Kingdom Name"]
    return df

# Fetch data for house count plot
data_houses_kingdoms = fetch_houses_and_kingdoms()
house_counts = data_houses_kingdoms.groupby("Kingdom Name").size().reset_index(name='Number of Houses')

# Fetch data for population and area
query_population = """
SELECT 
    CASE 
        WHEN h.region IN ('The North', 'The Neck', 'Beyond the Wall') THEN 'The North'
        WHEN h.region = 'The Vale' THEN 'The Vale'
        WHEN h.region = 'Iron Islands' THEN 'Iron Islands'
        WHEN h.region = 'The Riverlands' THEN 'The Riverlands'
        WHEN h.region = 'The Westerlands' THEN 'The Westerlands'
        WHEN h.region = 'The Stormlands' THEN 'The Stormlands'
        WHEN h.region = 'The Crownlands' THEN 'The Crownlands'
        WHEN h.region = 'The Reach' THEN 'The Reach'
        WHEN h.region = 'Dorne' THEN 'Dorne'
        ELSE 'Other Regions'
    END AS kingdom,
    COUNT(c.id) as total_population
FROM got.characters c
JOIN got.houses h ON h.id = ANY(c.allegiances)
GROUP BY kingdom;
"""

query_area = """
SELECT 
    CASE 
        WHEN k.name = 'The Neck' THEN 'The North'
        WHEN k.name = 'The Crownlands' THEN 'The Crownlands'
        ELSE k.name
    END AS kingdom,
    ST_Area(k.geog::geography) / 1000000 AS area_km2
FROM atlas.kingdoms k;
"""

# Load data into pandas DataFrames
df_population = pd.read_sql_query(query_population, engine)
df_area = pd.read_sql_query(query_area, engine)


#----------------------------------------------------------------------------------------------------
# UI Definition
#----------------------------------------------------------------------------------------------------

# Update the list of kingdoms to ensure it's consistent
kingdom_list = sorted(set(df_population['kingdom']).union(set(data_houses_kingdoms['Kingdom Name'])))

# Define the UI layout using ui.navset_tab and ui.nav_panel as positional arguments
app_ui = ui.page_fluid(
    ui.layout_sidebar(
        ui.sidebar(
            ui.h3("Filters"),
            ui.input_selectize("kingdoms", "Select Kingdom(s)", choices=kingdom_list, multiple=True),
            ui.input_select("plot_type", "Select Plot Type", ["Bar Plot", "Pie Chart"])
        ),
        ui.navset_tab(
            ui.nav_panel(
                "Overview",
                ui.h1("Game of Thrones Dashboard"),
                ui.row(
                    ui.column(6, ui.h3("Total Houses"), ui.output_text_verbatim("total_houses")),
                    ui.column(6, ui.h3("Total Population"), ui.output_text_verbatim("total_population"))
                )
            ),
            ui.nav_panel("Houses", ui.h1("Number of Houses per Kingdom"), output_widget("house_count_plot")),
            ui.nav_panel("Population", ui.h1("Population and Area by Kingdom"),
                         output_widget("population_plot"), output_widget("area_plot")),
            ui.nav_panel("Map", ui.h1("Map of Westeros"), ui.output_ui("map"))
        )
    )
)


#----------------------------------------------------------------------------------------------------
# Server Logic and Plot Rendering
#----------------------------------------------------------------------------------------------------

def server(input, output, session):
    # Total Houses
    @output
    @render.text
    def total_houses():
        total = data_houses_kingdoms['House Name'].nunique()
        return f"Total Houses: {total}"

    # Total Population
    @output
    @render.text
    def total_population():
        total = df_population['total_population'].sum()
        return f"Total Population: {total}"

    # Kingdom color mapping
    kingdom_color_mapping = {
        "The North": "#1f77b4", "The Reach": "#ff7f0e", "Dorne": "#2ca02c",
        "The Westerlands": "#d62728", "The Riverlands": "#9467bd", "The Vale": "#8c564b",
        "Iron Islands": "#e377c2", "The Stormlands": "#7f7f7f", "The Crownlands": "#ffff00",
        "Gift": "#17becf", "Other Regions": "#b5b5b5"
    }

    # Update the house count plot
    @output
    @render_widget
    def house_count_plot():
        selected_kingdoms = input.kingdoms()
        filtered_data = house_counts[house_counts['Kingdom Name'].isin(selected_kingdoms)] if selected_kingdoms else house_counts
        fig = px.bar(filtered_data, x='Kingdom Name', y='Number of Houses', color='Kingdom Name', title='Number of Houses per Kingdom',
                     color_discrete_map=kingdom_color_mapping) if input.plot_type() == "Bar Plot" else px.pie(
                     filtered_data, names='Kingdom Name', values='Number of Houses', color='Kingdom Name', title='Number of Houses per Kingdom',
                     color_discrete_map=kingdom_color_mapping)
        fig.update_layout(height=400)
        return fig

    # Update the population plot
    @output
    @render_widget
    def population_plot():
        selected_kingdoms = input.kingdoms()
        filtered_data = df_population[df_population['kingdom'].isin(selected_kingdoms)] if selected_kingdoms else df_population
        fig = px.bar(filtered_data, x='kingdom', y='total_population', color='kingdom', title='Total Population by Kingdom',
                     color_discrete_map=kingdom_color_mapping) if input.plot_type() == "Bar Plot" else px.pie(
                     filtered_data, names='kingdom', values='total_population', color='kingdom', title='Total Population by Kingdom',
                     color_discrete_map=kingdom_color_mapping)
        fig.update_layout(height=400)
        return fig

    # Update the area plot
    @output
    @render_widget
    def area_plot():
        selected_kingdoms = input.kingdoms()
        filtered_data = df_area[df_area['kingdom'].isin(selected_kingdoms)] if selected_kingdoms else df_area
        fig = px.bar(filtered_data, x='kingdom', y='area_km2', color='kingdom', title='Area of Kingdoms (km²)',
                     color_discrete_map=kingdom_color_mapping) if input.plot_type() == "Bar Plot" else px.pie(
                     filtered_data, names='kingdom', values='area_km2', color='kingdom', title='Area of Kingdoms (km²)',
                     color_discrete_map=kingdom_color_mapping)
        fig.update_layout(height=400)
        return fig


#----------------------------------------------------------------------------------------------------
# Map Rendering Logic
#----------------------------------------------------------------------------------------------------

    @output
    @render.ui
    def map():
        selected_kingdoms = input.kingdoms()

        # Fetch data for the map
        query_locations = """
        SELECT gid, name, type, summary, ST_AsText(geog) as geom_wkt
        FROM atlas.locations
        """
        location_df = pd.read_sql_query(query_locations, engine)

        query_kingdoms = """
        SELECT gid, name, claimedby, summary, ST_AsText(geog) as geom_wkt
        FROM atlas.kingdoms
        """
        kingdom_df = pd.read_sql_query(query_kingdoms, engine)

        query_houses = """
        SELECT gid, name, type, summary, ST_AsText(geog) as geom_wkt
        FROM atlas.locations
        WHERE type IN ('Castle', 'City')
        """
        houses_df = pd.read_sql_query(query_houses, engine)

        # Convert WKT to geometries
        location_df['geometry'] = location_df['geom_wkt'].apply(wkt.loads)
        location_gdf = gpd.GeoDataFrame(location_df, geometry='geometry', crs='EPSG:4326')

        kingdom_df['geometry'] = kingdom_df['geom_wkt'].apply(wkt.loads)
        kingdom_gdf = gpd.GeoDataFrame(kingdom_df, geometry='geometry', crs='EPSG:4326')

        houses_df['geometry'] = houses_df['geom_wkt'].apply(wkt.loads)
        houses_gdf = gpd.GeoDataFrame(houses_df, geometry='geometry', crs='EPSG:4326')

        # Assign random population values for demonstration
        np.random.seed(42)
        houses_gdf['population'] = np.random.randint(100, 5000, size=len(houses_gdf))

        # Filter kingdoms based on selected kingdoms
        if selected_kingdoms:
            kingdom_gdf = kingdom_gdf[kingdom_gdf['name'].isin(selected_kingdoms)]
        else:
            selected_kingdoms = kingdom_gdf['name'].tolist()  # All kingdoms

        # Assign colors to each kingdom using a colormap
        n = len(kingdom_gdf)
        if n > 0:
            colormap = cm.get_cmap('rainbow', n)
            kingdom_gdf['color'] = [colors.rgb2hex(colormap(i / n)) for i in range(n)]
        else:
            kingdom_gdf['color'] = 'gray'

        # Calculate the center of the map
        if not kingdom_gdf.empty:
            center = kingdom_gdf.geometry.unary_union.centroid.coords[:][0]  # (lon, lat) tuple
        else:
            center = location_gdf.geometry.unary_union.centroid.coords[:][0]

        # Create the folium map centered on the calculated centroid with tiles=None
        m = folium.Map(
            location=[center[1], center[0]],  # Folium uses [lat, lon]
            zoom_start=5,
            tiles=None  # Disable default tiles
        )

        # Add custom tile layer
        folium.TileLayer(
            tiles='https://cartocdn-gusc.global.ssl.fastly.net/ramirocartodb/api/v1/map/named/'
                  'tpl_756aec63_3adb_48b6_9d14_331c6cbc47cf/all/{z}/{x}/{y}.png',
            attr='CartoDB',
            name='CartoDB',
            overlay=False,
            control=False
        ).add_to(m)

        # Add polygons for kingdoms
        folium.GeoJson(
            kingdom_gdf,
            name='Kingdoms',
            style_function=lambda feature: {
                'fillColor': feature['properties']['color'],
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.5,
                'opacity': 1,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['name', 'claimedby'],
                aliases=['Name:', 'Claimed By:']
            ),
            popup=folium.GeoJsonPopup(
                fields=['name', 'claimedby', 'summary'],
                aliases=['Name:', 'Claimed By:', 'Summary:'],
                max_width=300
            )
        ).add_to(m)

        # Define color and icon mappings
        color_mapping = {
            'Castle': 'red',
            'City': 'blue',
            'Fortress': 'green',
            'Keep': 'orange',
            # Add more types and colors as needed
        }

        icon_mapping = {
            'Castle': 'shield-alt',
            'City': 'building',
            'Fortress': 'archway',  # Ensure this icon is available in the free version
            'Keep': 'home',
            # Add more types and icons as needed
        }

        # Add markers for locations with differentiated icons and colors
        marker_cluster = MarkerCluster(name='Locations').add_to(m)
        for idx, row in location_gdf.iterrows():
            location_type = row['type']
            marker_color = color_mapping.get(location_type, 'gray')
            icon_name = icon_mapping.get(location_type, 'info-circle')

            popup_content = f"""
            <b>Name:</b> {row['name']}<br>
            <b>Type:</b> {row['type']}<br>
            <b>Summary:</b> {row['summary'] or 'No summary available.'}
            """

            # Use built-in Folium icons with Font Awesome
            icon = folium.Icon(icon=icon_name, prefix='fa', icon_color='white', color=marker_color)

            try:
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=icon
                ).add_to(marker_cluster)
            except ValueError:
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=folium.Icon(icon='info-circle', prefix='fa', icon_color='white', color='gray')
                ).add_to(marker_cluster)

        # Add markers for houses with population
        houses_layer = folium.FeatureGroup(name='Houses').add_to(m)
        pop_min = houses_gdf['population'].min()
        pop_max = houses_gdf['population'].max()

        def get_radius(pop):
            if pop_max > pop_min:
                return 5 + (pop - pop_min) / (pop_max - pop_min) * 10
            else:
                return 10

        for idx, row in houses_gdf.iterrows():
            pop = row['population']
            radius = get_radius(pop)
            popup_content = f"""
            <b>Name:</b> {row['name']}<br>
            <b>Population:</b> {pop}<br>
            <b>Type:</b> {row['type']}<br>
            <b>Summary:</b> {row['summary'] or 'No summary available.'}
            """
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=radius,
                color='blue',
                fill=True,
                fill_color='blue',
                fill_opacity=0.6,
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(houses_layer)

        # Add layer control
        folium.LayerControl().add_to(m)

        # Return the HTML representation of the map
        return ui.HTML(m._repr_html_())


#----------------------------------------------------------------------------------------------------
# App Initialization and Execution
#----------------------------------------------------------------------------------------------------

# Create the Shiny app
app = App(app_ui, server)

# Run the app
if __name__ == "main":
    app.run()