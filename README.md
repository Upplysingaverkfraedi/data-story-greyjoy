# Game of Thrones Dashboard

This project is a Shiny-based web application that displays information about the Game of Thrones universe, including the number of houses, population, and area of different kingdoms. It also features an interactive map to visualize various locations.

## Prerequisites

Before running the application, ensure that you have the following software installed:

1. **Python 3.8 or higher**: Make sure you have Python installed.

2. A code editor that supports Python development.

3. **Python Packages**: Install the required Python packages listed below.
      - shiny
      - pandas
      - geopandas
      - sqlalchemy
      - folium
      - shapely
      - plotly
      - matplotlib
      - dotenv

5. **Database Access**: Ensure you have access to the PostgreSQL database with the necessary schemas (`got` and `atlas`) set up. The database credentials should be stored in a `.env` file.

## Setup
Set Up the .env File

In the project directory, create a .env file with the following content:

```bash
DB_USER=<your_database_username>
DB_PASSWORD=<your_database_password>
DB_HOST=<database_host>
DB_PORT=<database_port>
DB_NAME=<database_name>
Replace <your_database_username>, <your_database_password>, <database_host>, <database_port>, and <database_name> with the actual database credentials.
```

## Running the code
Run the code using:
```bash
python <your_script_name>.py
```

After running the script, the app will be hosted on http://127.0.0.1:8000 by default. Open this URL in your web browser to view the dashboard.
