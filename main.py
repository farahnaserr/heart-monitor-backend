from fastapi import FastAPI
from pydantic import BaseModel
import mysql.connector

app = FastAPI()

# connect to MySQL
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root12345",   # replace with your password if needed
        database="heart_monitoring"
    )

    cursor = conn.cursor()
    print("Connected to MySQL")

except:
    print("MySQL connection failed (expected on Render)")
    conn = None
    cursor = None


class ECGData(BaseModel):
    patient_id: int
    ecg: float
    timestamp: str

@app.get("/")
def root():
    return {"message": "Backend + MySQL connected"}

@app.post("/ecg")
def receive_ecg(data: ECGData):
    query = "INSERT INTO ecg_data (patient_id, ecg, timestamp) VALUES (%s, %s, %s)"
    values = (data.patient_id, data.ecg, data.timestamp)

    cursor.execute(query, values)
    conn.commit()

    return {"status": "saved to MySQL"}
@app.get("/ecg")
def get_all_ecg():
    cursor.execute("SELECT * FROM ecg_data")
    rows = cursor.fetchall()
    return {"data": rows}

@app.get("/ecg/latest")
def get_latest_ecg():
    cursor.execute("SELECT * FROM ecg_data ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    return {"latest": row}