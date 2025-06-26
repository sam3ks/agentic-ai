import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('credit_scores.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/get_credit_score', methods=['POST'])
def get_credit_score():
    pan = request.json.get('pan_number')
    aadhaar = request.json.get('aadhaar_number')
    conn = get_db_connection()
    if pan:
        cur = conn.execute('SELECT credit_score FROM credit_scores WHERE pan_number = ?', (pan,))
    elif aadhaar:
        cur = conn.execute('SELECT credit_score FROM credit_scores WHERE aadhaar_number = ?', (aadhaar,))
    else:
        conn.close()
        return jsonify({'error': 'No identifier provided'}), 400
    row = cur.fetchone()
    conn.close()
    score = row['credit_score'] if row else 600  # Default if not found
    return jsonify({'credit_score': score})

@app.route('/add_credit_score', methods=['POST'])
def add_credit_score():
    pan = request.json.get('pan_number')
    aadhaar = request.json.get('aadhaar_number')
    score = request.json.get('credit_score')
    conn = get_db_connection()
    conn.execute(
        'INSERT OR REPLACE INTO credit_scores (pan_number, aadhaar_number, credit_score) VALUES (?, ?, ?)',
        (pan, aadhaar, score)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    # Run this once to create the table if it doesn't exist
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS credit_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pan_number TEXT UNIQUE,
        aadhaar_number TEXT UNIQUE,
        credit_score INTEGER NOT NULL
    )''')
    conn.close()
    app.run(port=5001)
