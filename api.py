from flask import Flask, jsonify, request
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Lấy danh sách key từ biến môi trường
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))
# Định nghĩa main_control_key từ biến môi trường
MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

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
                return jsonify({"valid": True, "time_remaining": max(0, time_remaining)})
            else:
                return jsonify({"valid": False, "message": "Key đã hết hạn."})
    return jsonify({"valid": False, "message": "Key không hợp lệ."})

@app.route('/api/<main_control_key>/<new_key>/<duration>', methods=['POST'])
def add_new_key(main_control_key, new_key, duration):
    current_time = datetime.utcnow()
    if main_control_key != MAIN_CONTROL_KEY:
        return jsonify({"valid": False, "message": "Main control key không hợp lệ."})

    try:
        duration_months = int(duration)
        if duration_months <= 0:
            return jsonify({"valid": False, "message": "Thời gian phải lớn hơn 0."})

        expiration_time = current_time + timedelta(days=duration_months * 30)
        new_key_entry = {"key": new_key, "time": expiration_time.isoformat() + "Z"}
        api_keys.append(new_key_entry)
        os.environ["API_KEYS"] = json.dumps(api_keys)

        return jsonify({
            "valid": True,
            "message": "Key mới đã được thêm.",
            "new_key": new_key,
            "expiration_time": expiration_time.isoformat() + "Z"
        })
    except ValueError:
        return jsonify({"valid": False, "message": "Thời gian phải là số nguyên."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
