from flask import Flask, jsonify, request
import os
import json
from datetime import datetime

app = Flask(__name__)

# Lấy danh sách key từ biến môi trường và chuyển thành danh sách Python
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
