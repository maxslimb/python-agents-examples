import os
import threading
import livekit
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


LIVEKIT_WS_URL = os.environ.get("LIVEKIT_WS_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
PORT = 8000

ROOM_AGENTS: {str: []} = {}


@app.route("/add_agent", methods=["POST"])
def add_agent(request):
    data = request.get_json()
    room = data['room']
    agent = data['agent']
    return {"success": True}

if __name__ == "__main__":
    print("hello world")
    app.run(host="0.0.0.0", port=PORT, debug=True)

