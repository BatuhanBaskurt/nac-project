# NAC Sistemi — Network Access Control

FreeRADIUS + FastAPI + PostgreSQL + Redis ile PAP authentication tabanlı NAC sistemi.

## Kurulum
```bash
cp .env.example .env
# .env dosyasını düzenle
docker compose up -d --build
```

## Test
```bash
# PAP Authentication
docker exec nac-freeradius radtest admin admin123 localhost 0 testing123

# API Health
curl http://localhost:8000/health

# Kullanıcı listesi
curl http://localhost:8000/users

# Aktif oturumlar
curl http://localhost:8000/sessions/active
```

## Servisler

| Servis | Port |
|--------|------|
| FastAPI | 8000 |
| FreeRADIUS Auth | 1812/udp |
| FreeRADIUS Acct | 1813/udp |
