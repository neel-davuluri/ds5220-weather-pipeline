# DS5220 Weather Pipeline

## Data Source
This pipeline collects hourly weather data for Charlottesville, VA using the [Open-Meteo API](https://open-meteo.com/). Open-Meteo is a free, no-key-required weather API that returns current conditions including temperature, wind speed, precipitation, and cloud cover for any latitude/longitude.

## Scheduled Process
A Kubernetes CronJob runs `collect.py` once per hour. On each run, the script fetches current weather conditions from Open-Meteo, writes the reading to a DynamoDB table (`weather-tracking`) with a timestamp, reads the full history back from DynamoDB, generates an updated 4-panel time-series plot, and uploads both the plot and a CSV of all data to a public S3 website bucket.

## Output
- **plot.png** — a 4-panel time-series chart showing temperature (°F), wind speed (mph), precipitation (mm), and cloud cover (%) over the full collection window
- **data.csv** — a flat CSV file containing all collected readings with columns: `location_id`, `timestamp`, `temp_f`, `wind_mph`, `precip_mm`, `cloud_pct`
