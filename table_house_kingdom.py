import psycopg2
import pandas as pd
from shiny import App, ui, render

# Database connection details
DB_HOST = "junction.proxy.rlwy.net"
DB_PORT = "55303"
DB_NAME = "railway"
DB_USER = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # Replace with your actual username
DB_PASSWORD = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # Replace with your actual password

# Function to fetch the data from the database
def fetch_houses_and_kingdoms():
    # Connect to the database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

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
    df = pd.read_sql_query(query, conn)

    # Close the connection
    conn.close()

    # Remove the word "House" from the house names
    df["house_name"] = df["house_name"].str.replace("^House ", "", regex=True)

    # Rename the columns for better display
    df.columns = ["House Name", "Kingdom Name"]

    return df

# Fetch the data
data = fetch_houses_and_kingdoms()

# Define the Shiny UI
app_ui = ui.page_fluid(
    ui.h2("Houses and Kingdoms"),
    ui.input_select("sort_by", "Sort by:", {"House Name": "House Name", "Kingdom Name": "Kingdom Name"}),
    ui.output_table("house_kingdom_table")
)

# Define the Shiny server logic
def server(input, output, session):
    @output
    @render.table
    def house_kingdom_table():
        # Sort the data based on the selected option
        sorted_data = data.sort_values(by=input.sort_by())
        # Return the sorted DataFrame as a table
        return sorted_data

# Create the Shiny app
app = App(app_ui, server)

# Run the app
if __name__ == "__main__":
    app.run()