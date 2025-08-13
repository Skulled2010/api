from flask import Flask, jsonify
import os

app = Flask(__name__)

# Định nghĩa một route API cơ bản
@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Xin chào! Đây là API của bạn."})

# Chạy ứng dụng
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Lấy cổng từ Render, mặc định 5000 nếu chạy cục bộ
    app.run(host='0.0.0.0', port=port, debug=False)
