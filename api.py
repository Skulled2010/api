from flask import Flask, jsonify, request
import os
import json
import requests
from datetime import datetime, timedelta, UTC
import traceback

app = Flask(__name__)

# Load API keys
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))

# Control key
MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

# Render API info
RENDER_API_KEY = os.environ.get("RENDER_API_KEY")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID")

print(f"[DEBUG] RENDER_API_KEY: {RENDER_API_KEY}")
print(f"[DEBUG] RENDER_SERVICE_ID: {RENDER_SERVICE_ID}")

def update_render_env(api_keys_list):
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        return False, "Missing RENDER_API_KEY or RENDER_SERVICE_ID"

    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = [{
        "key": "API_KEYS",
        "value": json.dumps(api_keys_list, ensure_ascii=False)
    }]
    
    try:
        resp = requests.put(url, headers=headers, data=json.dumps(data), timeout=15)
        resp.raise_for_status()
        return True, None
    except requests.exceptions.RequestException as e:
        return False, str(e)

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello! This is your API."})

@app.route('/api/<key>', methods=['GET'])
def check_key(key):
    current_time = datetime.now(UTC)
    user = request.args.get("user")

    if not user:
        return jsonify({"valid": False, "message": "Missing required parameter: user"}), 400

    global api_keys
    for item in api_keys:
        if item.get("key") == key:
            # Parse expiration time
            key_time = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
            time_remaining = (key_time - current_time).total_seconds()

            if time_remaining <= 0:
                return jsonify({"valid": False, "message": "Key has expired."})

            # Ensure 'users' and 'max_users' exist
            item.setdefault("users", [])
            item.setdefault("max_users", 1)

            # If user already in list → allow
            if user in item["users"]:
                return jsonify({
                    "valid": True,
                    "time_remaining": time_remaining,
                    "users": item["users"],
                    "max_users": item["max_users"]
                })

            # If room not full → add user
            if len(item["users"]) < item["max_users"]:
                item["users"].append(user)
                update_render_env(api_keys)
                return jsonify({
                    "valid": True,
                    "time_remaining": time_remaining,
                    "users": item["users"],
                    "max_users": item["max_users"]
                })

            # Room full → reject
            return jsonify({"valid": False, "message": "Max user limit reached."})

    return jsonify({"valid": False, "message": "Key is invalid."})

@app.route('/api/add-key', methods=['GET'])
def add_new_key():
    current_time = datetime.now(UTC)

    control_key = request.args.get("control_key")
    new_key = request.args.get("key")
    expire_months = request.args.get("expire_months")
    max_users = request.args.get("max_users")

    if not control_key or not new_key or expire_months is None or max_users is None:
        return jsonify({"valid": False, "message": "Required parameters: control_key, key, expire_months, max_users."}), 400

    if control_key != MAIN_CONTROL_KEY:
        return jsonify({"valid": False, "message": "Main control key is invalid."})

    global api_keys
    try:
        expire_months_float = float(expire_months)
        max_users_int = int(max_users)

        if expire_months_float <= 0 or max_users_int <= 0:
            return jsonify({"valid": False, "message": "Expiration time and max_users must be greater than 0."})

        expiration_time = current_time + timedelta(days=expire_months_float * 30)
        new_key_entry = {
            "key": new_key,
            "time": expiration_time.isoformat() + "Z",
            "users": [],
            "max_users": max_users_int
        }

        original_api_keys = api_keys.copy()
        api_keys.append(new_key_entry)

        success, error_msg = update_render_env(api_keys)
        if not success:
            api_keys = original_api_keys
            return jsonify({"valid": False, "message": f"Failed to add key. Error: {error_msg}"}), 500

        return jsonify({
            "valid": True,
            "message": "New key has been added and saved on Render.",
            "new_key": new_key,
            "expiration_time": expiration_time.isoformat() + "Z",
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
    print(f"[INFO] Starting API server with {len(api_keys)} keys loaded.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

