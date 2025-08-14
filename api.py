from flask import Flask, jsonify, request
import os
import json
import requests
from datetime import datetime, timedelta, UTC
import traceback  # For detailed error logging

app = Flask(__name__)

# Load API keys from environment variable
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))

# Control key
MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

# Render API info
RENDER_API_KEY = os.environ.get("RENDER_API_KEY")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID")

def update_render_env(api_keys_list):
    """Update API_KEYS environment variable on Render with detailed error handling"""
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        error_msg = "Missing RENDER_API_KEY or RENDER_SERVICE_ID"
        print(f"[ERROR] {error_msg}")
        return False, error_msg

    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = [{
        "key": "API_KEYS",
        "value": json.dumps(api_keys_list, ensure_ascii=False)  # Keep UTF-8 for Vietnamese
    }]
    
    try:
        print(f"[INFO] Attempting to update API_KEYS with {len(api_keys_list)} keys")
        resp = requests.put(url, headers=headers, data=json.dumps(data), timeout=15)  # Increased timeout
        resp.raise_for_status()  # Raise exception if not successful
        print(f"[INFO] API_KEYS updated successfully on Render. Total keys: {len(api_keys_list)}")
        return True, None
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error: {resp.status_code} - {resp.text if 'resp.text' in locals() else str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello! This is your API."})

@app.route('/api/<key>', methods=['GET'])
def check_key(key):
    current_time = datetime.now(UTC)
    for item in api_keys:
        if item.get("key") == key:
            key_time = datetime.fromisoformat(item.get("time").replace("Z", "+00:00")) if "Z" not in item.get("time") else datetime.fromisoformat(item.get("time"))
            time_remaining = (key_time - current_time).total_seconds()
            if time_remaining > 0:
                print(f"[INFO] Key '{key}' is valid. Time remaining: {time_remaining} seconds.")
                return jsonify({"valid": True, "time_remaining": max(0, time_remaining)})
            else:
                print(f"[WARNING] Key '{key}' has expired.")
                return jsonify({"valid": False, "message": "Key has expired."})
    print(f"[WARNING] Key '{key}' is invalid.")
    return jsonify({"valid": False, "message": "Key is invalid."})

@app.route('/api/add-key', methods=['GET'])
def add_new_key():
    current_time = datetime.now(UTC)

    control_key = request.args.get("control_key")
    new_key = request.args.get("key")
    expire_months = request.args.get("expire_months")

    if not control_key or not new_key or expire_months is None:
        print("[ERROR] Missing required parameters when adding new key.")
        return jsonify({"valid": False, "message": "Required parameters: control_key, key, and expire_months."}), 400

    if control_key != MAIN_CONTROL_KEY:
        print("[ERROR] Invalid main control key provided.")
        return jsonify({"valid": False, "message": "Main control key is invalid."})

    # Ensure api_keys is accessible as a global variable
    global api_keys
    try:
        expire_months_float = float(expire_months)
        if expire_months_float <= 0:
            print("[ERROR] Expiration time must be greater than 0.")
            return jsonify({"valid": False, "message": "Expiration time must be greater than 0."})

        expiration_time = current_time + timedelta(days=expire_months_float * 30)
        new_key_entry = {"key": new_key, "time": expiration_time.isoformat() + "Z"}

        # Backup current api_keys
        original_api_keys = api_keys.copy()
        api_keys.append(new_key_entry)
        print(f"[INFO] Added new key '{new_key}' with expiration date {expiration_time.isoformat()}Z.")

        # Update Environment Variables on Render
        success, error_msg = update_render_env(api_keys)
        if not success:
            # Rollback if update fails
            api_keys = original_api_keys
            print(f"[ERROR] Rollback performed due to: {error_msg}")
            return jsonify({"valid": False, "message": f"Failed to add key. Error: {error_msg}"}), 500

        return jsonify({
            "valid": True,
            "message": "New key has been added and saved on Render.",
            "new_key": new_key,
            "expiration_time": expiration_time.isoformat() + "Z",
            "current_api_keys": json.dumps(api_keys)  # Show updated list for verification
        })
    except ValueError as e:
        print(f"[ERROR] Expiration time must be a valid number. Details: {str(e)}")
        return jsonify({"valid": False, "message": "Expiration time must be a valid number."}), 400
    except Exception as e:
        print(f"[ERROR] Unexpected error in add_new_key: {str(e)}")
        print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
        return jsonify({"valid": False, "message": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    print(f"[INFO] Starting API server with {len(api_keys)} keys loaded.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
