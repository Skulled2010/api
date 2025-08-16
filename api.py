from flask import Flask, jsonify, request
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
import traceback

app = Flask(__name__)

# ENV variables
DATABASE_URL = os.environ.get("DATABASE_URL")
MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set!")

# Connect DB helper
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Create table if not exists
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key TEXT PRIMARY KEY,
                    expire_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    users TEXT[] DEFAULT '{}',
                    max_users INT NOT NULL
                );
            """)
        conn.commit()

init_db()

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello! This is your API."})

@app.route('/api/<key>', methods=['GET'])
def check_key(key):
    try:
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        user = request.args.get("user")

        if not user:
            return jsonify({"valid": False, "message": "Missing required parameter: user"}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM api_keys WHERE key = %s", (key,))
                row = cur.fetchone()

        if not row:
            return jsonify({"valid": False, "message": "Key is invalid."})

        key_time = row["expire_at"]
        # Fix offset-naive vs offset-aware
        if key_time.tzinfo is None:
            key_time = key_time.replace(tzinfo=timezone.utc)

        time_remaining = (key_time - current_time).total_seconds()

        if time_remaining <= 0:
            return jsonify({"valid": False, "message": "Key has expired."})

        users = row["users"] or []
        max_users = row["max_users"]

        if user in users:
            return jsonify({
                "valid": True,
                "time_remaining": time_remaining,
                "users": users,
                "max_users": max_users
            })

        if len(users) < max_users:
            users.append(user)
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE api_keys SET users = %s WHERE key = %s",
                        (users, key)
                    )
                conn.commit()
            return jsonify({
                "valid": True,
                "time_remaining": time_remaining,
                "users": users,
                "max_users": max_users
            })

        return jsonify({"valid": False, "message": "Max user limit reached."})

    except Exception as e:
        print(f"[ERROR] Internal error in check_key: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"valid": False, "message": f"Internal server error: {str(e)}"}), 500

@app.route('/api/add-key', methods=['GET'])
def add_new_key():
    try:
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        control_key = request.args.get("control_key")
        new_key = request.args.get("key")
        expire_months = request.args.get("expire_months")
        max_users = request.args.get("max_users")

        if not control_key or not new_key or expire_months is None or max_users is None:
            return jsonify({"valid": False, "message": "Required parameters: control_key, key, expire_months, max_users."}), 400

        if control_key != MAIN_CONTROL_KEY:
            return jsonify({"valid": False, "message": "Main control key is invalid."})

        expire_months_float = float(expire_months)
        max_users_int = int(max_users)

        if expire_months_float <= 0 or max_users_int <= 0:
            return jsonify({"valid": False, "message": "Expiration time and max_users must be greater than 0."})

        expiration_time = current_time + timedelta(days=expire_months_float * 30)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM api_keys WHERE key = %s", (new_key,))
                if cur.fetchone():
                    return jsonify({"valid": False, "message": "Key already exists."}), 400

                cur.execute(
                    "INSERT INTO api_keys (key, expire_at, users, max_users) VALUES (%s, %s, %s, %s)",
                    (new_key, expiration_time, [], max_users_int)
                )
            conn.commit()

        return jsonify({
            "valid": True,
            "message": "New key has been added to database.",
            "new_key": new_key,
            "expiration_time": expiration_time.isoformat(),
            "max_users": max_users_int,
            "users": []
        })

    except ValueError:
        return jsonify({"valid": False, "message": "expire_months and max_users must be valid numbers."}), 400
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        print(traceback.format_exc())
        return jsonify({"valid": False, "message": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

        print(traceback.format_exc())
        return jsonify({"valid": False, "message": f"Internal server error: {str(e)}"}), 500

