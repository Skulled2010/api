from flask import Flask, jsonify, request
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)
print("new")
# Lấy danh sách key từ biến môi trường và chuyển thành danh sách Python
api_keys = json.loads(os.environ.get("API_KEYS", "[]"))
# Định nghĩa main_control_key từ biến môi trường
MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

@app.route('/api/add-key', methods=['GET'])
def add_new_key():
    current_time = datetime.utcnow()
    # Lấy tham số từ query string
    control_key = request.args.get("control_key")
    new_key = request.args.get("key")
    expire_months = request.args.get("expire_months")

    # Kiểm tra nếu thiếu tham số
    if not control_key or not new_key or expire_months is None:
        return jsonify({"valid": False, "message": "Yêu cầu các tham số: control_key, key, và expire_months."}), 400

    # Kiểm tra main_control_key
    if control_key != MAIN_CONTROL_KEY:
        return jsonify({"valid": False, "message": "Main control key không hợp lệ."})

    try:
        expire_months_float = float(expire_months)
        if expire_months_float <= 0:
            return jsonify({"valid": False, "message": "Thời gian phải lớn hơn 0."})

        # Tính thời gian hết hạn (dựa trên số ngày từ tháng, 1 tháng ≈ 30 ngày)
        expiration_time = current_time + timedelta(days=expire_months_float * 30)
        new_key_entry = {"key": new_key, "time": expiration_time.isoformat() + "Z"}
        api_keys.append(new_key_entry)

        # Lưu thay đổi (chỉ trong bộ nhớ, không vĩnh viễn trên Render)
        os.environ["API_KEYS"] = json.dumps(api_keys)

        return jsonify({
            "valid": True,
            "message": "Key mới đã được thêm.",
            "new_key": new_key,
            "expiration_time": expiration_time.isoformat() + "Z"
        })
    except ValueError:
        return jsonify({"valid": False, "message": "Thời gian phải là số hợp lệ."}), 400

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
