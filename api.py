from flask import Flask, jsonify, request
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Lấy danh sách key từ biến môi trường
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))
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
                return jsonify({"valid": True, "time_remaining_seconds": max(0, time_remaining)})
            else:
                return jsonify({"valid": False, "message": "Key đã hết hạn."})
    return jsonify({"valid": False, "message": "Key không hợp lệ."})

@app.route('/api/add_key', methods=['POST'])
def add_key():
    data = request.get_json()

    # Kiểm tra control key
    if data.get("control_key") != MAIN_CONTROL_KEY:
        return jsonify({"success": False, "message": "Sai MAIN_CONTROL_KEY"}), 403

    new_key = data.get("key")
    expire_months = float(data.get("expire_months", 1))  # mặc định 1 tháng

    if not new_key:
        return jsonify({"success": False, "message": "Thiếu key"}), 400

    # Tính thời gian hết hạn
    months_int = int(expire_months)  # phần nguyên
    extra_days = int((expire_months - months_int) * 30)  # phần thập phân quy ra ngày (xấp xỉ 30 ngày/tháng)

    expire_time = datetime.utcnow() + timedelta(days=months_int * 30 + extra_days)
    expire_time_iso = expire_time.isoformat() + "Z"

    # Thêm vào list
    api_keys.append({"key": new_key, "time": expire_time_iso})

    return jsonify({
        "success": True,
        "message": "Thêm key thành công",
        "expire_time": expire_time_iso,
        "total_keys": len(api_keys)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
