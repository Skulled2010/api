from flask import Flask, jsonify, request
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
import os, json, traceback

app = Flask(__name__)

# DB setup
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Model
class APIKey(Base):
    __tablename__ = "api_keys"
    key = Column(String, primary_key=True)
    expire_time = Column(DateTime, nullable=False)
    users = Column(Text, default="[]")  # Lưu dạng JSON string
    max_users = Column(Integer, default=1)

Base.metadata.create_all(engine)

MAIN_CONTROL_KEY = os.environ.get("MAIN_CONTROL_KEY", "default_control_key")

@app.route('/api/<key>', methods=['GET'])
def check_key(key):
    session = Session()
    try:
        user = request.args.get("user")
        if not user:
            return jsonify({"valid": False, "message": "Missing required parameter: user"}), 400

        api_key = session.query(APIKey).filter_by(key=key).first()
        if not api_key:
            return jsonify({"valid": False, "message": "Key is invalid."})

        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        if api_key.expire_time < current_time:
            return jsonify({"valid": False, "message": "Key has expired."})

        users_list = json.loads(api_key.users)
        if user in users_list:
            return jsonify({"valid": True, "time_remaining": (api_key.expire_time - current_time).total_seconds(),
                            "users": users_list, "max_users": api_key.max_users})

        if len(users_list) < api_key.max_users:
            users_list.append(user)
            api_key.users = json.dumps(users_list)
            session.commit()
            return jsonify({"valid": True, "time_remaining": (api_key.expire_time - current_time).total_seconds(),
                            "users": users_list, "max_users": api_key.max_users})

        return jsonify({"valid": False, "message": "Max user limit reached."})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"valid": False, "message": str(e)}), 500
    finally:
        session.close()

@app.route('/api/add-key', methods=['GET'])
def add_key():
    session = Session()
    try:
        control_key = request.args.get("control_key")
        new_key = request.args.get("key")
        expire_months = request.args.get("expire_months", type=float)
        max_users = request.args.get("max_users", type=int)

        if control_key != MAIN_CONTROL_KEY:
            return jsonify({"valid": False, "message": "Main control key is invalid."})

        if not all([new_key, expire_months, max_users]):
            return jsonify({"valid": False, "message": "Missing parameters."}), 400

        if session.query(APIKey).filter_by(key=new_key).first():
            return jsonify({"valid": False, "message": "Key already exists."})

        expire_time = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(days=expire_months * 30)
        new_api_key = APIKey(key=new_key, expire_time=expire_time, users=json.dumps([]), max_users=max_users)
        session.add(new_api_key)
        session.commit()

        return jsonify({"valid": True, "message": "Key added.", "key": new_key, "expiration_time": expire_time.isoformat()})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"valid": False, "message": str(e)}), 500
    finally:
        session.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
