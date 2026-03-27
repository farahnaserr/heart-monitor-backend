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
class ECGData(BaseModel):
    patient_id: int
    ecg: float
    timestamp: str


# =========================
# ROOT (TEST)
# =========================
@app.get("/")
def root():
    return {"message": "Backend is running 🚀"}


# =========================
# POST ECG DATA
# =========================
@app.post("/ecg")
def receive_ecg(data: ECGData):
    if conn is None or cursor is None:
        return {"error": "Database not connected"}

    try:
        query = "INSERT INTO ecg_data (patient_id, ecg, timestamp) VALUES (%s, %s, %s)"
        values = (data.patient_id, data.ecg, data.timestamp)

        cursor.execute(query, values)
        conn.commit()

        return {"message": "Data saved"}

    except Exception as e:
        return {"error": str(e)}


# =========================
# GET ECG DATA
# =========================
@app.get("/ecg")
def get_ecg():
    if conn is None or cursor is None:
        return {"error": "Database not connected"}

    try:
        cursor.execute("SELECT * FROM ecg_data")
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "patient_id": row[1],
                "ecg": row[2],
                "timestamp": row[3]
            })

        return {"data": data}

    except Exception as e:
        return {"error": str(e)}