from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
import os
import numpy as np
from tensorflow.keras.models import load_model

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# AI MODEL SETTINGS
# =========================
THRESHOLD = 0.05

try:
    model = load_model("ecg_cnn_model_multi_balanced_norm.h5")
    print("AI model loaded successfully")
except Exception as e:
    print("AI model loading failed:", e)
    model = None

# =========================
# DATABASE CONNECTION
# =========================

try:
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    print("Connected to CLOUD MySQL")

except Exception as e:
    print("Cloud MySQL connection failed:", e)
    conn = None
    cursor = None

# =========================
# DATA MODELS
# =========================
class SensorData(BaseModel):
    patient_id: int
    timestamp: str
    ecg: float | None = None
    heart_rate: int | None = None
    spo2: int | None = None
    temperature: float | None = None

class ECGPredictRequest(BaseModel):
    patient_id: int
    timestamp: str
    ecg: list[float]
    heart_rate: int | None = None
    spo2: int | None = None
    temperature: float | None = None

# =========================
# AI FUNCTION
# =========================
def predict_ecg_signal(ecg_signal: list[float]):
    if model is None:
        return {"error": "AI model not loaded"}

    ecg = np.array(ecg_signal, dtype=float)

    if len(ecg) != 250:
        return {"error": "ECG signal must contain exactly 250 values"}

    mean = np.mean(ecg)
    std = np.std(ecg)

    if std == 0:
        return {"error": "Invalid ECG signal"}

    # Same normalization used in training
    ecg = (ecg - mean) / std
    ecg = ecg.reshape(1, 250, 1)

    p = float(model.predict(ecg, verbose=0)[0][0])

    if p >= THRESHOLD:
        status = "Abnormal"
    else:
        status = "Normal"

    return {
        "probability": round(p, 4),
        "status": status
    }

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"message": "Backend is running with AI 🚀"}

# =========================
# POST SENSOR DATA
# =========================
@app.post("/sensor-data")
def receive_sensor_data(data: SensorData):
    if conn is None or cursor is None:
        return {"error": "Database not connected"}

    try:
        query = """
        INSERT INTO ecg_data (patient_id, timestamp, ecg, heart_rate, spo2, temperature)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            data.patient_id,
            data.timestamp,
            data.ecg,
            data.heart_rate,
            data.spo2,
            data.temperature
        )

        cursor.execute(query, values)
        conn.commit()

        return {"message": "Sensor data saved"}

    except Exception as e:
        return {"error": str(e)}

# =========================
# ECG AI PREDICTION
# =========================
@app.post("/predict-ecg")
def predict_ecg(data: ECGPredictRequest):
    # 1. ECG AI prediction
    ecg_result = predict_ecg_signal(data.ecg)

    if "error" in ecg_result:
        return ecg_result

    # 2. Analyze other sensors
    vitals_result = analyze_vitals(
        heart_rate=data.heart_rate,
        spo2=data.spo2,
        temperature=data.temperature
    )

    # 3. Overall status
    overall_status = get_overall_status(
        ecg_status=ecg_result["status"],
        vitals=vitals_result
    )

    if conn is None or cursor is None:
        return {"error": "Database not connected"}

    try:
        query = """
        INSERT INTO ecg_predictions (patient_id, timestamp, probability, status)
        VALUES (%s, %s, %s, %s)
        """
        values = (
            data.patient_id,
            data.timestamp,
            ecg_result["probability"],
            overall_status
        )

        cursor.execute(query, values)
        conn.commit()

        return {
            "message": "Health analysis saved",
            "patient_id": data.patient_id,
            "timestamp": data.timestamp,
            "ecg_probability": ecg_result["probability"],
            "ecg_status": ecg_result["status"],
            "vitals": vitals_result,
            "overall_status": overall_status
        }

    except Exception as e:
        return {"error": str(e)}
# =========================
# GET ALL SENSOR DATA
# =========================
@app.get("/sensor-data")
def get_sensor_data():
    if conn is None or cursor is None:
        return {"error": "Database not connected"}

    try:
        cursor.execute("""
            SELECT id, patient_id, timestamp, ecg, heart_rate, spo2, temperature
            FROM ecg_data
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "patient_id": row[1],
                "timestamp": row[2],
                "ecg": row[3],
                "heart_rate": row[4],
                "spo2": row[5],
                "temperature": row[6]
            })

        return {"data": data}

    except Exception as e:
        return {"error": str(e)}

# =========================
# GET LATEST SENSOR DATA
# =========================
@app.get("/sensor-data/latest")
def get_latest_sensor_data():
    if conn is None or cursor is None:
        return {"error": "Database not connected"}

    try:
        cursor.execute("""
            SELECT id, patient_id, timestamp, ecg, heart_rate, spo2, temperature
            FROM ecg_data
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()

        if row is None:
            return {"message": "No data found"}

        return {
            "latest": {
                "id": row[0],
                "patient_id": row[1],
                "timestamp": row[2],
                "ecg": row[3],
                "heart_rate": row[4],
                "spo2": row[5],
                "temperature": row[6]
            }
        }

    except Exception as e:
        return {"error": str(e)}
    

 # =========================
# GET ECG AI PREDICTIONS
# =========================
@app.get("/ecg-predictions")
def get_ecg_predictions():
    if conn is None or cursor is None:
        return {"error": "Database not connected"}

    try:
        cursor.execute("""
            SELECT id, patient_id, timestamp, probability, status
            FROM ecg_predictions
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "patient_id": row[1],
                "timestamp": row[2],
                "probability": row[3],
                "status": row[4]
            })

        return {"data": data}

    except Exception as e:
        return {"error": str(e)}
    
    # =========================
# VITALS ANALYSIS (RULE-BASED)
# =========================
def analyze_vitals(heart_rate=None, spo2=None, temperature=None):
    result = {}

    if temperature is not None:
        if temperature >= 38:
            result["temperature_status"] = "High"
        elif temperature < 35:
            result["temperature_status"] = "Low"
        else:
            result["temperature_status"] = "Normal"

    if heart_rate is not None:
        if heart_rate > 100:
            result["heart_rate_status"] = "High"
        elif heart_rate < 60:
            result["heart_rate_status"] = "Low"
        else:
            result["heart_rate_status"] = "Normal"

    if spo2 is not None:
        if spo2 < 95:
            result["spo2_status"] = "Low"
        else:
            result["spo2_status"] = "Normal"

    return result


# =========================
# OVERALL STATUS
# =========================
def get_overall_status(ecg_status=None, vitals=None):
    if vitals is None:
        vitals = {}

    if (
        ecg_status == "Abnormal" or
        vitals.get("temperature_status") == "High" or
        vitals.get("heart_rate_status") in ["High", "Low"] or
        vitals.get("spo2_status") == "Low"
    ):
        return "Warning"

    return "Normal"