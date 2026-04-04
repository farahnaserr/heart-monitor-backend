from fastapi import FastAPI
from pydantic import BaseModel
import mysql.connector
import os

app = FastAPI()

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
# DATA MODEL
# =========================
class SensorData(BaseModel):
    patient_id: int
    timestamp: str
    ecg: float | None = None
    heart_rate: int | None = None
    spo2: int | None = None
    temperature: float | None = None


# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"message": "Backend is running 🚀"}


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