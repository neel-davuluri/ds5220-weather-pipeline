import os
import boto3
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone

# Config
LOCATION_ID = "charlottesville_va"
LAT = 38.0293
LON = -78.4767
BUCKET = os.environ.get("S3_BUCKET", "neel-ds5220-weather")
REGION = "us-east-1"
TABLE = "weather-tracking"

def fetch_weather():
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&current=temperature_2m,wind_speed_10m,precipitation,cloud_cover"
        f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()["current"]
    return {
        "temp_f": data["temperature_2m"],
        "wind_mph": data["wind_speed_10m"],
        "precip_mm": data["precipitation"],
        "cloud_pct": data["cloud_cover"],
    }

def write_dynamo(ts, weather):
    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = ddb.Table(TABLE)
    table.put_item(Item={
        "location_id": LOCATION_ID,
        "timestamp": ts,
        "temp_f": str(weather["temp_f"]),
        "wind_mph": str(weather["wind_mph"]),
        "precip_mm": str(weather["precip_mm"]),
        "cloud_pct": str(weather["cloud_pct"]),
    })

def read_history():
    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = ddb.Table(TABLE)
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("location_id").eq(LOCATION_ID)
    )
    items = resp["Items"]
    df = pd.DataFrame(items)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    for col in ["temp_f", "wind_mph", "precip_mm", "cloud_pct"]:
        df[col] = df[col].astype(float)
    return df

def plot_and_upload(df):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Charlottesville, VA — Weather Tracker", fontsize=14)

    pairs = [
        (axes[0,0], "temp_f", "Temperature (°F)", "tomato"),
        (axes[0,1], "wind_mph", "Wind Speed (mph)", "steelblue"),
        (axes[1,0], "precip_mm", "Precipitation (mm)", "mediumseagreen"),
        (axes[1,1], "cloud_pct", "Cloud Cover (%)", "slategray"),
    ]

    for ax, col, title, color in pairs:
        ax.plot(df["timestamp"], df[col], color=color, linewidth=1.5)
        ax.set_title(title)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("/tmp/plot.png", dpi=150)
    plt.close()

    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file("/tmp/plot.png", BUCKET, "plot.png",
                   ExtraArgs={"ContentType": "image/png"})

    df.to_csv("/tmp/data.csv", index=False)
    s3.upload_file("/tmp/data.csv", BUCKET, "data.csv",
                   ExtraArgs={"ContentType": "text/csv"})

def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    weather = fetch_weather()
    write_dynamo(ts, weather)
    print(f"Charlottesville | temp={weather['temp_f']}°F | wind={weather['wind_mph']}mph | precip={weather['precip_mm']}mm | cloud={weather['cloud_pct']}%")
    df = read_history()
    plot_and_upload(df)
    print(f"Plot uploaded — {len(df)} data points")

if __name__ == "__main__":
    main()
