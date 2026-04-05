from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from redis import Redis
import os, json
from datetime import datetime, timezone
from typing import Optional, Any

app = FastAPI(title="NAC Policy Engine")

engine = create_engine(os.environ["DATABASE_URL"])
redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

class AuthRequest(BaseModel):
    username: Optional[str] = Field(None, alias="User-Name")
    password: Optional[str] = Field(None, alias="User-Password")
    model_config = {"populate_by_name": True}

class AuthorizeRequest(BaseModel):
    username: Optional[str] = Field(None, alias="User-Name")
    model_config = {"populate_by_name": True}

class AccountingRequest(BaseModel):
    username: Optional[str] = Field(None, alias="User-Name")
    nasipaddress: Optional[str] = Field(None, alias="NAS-IP-Address")
    acctsessionid: Optional[str] = Field(None, alias="Acct-Session-Id")
    acctstatustype: Optional[str] = Field(None, alias="Acct-Status-Type")
    acctsessiontime: Optional[int] = Field(0, alias="Acct-Session-Time")
    acctinputoctets: Optional[int] = Field(0, alias="Acct-Input-Octets")
    acctoutputoctets: Optional[int] = Field(0, alias="Acct-Output-Octets")
    model_config = {"populate_by_name": True}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth")
async def auth(req: AuthRequest):
    username = req.username
    password = req.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")

    rate_key = f"ratelimit:{username}"
    attempts = redis.get(rate_key)
    if attempts and int(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT value FROM radcheck WHERE username=:u AND attribute='Cleartext-Password'"),
            {"u": username}
        ).fetchone()

    if not result or result[0] != password:
        redis.incr(rate_key)
        redis.expire(rate_key, 300)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    redis.delete(rate_key)
    return {"control": {"Auth-Type": "Accept"}}

@app.post("/authorize")
async def authorize(req: AuthorizeRequest):
    username = req.username
    if not username:
        raise HTTPException(status_code=400, detail="Missing username")

    with engine.connect() as conn:
        group = conn.execute(
            text("SELECT groupname FROM radusergroup WHERE username=:u"),
            {"u": username}
        ).fetchone()

        if not group:
            raise HTTPException(status_code=404, detail="User not found")

        attrs = conn.execute(
            text("SELECT attribute, op, value FROM radgroupreply WHERE groupname=:g"),
            {"g": group[0]}
        ).fetchall()

    reply = {row[0]: row[2] for row in attrs}
    return {"reply": reply, "group": group[0]}

@app.post("/accounting")
async def accounting(req: AccountingRequest):
    now = datetime.now(timezone.utc)
    username = req.username or "unknown"
    nasip = req.nasipaddress or "0.0.0.0"
    sessionid = req.acctsessionid or "unknown"
    statustype = req.acctstatustype or "unknown"

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
                "stop": now, "dur": req.acctsessiontime or 0,
                "in": req.acctinputoctets or 0, "out": req.acctoutputoctets or 0,
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

@app.post("/debug")
async def debug(request: Request):
    body = await request.json()
    print("DEBUG BODY:", body)
    return body
