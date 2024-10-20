import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from shiny import App, render, ui
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Access the variables using os.getenv
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Staðfestu að allar breytur séu settar
if not all([db_user, db_password, db_host, db_port, db_name]):
    raise ValueError("One or more environment variables are not set.")

# Tengja við gagnagrunninn með því að nota breyturnar
db_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
engine = create_engine(db_url)

# Fyrirspurn fyrir fólksfjölda eftir sjö konungsríkjum
query_population = """
SELECT 
    CASE 
        WHEN h.region IN ('The North', 'The Neck', 'Beyond the Wall') THEN 'Kingdom of the North'
        WHEN h.region IN ('The Vale') THEN 'Kingdom of the Mountain and the Vale'
        WHEN h.region IN ('Iron Islands', 'The Riverlands') THEN 'Kingdom of the Isles and the Riverlands'
        WHEN h.region IN ('The Westerlands') THEN 'Kingdom of the Rock'
        WHEN h.region IN ('The Stormlands', 'The Crownlands') THEN 'Kingdom of the Stormlands'
        WHEN h.region IN ('The Reach') THEN 'Kingdom of the Reach'
        WHEN h.region IN ('Dorne') THEN 'Principality of Dorne'
        ELSE 'Other Regions'
    END AS kingdom,
    COUNT(c.id) as total_population
FROM got.characters c
JOIN got.houses h ON c.id = h.id
GROUP BY kingdom;
"""

# Fyrirspurn fyrir flatarmál konungsríkjanna
query_area = """
SELECT
    k.name AS kingdom,
    ST_Area(k.geog::geography) / 1000000 AS area_km2  -- Reikna flatarmál í km²
FROM atlas.kingdoms k;
"""

# Hlaða gögnin í pandas DataFrames
df_population = pd.read_sql(query_population, engine)
df_area = pd.read_sql(query_area, engine)

colors = ['lightblue', 'green', 'coral', 'salmon', 'pink', 'gray', 'blue', 'yellow']

# Shiny UI hluti
app_ui = ui.page_fluid(
    ui.h2("Samanburður á Game of Thrones konungsríkjunum"),
    ui.row(
        ui.column(6, ui.output_plot("population_plot")),  # Súlurit fyrir fjölda fólks
        ui.column(6, ui.output_plot("area_plot"))         # Súlurit fyrir flatarmál
    )
)

# Shiny server hluti
def server(input, output, session):
    @output
    @render.plot
    def population_plot():
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(df_population['kingdom'], df_population['total_population'], color=colors[:len(df_population)])
        ax.set_xlabel('Konungsríki')
        ax.set_ylabel('Fjöldi fólks')
        ax.set_title('Fjöldi fólks eftir sjö konungsríkjum í Game of Thrones')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        return fig

    @output
    @render.plot
    def area_plot():
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(df_area['kingdom'], df_area['area_km2'], color=colors[:len(df_area)])
        ax.set_xlabel('Konungsríki')
        ax.set_ylabel('Flatarmál (km²)')
        ax.set_title('Flatarmál (km²) fyrir konungsríkin í Game of Thrones')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        return fig

# Búa til Shiny app
app = App(app_ui, server)

# Keyra shiny forritið
if __name__ == "_main_":
    app.run()