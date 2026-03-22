# ------------------------------------------------------------
# Free Fire Account Info API
#
# 👑 Owner / Developer :
# USERNAME  : @STAR_GMR
# CHANNEL   : @STAR_METHODE
#
# Credit    : @STAR_GMR
# JOIN      : @STAR_METHODE
#
# Purpose  : Fetch Free Fire profile details using UID (JWT + AES)
# Note     : THIS CODE MANAGED & MAINTAINED BY @STAR_GMR
#
# Endpoint : /info?uid=<PLAYER_UID>&region=<REGION>
# Example  : /info?uid=11111111&region=IND
#
# Regions Supported : IND | BD | PK
# Release Version   : OB52
# License : Personal / internal use only
# ------------------------------------------------------------

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import requests
from flask import Flask, jsonify, request
from data_pb2 import AccountPersonalShowInfo
from google.protobuf.json_format import MessageToDict
import uid_generator_pb2
import threading
import time

app = Flask(__name__)

jwt_token = None
jwt_lock = threading.Lock()

# ---------------- JWT CONFIG ----------------
JWT_API = "http://star-jwt-gen.vercel.app/token?"

JWT_CREDENTIALS = {
    "IND": {"uid": "4657633505", "password": "S_47O7O_BY_STAR_GMR_E65Q7"},
    "BD":  {"uid": "4647636696", "password": "STAR_6TNZJ_BY_STAR_GMR_0428C"},
    "PK":  {"uid": "4608984203", "password": "STAR_GMR_STAR_5DHXJ"},
}

# ---------------- JWT HANDLING ----------------
def get_jwt_token_sync(region):
    global jwt_token

    creds = JWT_CREDENTIALS.get(region, JWT_CREDENTIALS["IND"])
    url = f"{JWT_API}?uid={creds['uid']}&password={creds['password']}"

    with jwt_lock:
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if isinstance(data, dict) and "token" in data:
                jwt_token = data["token"]
                return jwt_token
        except Exception as e:
            print("[JWT ERROR]", e)

    return None

def ensure_jwt_token_sync(region):
    global jwt_token
    if not jwt_token:
        return get_jwt_token_sync(region)
    return jwt_token

def jwt_token_updater(region):
    while True:
        get_jwt_token_sync(region)
        time.sleep(300)

# ---------------- API ENDPOINT ----------------
def get_api_endpoint(region):
    endpoints = {
        "IND": "https://client.ind.freefiremobile.com/GetPlayerPersonalShow",
        "BD":  "https://clientbp.ggblueshark.com/GetPlayerPersonalShow",
        "PK":  "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
    }
    return endpoints.get(region, endpoints["IND"])

# ---------------- AES ----------------
AES_KEY = "Yg&tc%DEuh6%Zc^8"
AES_IV  = "6oyZDr22E3ychjM%"

def encrypt_aes(hex_data):
    cipher = AES.new(AES_KEY.encode()[:16], AES.MODE_CBC, AES_IV.encode()[:16])
    padded = pad(bytes.fromhex(hex_data), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return binascii.hexlify(encrypted).decode()

# ---------------- MAIN API CALL ----------------
def call_api(enc_hex, region):
    token = ensure_jwt_token_sync(region)
    if not token:
        raise Exception("JWT token not available")

    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)",
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB52",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    r = requests.post(
        get_api_endpoint(region),
        headers=headers,
        data=bytes.fromhex(enc_hex),
        timeout=10
    )

    return r.content.hex()

# ---------------- ROUTES ----------------
@app.route("/info")
def info():
    try:
        uid = request.args.get("uid")
        region = request.args.get("region", "IND").upper()

        if not uid:
            return jsonify({"error": "UID required"}), 400

        if region not in ["IND", "BD", "PK"]:
            return jsonify({"error": "Only IND, BD, PK supported"}), 400

        threading.Thread(target=jwt_token_updater, args=(region,), daemon=True).start()

        msg = uid_generator_pb2.uid_generator()
        msg.saturn_ = int(uid)
        msg.garena = 1

        hex_data = binascii.hexlify(msg.SerializeToString()).decode()
        encrypted = encrypt_aes(hex_data)

        api_hex = call_api(encrypted, region)

        pb = AccountPersonalShowInfo()
        pb.ParseFromString(bytes.fromhex(api_hex))
        data = MessageToDict(pb)

        data["Developer"] = "@STAR_GMR"
        data["Channel"] = "@STAR_METHODE"
        data["Region"] = region
        data["Version"] = "OB52"

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return jsonify({
        "message": "Free Fire Account Info API",
        "developer": "@STAR_GMR",
        "channel": "@STAR_METHODE",
        "endpoint": "/info?uid=UID&region=IND"
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    ensure_jwt_token_sync("IND")
    app.run(host="0.0.0.0", port=5000)
