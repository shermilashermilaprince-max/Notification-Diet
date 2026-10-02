from flask import Flask, render_template, jsonify
import pandas as pd
import os

app = Flask(__name__)

CSV_FILE = "data/notifications.csv"


def load_data():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()

    df = pd.read_csv(CSV_FILE)

    df["Date"] = pd.to_datetime(df["Date"])
    df["Time"] = pd.to_datetime(df["Time"], format="%H:%M").dt.time

    return df


def calculate_distraction_scores(df):

    scores = []

    for app_name, group in df.groupby("App"):

        total_notifications = len(group)

        # Frequency score
        frequency_score = min(total_notifications / len(df) * 100, 100)

        # Repeated notifications
        repeated = group["Notification Type"].duplicated().sum()
        repeated_score = min((repeated / max(total_notifications, 1)) * 100, 100)

        # Late night notifications
        late_night = sum(
            21 <= t.hour or t.hour < 6
            for t in group["Time"]
        )

        late_score = min(
            (late_night / max(total_notifications, 1)) * 100,
            100
        )

        # Interaction score
        interactions = (
            group["Interacted"]
            .astype(str)
            .str.lower()
            .eq("yes")
            .sum()
        )

        interaction_score = min(
            (interactions / max(total_notifications, 1)) * 100,
            100
        )

        # Final score
        score = (
            frequency_score * 0.30
            + repeated_score * 0.20
            + late_score * 0.20
            + interaction_score * 0.30
        )

        scores.append({
            "app": app_name,
            "score": round(score),
            "notifications": total_notifications
        })

    return sorted(
        scores,
        key=lambda x: x["score"],
        reverse=True
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():

    df = load_data()

    if df.empty:
        return jsonify({
            "total_notifications": 0,
            "total_apps": 0,
            "scores": [],
            "hours": [],
            "peak_hour": "No data",
            "night_percentage": 0
        })

    scores = calculate_distraction_scores(df)

    # Hour analysis
    hours = df["Time"].apply(lambda x: x.hour)
    hour_counts = hours.value_counts().sort_index()

    hour_data = [
        {
            "hour": int(hour),
            "count": int(count)
        }
        for hour, count in hour_counts.items()
    ]

    # Night notification percentage
    night_notifications = sum(
        (df["Time"].apply(lambda x: x.hour) >= 21) |
        (df["Time"].apply(lambda x: x.hour) < 6)
    )

    night_percentage = round(
        (night_notifications / len(df)) * 100
    )

    peak_hour = int(
        hour_counts.idxmax()
    )

    return jsonify({
        "total_notifications": len(df),
        "total_apps": df["App"].nunique(),
        "scores": scores,
        "hours": hour_data,
        "peak_hour": f"{peak_hour}:00",
        "night_percentage": night_percentage
    })


if __name__ == "__main__":
    app.run(debug=True)