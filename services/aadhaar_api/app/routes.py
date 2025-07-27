import os
import sqlite3
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

DB_FILE = 'aadhaar_details.db'

class AadhaarRequest(BaseModel):
    aadhaar_number: str

class AadhaarDetails(BaseModel):
    aadhaar_number: str
    name: str
    age: int
    gender: str
    address: str
    dob: str

def initialize_database():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS aadhaar_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aadhaar_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                address TEXT NOT NULL,
                dob TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print(f"New database '{DB_FILE}' created successfully.")
    else:
        print(f"Database '{DB_FILE}' already exists. Connecting to it.")

@router.post("/get_aadhaar_details")
def get_aadhaar_details(payload: AadhaarRequest):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute('''
        SELECT name, age, gender, address, dob 
        FROM aadhaar_details WHERE aadhaar_number = ?
    ''', (payload.aadhaar_number,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "name": row[0],
            "age": row[1],
            "gender": row[2],
            "address": row[3],
            "dob": row[4]
        }
    else:
        raise HTTPException(status_code=404, detail="Aadhaar number not found")

@router.post("/add_aadhaar_details")
def add_aadhaar_details(payload: AadhaarDetails):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        INSERT OR REPLACE INTO aadhaar_details 
        (aadhaar_number, name, age, gender, address, dob)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        payload.aadhaar_number,
        payload.name,
        payload.age,
        payload.gender,
        payload.address,
        payload.dob
    ))
    conn.commit()
    conn.close()
    return {"status": "success"}
