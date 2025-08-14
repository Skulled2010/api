from flask import Flask, jsonify, request
import os
import json
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# Lấy danh sách key từ biến môi trường
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))

# Control key
MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

# Render API info
RENDER_API_KEY = os.environ.get("RENDER_API_KEY")
RENDER_SERVICE_ID = os.environ.get("RENDER_SERVICE_ID")

def update_render_env(api_keys_list):
    """Cập nhật biến môi trường API_KEYS trên Render"""
    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = [{
        "key": "API_KEYS",
        "value": json.dumps(api_keys_list)
    }]
    resp = requests.put(url, headers=headers, data=json.dumps(data))
    if resp.status_code == 200:
        print("✅ API_KEYS đã được cập nhật trên Render.")
    else:
        print("❌ Lỗi khi cập nhật API_KEYS:", resp.text)

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

@app.route('/api/add-key', methods=['GET'])
def add_new_key():
    current_time = datetime.utcnow()

    control_key = request.args.get("control_key")
    new_key = request.args.get("key")
    expire_months = request.args.get("expire_months")

    if not control_key or not new_key or expire_months is None:
        return jsonify({"valid": False, "message": "Yêu cầu các tham số: control_key, key, và expire_months."}), 400

    if control_key != MAIN_CONTROL_KEY:
        return jsonify({"valid": False, "message": "Main control key không hợp lệ."})

    try:
        expire_months_float = float(expire_months)
        if expire_months_float <= 0:
            return jsonify({"valid": False, "message": "Thời gian phải lớn hơn 0."})

        expiration_time = current_time + timedelta(days=expire_months_float * 30)
        new_key_entry = {"key": new_key, "time": expiration_time.isoformat() + "Z"}

        api_keys.append(new_key_entry)

        # Cập nhật biến môi trường trên Render
        update_render_env(api_keys)

        return jsonify({
            "valid": True,
            "message": "Key mới đã được thêm và lưu trên Render.",
            "new_key": new_key,
            "expiration_time": expiration_time.isoformat() + "Z"
        })
    except ValueError:
        return jsonify({"valid": False, "message": "Thời gian phải là số hợp lệ."}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
