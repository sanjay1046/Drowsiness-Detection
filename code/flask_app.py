from flask import Flask, render_template_string
import requests

app = Flask(__name__)

# ThingSpeak API details
CHANNEL_ID = "3134249"
READ_API_KEY = "1KN3PY9J9M7F788C"
URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds/last.json"

# Modern UI + Countdown Timer
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Driver Drowsiness Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: #fff;
            margin: 0;
            padding: 0;
        }
        header {
            text-align: center;
            padding: 30px 10px;
            background-color: rgba(0,0,0,0.3);
            box-shadow: 0 2px 5px rgba(0,0,0,0.4);
        }
        header h1 {
            margin: 0;
            font-size: 2.2rem;
        }
        main {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            padding: 40px 20px;
            gap: 20px;
        }
        .card {
            background: #fff;
            color: #222;
            border-radius: 16px;
            width: 240px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: transform 0.2s ease-in-out;
        }
        .card:hover { transform: translateY(-6px); }
        .status-yes { color: #27ae60; font-weight: bold; font-size: 1.6rem; }
        .status-no { color: #c0392b; font-weight: bold; font-size: 1.6rem; }
        .title { font-size: 1.1rem; margin-bottom: 10px; color: #444; }
        footer {
            text-align: center;
            padding: 15px;
            font-size: 0.9rem;
            color: #ddd;
            background-color: rgba(0,0,0,0.2);
        }
        .metrics {
            margin-top: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 15px 25px;
            display: inline-block;
        }
        .metric-value {
            font-weight: bold;
            color: #ffeb3b;
        }
        #countdown {
            font-size: 1.2rem;
            color: #ffeb3b;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <header>
        <h1>🚗 Driver Drowsiness Monitoring Dashboard</h1>
    </header>

    <main>
        <div class="card">
            <div class="title">Drowsy</div>
            <div class="{{ drowsy_class }}">{{ drowsy }}</div>
        </div>
        <div class="card">
            <div class="title">Yawning</div>
            <div class="{{ yawning_class }}">{{ yawning }}</div>
        </div>
        <div class="card">
            <div class="title">Distracted</div>
            <div class="{{ distracted_class }}">{{ distracted }}</div>
        </div>
        <div class="card">
            <div class="title">Alert</div>
            <div class="{{ alert_class }}">{{ alert }}</div>
        </div>
    </main>

    <div style="text-align:center;">
        <div class="metrics">
            <p>
                EAR: <span class="metric-value">{{ ear }}</span> &nbsp;&nbsp;
                MAR: <span class="metric-value">{{ mar }}</span> &nbsp;&nbsp;
                ENED: <span class="metric-value">{{ ened }}</span>
            </p>
            <div id="countdown">🔄 Refreshing in <span id="timer">15</span> seconds...</div>
        </div>
    </div>

    <footer>
        Powered by ThingSpeak & Flask
    </footer>

    <script>
        // Countdown timer logic
        let timeLeft = 15;
        const timerEl = document.getElementById("timer");

        const countdown = setInterval(() => {
            timeLeft--;
            timerEl.textContent = timeLeft;
            if (timeLeft <= 0) {
                clearInterval(countdown);
                window.location.reload(); // reload when timer hits 0
            }
        }, 1000);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    try:
        response = requests.get(URL, params={'api_key': READ_API_KEY})
        response.raise_for_status()
        data = response.json()

        ear = float(data.get('field1', 0))
        mar = float(data.get('field2', 0))
        ened = float(data.get('field3', 0))

        is_drowsy = ear < 0.20
        is_yawning = mar > 0.60
        is_distracted = ened > 8.0
        is_alert = not (is_drowsy or is_yawning or is_distracted)

        def yn(flag): return "YES" if flag else "NO"
        def cls(flag): return "status-yes" if flag else "status-no"

        return render_template_string(
            HTML,
            ear=f"{ear:.2f}",
            mar=f"{mar:.2f}",
            ened=f"{ened:.2f}",
            drowsy=yn(is_drowsy),
            yawning=yn(is_yawning),
            distracted=yn(is_distracted),
            alert=yn(is_alert),
            drowsy_class=cls(is_drowsy),
            yawning_class=cls(is_yawning),
            distracted_class=cls(is_distracted),
            alert_class=cls(is_alert)
        )

    except Exception as e:
        return f"<h3 style='color:red; text-align:center;'>Error fetching data: {e}</h3>"

if __name__ == "__main__":
    app.run(debug=True)
