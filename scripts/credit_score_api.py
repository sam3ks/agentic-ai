import os
import sqlite3
import logging
from flask import Flask, request, jsonify, g, abort
from flask_cors import CORS
import json

DB_FILE = os.getenv('DB_FILE', 'credit_scores.db')
PORT = int(os.getenv('PORT', 5001))

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def initialize_database():
    if not os.path.exists(DB_FILE):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS credit_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pan_number TEXT UNIQUE NOT NULL,
                    credit_score INTEGER NOT NULL CHECK(credit_score >= 0 AND credit_score <= 900)
                )
            ''')
            conn.commit()
        logging.info(f"Created new database '{DB_FILE}'")
    else:
        logging.info(f"Database '{DB_FILE}' already exists")

def log_request_details():
    try:
        body = request.get_json(silent=True)
        body_str = json.dumps(body) if body else "No JSON body"
    except Exception:
        body_str = "Invalid JSON body"

    logging.info(
        f"Request from {request.remote_addr} | "
        f"{request.method} {request.path} | "
        f"Body: {body_str}"
    )

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS if needed

    app.teardown_appcontext(close_db)

    @app.route('/get_credit_score', methods=['POST'])
    def get_credit_score():
        log_request_details()

        if not request.is_json:
            abort(400, description="Request must be JSON")
        data = request.get_json()
        pan = data.get('pan_number')
        if not pan or not isinstance(pan, str):
            abort(400, description="Invalid or missing 'pan_number'")

        db = get_db()
        cur = db.execute('SELECT credit_score FROM credit_scores WHERE pan_number = ?', (pan,))
        row = cur.fetchone()
        if row:
            return jsonify({"credit_score": row['credit_score']})
        else:
            return jsonify({"error": "PAN number not found"}), 404

    @app.route('/add_credit_score', methods=['POST'])
    def add_credit_score():
        log_request_details()

        if not request.is_json:
            abort(400, description="Request must be JSON")
        data = request.get_json()
        pan = data.get('pan_number')
        score = data.get('credit_score')

        if not pan or not isinstance(pan, str):
            abort(400, description="Invalid or missing 'pan_number'")
        if not isinstance(score, int) or not (0 <= score <= 900):
            abort(400, description="'credit_score' must be an integer between 0 and 900")

        db = get_db()
        try:
            db.execute('''
                INSERT INTO credit_scores (pan_number, credit_score)
                VALUES (?, ?)
                ON CONFLICT(pan_number) DO UPDATE SET credit_score=excluded.credit_score
            ''', (pan, score))
            db.commit()
        except sqlite3.Error as e:
            logging.error(f"DB error: {e}")
            return jsonify({"error": "Database error"}), 500

        return jsonify({"status": "success"})

    return app

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    initialize_database()
    app = create_app()
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
    logging.info(f"Credit Score API running on port {PORT}")