import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_FILE = 'credit_scores.db'

# Function to initialize the database
def initialize_database():
    # Check if the database file exists
    if not os.path.exists(DB_FILE):
        # Create a new database if it doesn't exist
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


# API endpoint to get credit score
@app.route('/get_credit_score', methods=['POST'])
def get_credit_score():
    data = request.json
    pan = data.get('pan_number')
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute('SELECT credit_score FROM credit_scores WHERE pan_number = ?', (pan,))
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify({"credit_score": row[0]})
    else:
        return jsonify({"error": "PAN number not found"}), 404


# API endpoint to add or update credit score
@app.route('/add_credit_score', methods=['POST'])
def add_credit_score():
    data = request.json
    pan = data.get('pan_number')
    score = data.get('credit_score')
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        INSERT OR REPLACE INTO credit_scores (pan_number, credit_score)
        VALUES (?, ?)
    ''', (pan, score))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Initialize the database (create if it doesn't exist)
    initialize_database()
    app.run(port=5001)
