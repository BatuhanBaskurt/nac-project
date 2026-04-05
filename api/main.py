from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import create_engine, text
from redis import Redis
import os, json
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="NAC Policy Engine")

engine = create_engine(os.environ["DATABASE_URL"])
redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

def get_val(body: dict, key: str) -> Optional[str]:
    field = body.get(key)
    if not field:
        return None
    val = field.get("value", [])
    return val[0] if val else None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/authorize")
async def authorize(request: Request):
    body = await request.json()
    username = get_val(body, "User-Name")
    password = get_val(body, "User-Password")

    if not username:
        raise HTTPException(status_code=400, detail="Missing username")

    # Rate limiting
    rate_key = f"ratelimit:{username}"
    attempts = redis.get(rate_key)
    if attempts and int(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT value FROM radcheck WHERE username=:u AND attribute='Bcrypt-Password'"),
            {"u": username}
        ).fetchone()

        if not result:
            redis.incr(rate_key)
            redis.expire(rate_key, 300)
            raise HTTPException(status_code=404, detail="User not found")

        # Şifre kontrolü
        import bcrypt as _bcrypt
        if password and not _bcrypt.checkpw(password.encode(), result[0].encode()):
            redis.incr(rate_key)
            redis.expire(rate_key, 300)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        redis.delete(rate_key)

        group = conn.execute(
            text("SELECT groupname FROM radusergroup WHERE username=:u"),
            {"u": username}
        ).fetchone()

        attrs = []
        if group:
            attrs = conn.execute(
                text("SELECT attribute, op, value FROM radgroupreply WHERE groupname=:g"),
                {"g": group[0]}
            ).fetchall()

    reply = {row[0]: row[2] for row in attrs}
    return {"reply": reply}

@app.post("/auth")
async def auth(request: Request):
    body = await request.json()
    username = get_val(body, "User-Name")
    password = get_val(body, "User-Password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT value FROM radcheck WHERE username=:u AND attribute='Bcrypt-Password'"),
            {"u": username}
        ).fetchone()

    if not result or result[0] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"control": {"Auth-Type": "Accept"}}

@app.post("/accounting")
async def accounting(request: Request):
    body = await request.json()
    now = datetime.now(timezone.utc)

    username = get_val(body, "User-Name") or "unknown"
    nasip = get_val(body, "NAS-IP-Address") or "0.0.0.0"
    sessionid = get_val(body, "Acct-Session-Id") or "unknown"
    statustype = get_val(body, "Acct-Status-Type") or "unknown"
    sessiontime = int(get_val(body, "Acct-Session-Time") or 0)
    inputoctets = int(get_val(body, "Acct-Input-Octets") or 0)
    outputoctets = int(get_val(body, "Acct-Output-Octets") or 0)

    with engine.begin() as conn:
        if statustype == "Start":
            conn.execute(text("""
                INSERT INTO radacct (acctsessionid, acctuniqueid, username, nasipaddress,
                    acctstarttime, acctstatustype)
                VALUES (:sid, :uid, :u, :nas, :start, :status)
            """), {
                "sid": sessionid, "uid": sessionid,
                "u": username, "nas": nasip,
                "start": now, "status": statustype
            })
            redis.setex(f"session:{sessionid}", 86400,
                json.dumps({"username": username, "start": str(now)}))

        elif statustype == "Stop":
            conn.execute(text("""
                UPDATE radacct SET acctstoptime=:stop, acctsessiontime=:dur,
                    acctinputoctets=:in, acctoutputoctets=:out, acctstatustype=:status
                WHERE acctsessionid=:sid
            """), {
                "stop": now, "dur": sessiontime,
                "in": inputoctets, "out": outputoctets,
                "status": statustype, "sid": sessionid
            })
            redis.delete(f"session:{sessionid}")

    return {"status": "ok"}

@app.get("/users")
def get_users():
    with engine.connect() as conn:
        users = conn.execute(text("""
            SELECT r.username, g.groupname
            FROM radcheck r
            LEFT JOIN radusergroup g ON r.username = g.username
        """)).fetchall()
    return [{"username": u[0], "group": u[1]} for u in users]

@app.get("/sessions/active")
def active_sessions():
    keys = redis.keys("session:*")
    sessions = []
    for k in keys:
        data = redis.get(k)
        if data:
            sessions.append(json.loads(data))
    return sessions
