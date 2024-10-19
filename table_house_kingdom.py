from sqlalchemy import create_engine
import pandas as pd
from shiny import App, ui, render
import plotly.express as px
from shinywidgets import output_widget, render_widget

# Function to fetch the data from the database using SQLAlchemy engine
def fetch_houses_and_kingdoms():
    # Create the database engine
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    # Define the SQL query
    query = """
    SELECT 
        h.name AS house_name,
        k.name AS kingdom_name
    FROM 
        got.houses h
    JOIN 
        atlas.kingdoms k 
    ON 
        h.region = k.name;
    """

    # Execute the query and load the results into a DataFrame
    df = pd.read_sql_query(query, engine)

    # Remove the word "House" from the house names
    df["house_name"] = df["house_name"].str.replace("^House ", "", regex=True)

    # Rename the columns for better display
    df.columns = ["House Name", "Kingdom Name"]

    return df

# Fetch the data
data = fetch_houses_and_kingdoms()

# Calculate the number of houses per kingdom
house_counts = data.groupby("Kingdom Name").size().reset_index(name='Number of Houses')

# Define the Shiny UI
app_ui = ui.page_fluid(
    ui.h2("Number of Houses per Kingdom"),
    output_widget("house_count_plot")
)

# Define the Shiny server logic
def server(input, output, session):
    @output
    @render_widget
    def house_count_plot():
        # Create a bar chart of the number of houses per kingdom
        fig = px.bar(house_counts, x='Kingdom Name', y='Number of Houses',
                     title='Number of Houses per Kingdom')
        fig.update_layout(xaxis_title='Kingdom Name', yaxis_title='Number of Houses')
        return fig

# Create the Shiny app
app = App(app_ui, server)

# Run the app
if _name_ == "_main_":
    app.run()