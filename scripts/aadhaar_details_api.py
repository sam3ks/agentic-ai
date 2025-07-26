import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_FILE = 'aadhaar_details.db'

# Function to initialize the database
def initialize_database():
    # Check if the database file exists
    if not os.path.exists(DB_FILE):
        # Create a new database if it doesn't exist
        conn = sqlite3.connect(DB_FILE)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS aadhaar_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aadhaar_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                marital_status TEXT NOT NULL,
                gender TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print(f"New database '{DB_FILE}' created successfully.")
    else:
        print(f"Database '{DB_FILE}' already exists. Connecting to it.")


# API endpoint to get personal details by Aadhaar number
@app.route('/get_aadhaar_details', methods=['POST'])
def get_aadhaar_details():
    data = request.json
    aadhaar = data.get('aadhaar_number')
    
    if not aadhaar:
        return jsonify({"error": "Aadhaar number is required"}), 400
    
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute('''
        SELECT name, age, marital_status, gender 
        FROM aadhaar_details WHERE aadhaar_number = ?
    ''', (aadhaar,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            "name": row[0],
            "age": row[1],
            "marital_status": row[2],
            "gender": row[3]
        })
    else:
        return jsonify({"error": "Aadhaar number not found"}), 404


# API endpoint to add or update personal details
@app.route('/add_aadhaar_details', methods=['POST'])
def add_aadhaar_details():
    data = request.json
    aadhaar = data.get('aadhaar_number')
    name = data.get('name')
    age = data.get('age')
    marital_status = data.get('marital_status')
    gender = data.get('gender')
    
    if not all([aadhaar, name, age, marital_status, gender]):
        return jsonify({"error": "Required fields: aadhaar_number, name, age, marital_status, gender"}), 400
    
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        INSERT OR REPLACE INTO aadhaar_details 
        (aadhaar_number, name, age, marital_status, gender)
        VALUES (?, ?, ?, ?, ?)
    ''', (aadhaar, name, age, marital_status, gender))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


if __name__ == '__main__':
    # Initialize the database (create if it doesn't exist)
    initialize_database()
    app.run(port=5002)  # Different port from credit score API
