from sqlalchemy import create_engine
from shiny import App, render, ui
import pandas as pd
import geopandas as gpd
from shapely import wkt
import folium
from folium.plugins import MarkerCluster
from matplotlib import cm, colors
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Fá allar breytur úr umhverfinu
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Define the UI
app_ui = ui.page_fluid(
    ui.h1("Westeros Map"),
    ui.output_ui("map")
)

# Define the server function
def server(input, output, session):

    @output
    @render.ui
    def map():
        # Connect to the PostgreSQL database using SQLAlchemy
        engine = create_engine(f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

        # Fetch data about locations in Westeros, including 'type' and 'summary' fields
        query_locations = """
        SELECT gid, name, type, summary, ST_AsText(geog) as geom_wkt
        FROM atlas.locations
        """
        location_df = pd.read_sql_query(query_locations, engine)

        # Fetch data about kingdoms in Westeros, including 'claimedby' and 'summary' fields
        query_kingdoms = """
        SELECT gid, name, claimedby, summary, ST_AsText(geog) as geom_wkt
        FROM atlas.kingdoms
        """
        kingdom_df = pd.read_sql_query(query_kingdoms, engine)

        # Fetch data about houses from locations where type is 'Castle' or 'City'
        query_houses = """
        SELECT gid, name, type, summary, ST_AsText(geog) as geom_wkt
        FROM atlas.locations
        WHERE type IN ('Castle', 'City')
        """
        houses_df = pd.read_sql_query(query_houses, engine)

        # Convert WKT to geometries for locations
        location_df['geometry'] = location_df['geom_wkt'].apply(wkt.loads)
        location_gdf = gpd.GeoDataFrame(location_df, geometry='geometry', crs='EPSG:4326')

        # Convert WKT to geometries for kingdoms
        kingdom_df['geometry'] = kingdom_df['geom_wkt'].apply(wkt.loads)
        kingdom_gdf = gpd.GeoDataFrame(kingdom_df, geometry='geometry', crs='EPSG:4326')

        # Convert WKT to geometries for houses
        houses_df['geometry'] = houses_df['geom_wkt'].apply(wkt.loads)
        houses_gdf = gpd.GeoDataFrame(houses_df, geometry='geometry', crs='EPSG:4326')

        # Assign random population values for demonstration
        np.random.seed(42)  # For reproducible results
        houses_gdf['population'] = np.random.randint(100, 5000, size=len(houses_gdf))

        # Assign colors to each kingdom
        n = len(kingdom_gdf)
        colormap = cm.get_cmap('rainbow', n)
        kingdom_gdf['color'] = [colors.rgb2hex(colormap(i / n)) for i in range(n)]

        # Calculate the center of the map
        center = location_gdf.geometry.unary_union.centroid

        # Create the folium map
        m = folium.Map(location=[center.y, center.x], zoom_start=5, tiles=None)

        # Add custom tile layer
        folium.TileLayer(
            tiles='https://cartocdn-gusc.global.ssl.fastly.net/ramirocartodb/api/v1/map/named/'
                  'tpl_756aec63_3adb_48b6_9d14_331c6cbc47cf/all/{z}/{x}/{y}.png',
            attr='CartoDB',
            name='CartoDB',
            overlay=False,
            control=False
        ).add_to(m)

        # Define a mapping from location types to icon names or custom icons
        type_icon_mapping = {
            'Castle': 'fa-fort-awesome',
            'City': 'fa-building',
            'Landmark': 'fa-map-pin',
            'Region': 'fa-globe',
            'Ruin': 'fa-university',
            'Town': 'fa-home'
        }

        # Add markers for locations with specific icons and include 'summary' in the popup
        marker_cluster = MarkerCluster(name='Locations').add_to(m)
        for idx, row in location_gdf.iterrows():
            popup_content = f"""
            <b>Name:</b> {row['name']}<br>
            <b>Type:</b> {row['type']}<br>
            <b>Summary:</b> {row['summary'] or 'No summary available.'}
            """
            location_type = row['type']
            icon_name = type_icon_mapping.get(location_type, 'fa-info-circle')  # default icon if type not found

            # Use built-in Folium icons with Font Awesome
            icon = folium.Icon(icon=icon_name, prefix='fa', icon_color='white', color='blue')

            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                popup=folium.Popup(popup_content, max_width=300),
                icon=icon
            ).add_to(marker_cluster)

        # Define style function for kingdoms
        def style_function(feature):
            return {
                'fillColor': feature['properties']['color'],
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.5,
                'opacity': 1,
            }

        # Prepare tooltip content to include 'name' and 'claimedby'
        kingdom_gdf['tooltip'] = kingdom_gdf.apply(
            lambda row: f"<b>Name:</b> {row['name']}<br><b>Claimed By:</b> {row['claimedby']}", axis=1
        )

        # Prepare popup content to include 'name', 'claimedby', and 'summary'
        kingdom_gdf['popup'] = kingdom_gdf.apply(
            lambda row: f"""
            <b>Name:</b> {row['name']}<br>
            <b>Claimed By:</b> {row['claimedby']}<br>
            <b>Summary:</b> {row['summary'] or 'No summary available.'}
            """, axis=1
        )

        # Add polygons for kingdoms with updated tooltip and popup
        folium.GeoJson(
            kingdom_gdf,
            name='Kingdoms',
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(fields=['tooltip'], aliases=[''], labels=False),
            popup=folium.GeoJsonPopup(fields=['popup'], labels=False, max_width=300)
        ).add_to(m)

        # Calculate radius for CircleMarkers based on population
        pop_min = houses_gdf['population'].min()
        pop_max = houses_gdf['population'].max()

        def get_radius(pop):
            # Normalize the population to a radius between 5 and 15
            return 5 + (pop - pop_min) / (pop_max - pop_min) * 10 if pop_max > pop_min else 10

        # Add markers for houses with CircleMarkers
        houses_layer = folium.FeatureGroup(name='Houses').add_to(m)
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

# Create the Shiny app
app = App(app_ui, server)

# Run the app
if __name__ == "_main_":
    app.run()