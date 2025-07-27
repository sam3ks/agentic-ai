import os
import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
DB_FILE = 'credit_scores.db'

class CreditScoreRequest(BaseModel):
    pan_number: str

class AddCreditScoreRequest(BaseModel):
    pan_number: str
    credit_score: int

def initialize_database():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS credit_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pan_number TEXT UNIQUE NOT NULL,
                credit_score INTEGER NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print(f"New database '{DB_FILE}' created successfully.")
    else:
        print(f"Database '{DB_FILE}' already exists. Connecting to it.")

@router.post("/get_credit_score")
def get_credit_score(payload: CreditScoreRequest):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute('SELECT credit_score FROM credit_scores WHERE pan_number = ?', (payload.pan_number,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {"credit_score": row[0]}
    else:
        raise HTTPException(status_code=404, detail="PAN number not found")

@router.post("/add_credit_score")
def add_credit_score(payload: AddCreditScoreRequest):
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        INSERT OR REPLACE INTO credit_scores (pan_number, credit_score)
        VALUES (?, ?)
    ''', (payload.pan_number, payload.credit_score))
    conn.commit()
    conn.close()
    return {"status": "success"}
