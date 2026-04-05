from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from redis import Redis
from passlib.hash import bcrypt
import os, json
from datetime import datetime, timezone

app = FastAPI(title="NAC Policy Engine")

# DB ve Redis bağlantıları
engine = create_engine(os.environ["DATABASE_URL"])
redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

# --- Modeller ---
class AuthRequest(BaseModel):
    username: str
    password: str

class AuthorizeRequest(BaseModel):
    username: str

class AccountingRequest(BaseModel):
    username: str
    nasipaddress: str
    acctsessionid: str
    acctstatustype: str
    acctsessiontime: int = 0
    acctinputoctets: int = 0
    acctoutputoctets: int = 0

# --- Health ---
@app.get("/health")
def health():
    return {"status": "ok"}

# --- Auth ---
@app.post("/auth")
def auth(req: AuthRequest):
    # Rate limiting — 5 yanlış denemede blok
    rate_key = f"ratelimit:{req.username}"
    attempts = redis.get(rate_key)
    if attempts and int(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT value FROM radcheck WHERE username=:u AND attribute='Cleartext-Password'"),
            {"u": req.username}
        ).fetchone()

    if not result or result[0] != req.password:
        # Yanlış şifre — sayacı artır
        redis.incr(rate_key)
        redis.expire(rate_key, 300)  # 5 dakika blok
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Başarılı — sayacı sıfırla
    redis.delete(rate_key)
    return {"control": {"Auth-Type": "Accept"}}

# --- Authorize ---
@app.post("/authorize")
def authorize(req: AuthorizeRequest):
    with engine.connect() as conn:
        # Kullanıcının grubunu bul
        group = conn.execute(
            text("SELECT groupname FROM radusergroup WHERE username=:u"),
            {"u": req.username}
        ).fetchone()

        if not group:
            raise HTTPException(status_code=404, detail="User not found")

        # Grubun VLAN atribütlerini bul
        attrs = conn.execute(
            text("SELECT attribute, op, value FROM radgroupreply WHERE groupname=:g"),
            {"g": group[0]}
        ).fetchall()

    reply = {row[0]: row[2] for row in attrs}
    return {"reply": reply, "group": group[0]}

# --- Accounting ---
@app.post("/accounting")
def accounting(req: AccountingRequest):
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        if req.acctstatustype == "Start":
            conn.execute(text("""
                INSERT INTO radacct (acctsessionid, acctuniqueid, username, nasipaddress,
                    acctstarttime, acctstatustype)
                VALUES (:sid, :uid, :u, :nas, :start, :status)
            """), {
                "sid": req.acctsessionid,
                "uid": req.acctsessionid,
                "u": req.username,
                "nas": req.nasipaddress,
                "start": now,
                "status": req.acctstatustype
            })
            # Redis'e aktif oturum ekle
            redis.setex(f"session:{req.acctsessionid}", 86400,
                json.dumps({"username": req.username, "start": str(now)}))

        elif req.acctstatustype == "Stop":
            conn.execute(text("""
                UPDATE radacct SET acctstoptime=:stop, acctsessiontime=:dur,
                    acctinputoctets=:in, acctoutputoctets=:out, acctstatustype=:status
                WHERE acctsessionid=:sid
            """), {
                "stop": now, "dur": req.acctsessiontime,
                "in": req.acctinputoctets, "out": req.acctoutputoctets,
                "status": req.acctstatustype, "sid": req.acctsessionid
            })
            # Redis'ten oturumu sil
            redis.delete(f"session:{req.acctsessionid}")

    return {"status": "ok"}

# --- Kullanıcı listesi ---
@app.get("/users")
def get_users():
    with engine.connect() as conn:
        users = conn.execute(text("""
            SELECT r.username, g.groupname
            FROM radcheck r
            LEFT JOIN radusergroup g ON r.username = g.username
        """)).fetchall()
    return [{"username": u[0], "group": u[1]} for u in users]

# --- Aktif oturumlar ---
@app.get("/sessions/active")
def active_sessions():
    keys = redis.keys("session:*")
    sessions = []
    for k in keys:
        data = redis.get(k)
        if data:
            sessions.append(json.loads(data))
    return sessions
