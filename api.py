from flask import Flask, jsonify, request
import os
import json
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# Load API keys from environment variable
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))

# Control key
MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

# Render API info
RENDER_API_KEY = os.environ.get("RENDER_API_KEY")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID")

def update_render_env(api_keys_list):
    """Update API_KEYS environment variable on Render with retry mechanism"""
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
        "value": json.dumps(api_keys_list, ensure_ascii=False)  # Keep UTF-8 for Vietnamese
    }]
    
    try:
        resp = requests.put(url, headers=headers, data=json.dumps(data), timeout=10)
        if resp.status_code == 200:
            print(f"[INFO] API_KEYS updated successfully on Render. Total keys: {len(api_keys_list)}")
            return True, None
        else:
            print(f"[ERROR] Failed to update API_KEYS: {resp.status_code} - {resp.text}")
            return False, f"API update failed: {resp.status_code} - {resp.text}"
    except requests.RequestException as e:
        print(f"[ERROR] Network error updating API_KEYS: {str(e)}")
        return False, f"Network error: {str(e)}"

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Xin chào! Đây là API của bạn."})

@app.route('/api/<key>', methods=['GET'])
def check_key(key):
    current_time = datetime.utcnow()
    for item in api_keys:
        if item.get("key") == key:
            key_time = datetime.fromisoformat(item.get("time").replace("Z", "+00:00"))
            time_remaining = (key_time - current_time).total_seconds()
            if time_remaining > 0:
                print(f"[INFO] Key '{key}' is valid. Time remaining: {time_remaining} seconds.")
                return jsonify({"valid": True, "time_remaining": max(0, time_remaining)})
            else:
                print(f"[WARNING] Key '{key}' has expired.")
                return jsonify({"valid": False, "message": "Key đã hết hạn."})
    print(f"[WARNING] Key '{key}' is invalid.")
    return jsonify({"valid": False, "message": "Key không hợp lệ."})

@app.route('/api/add-key', methods=['GET'])
def add_new_key():
    current_time = datetime.utcnow()

    control_key = request.args.get("control_key")
    new_key = request.args.get("key")
    expire_months = request.args.get("expire_months")

    if not control_key or not new_key or expire_months is None:
        print("[ERROR] Missing required parameters when adding new key.")
        return jsonify({"valid": False, "message": "Yêu cầu các tham số: control_key, key, và expire_months."}), 400

    if control_key != MAIN_CONTROL_KEY:
        print("[ERROR] Invalid main control key provided.")
        return jsonify({"valid": False, "message": "Main control key không hợp lệ."})

    try:
        expire_months_float = float(expire_months)
        if expire_months_float <= 0:
            print("[ERROR] Expiration time must be greater than 0.")
            return jsonify({"valid": False, "message": "Thời gian phải lớn hơn 0."})

        expiration_time = current_time + timedelta(days=expire_months_float * 30)
        new_key_entry = {"key": new_key, "time": expiration_time.isoformat() + "Z"}

        # Thêm key vào danh sách tạm thời
        api_keys.append(new_key_entry)
        print(f"[INFO] Added new key '{new_key}' with expiration date {expiration_time.isoformat()}Z.")

        # Cập nhật Environment Variables trên Render
        success, error_msg = update_render_env(api_keys)
        if not success:
            # Rollback nếu cập nhật thất bại
            api_keys.pop()
            return jsonify({"valid": False, "message": f"Thêm key thất bại. Lỗi: {error_msg}"}), 500

        return jsonify({
            "valid": True,
            "message": "Key mới đã được thêm và lưu trên Render.",
            "new_key": new_key,
            "expiration_time": expiration_time.isoformat() + "Z"
        })
    except ValueError:
        print("[ERROR] Expiration time must be a valid number.")
        return jsonify({"valid": False, "message": "Thời gian phải là số hợp lệ."}), 400

if __name__ == '__main__':
    print(f"[INFO] Starting API server with {len(api_keys)} keys loaded.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
