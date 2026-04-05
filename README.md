# 🔐 NAC Sistemi — Network Access Control

FreeRADIUS, FastAPI, PostgreSQL ve Redis kullanarak geliştirilmiş PAP tabanlı Network Access Control sistemi.

## 📐 Mimari
Kullanıcı/NAS
↓
FreeRADIUS (1812/udp auth, 1813/udp acct)
↓  rlm_rest (HTTP JSON)
FastAPI Policy Engine (8000/tcp)
↓                    ↓
PostgreSQL               Redis
(Kullanıcılar,          (Oturum cache,
VLAN, Accounting)       Rate limiting)


## ⚙️ Kurulum

**1. Repoyu klonla**
```bash
git clone https://github.com/BatuhanBaskurt/nac-project.git
cd nac-project
```

**2. .env dosyasını oluştur**
```bash
cp .env.example .env
```

**3. Sistemi başlat**
```bash
docker compose up -d --build
```

**4. Servisleri kontrol et**
```bash
docker ps
```

Şu 4 container çalışıyor olmalı:
| Container | Açıklama |
|-----------|----------|
| nac-freeradius | RADIUS sunucusu |
| nac-api | FastAPI policy engine |
| nac-postgres | Veritabanı |
| nac-redis | Cache ve rate limiting |

## 👥 Test Kullanıcıları

| Kullanıcı | Şifre | Grup | VLAN |
|-----------|-------|------|------|
| admin | admin123 | admin | 10 |
| employee | emp123 | employee | 20 |
| guest | guest123 | guest | 30 |

## 🧪 Authentication Testleri
```bash
# Başarılı giriş
docker exec nac-freeradius radtest admin admin123 localhost 0 testing123

# Başarısız giriş
docker exec nac-freeradius radtest admin yanliksifre localhost 0 testing123

# Olmayan kullanıcı
docker exec nac-freeradius radtest olmayan sifre123 localhost 0 testing123
```

## 📡 API Testleri
```bash
# Health check
curl http://localhost:8000/health

# Kullanıcı listesi
curl http://localhost:8000/users

# Aktif oturumlar
curl http://localhost:8000/sessions/active
```

## 📊 Accounting Testleri
```bash
# Oturum başlat
docker exec nac-freeradius bash -c 'echo "User-Name=admin,Acct-Status-Type=Start,Acct-Session-Id=session001,NAS-IP-Address=127.0.0.1" | radclient localhost acct testing123'

# Aktif oturumu gör
curl http://localhost:8000/sessions/active

# Oturum bitir
docker exec nac-freeradius bash -c 'echo "User-Name=admin,Acct-Status-Type=Stop,Acct-Session-Id=session001,NAS-IP-Address=127.0.0.1,Acct-Session-Time=120" | radclient localhost acct testing123'

# PostgreSQL kaydını kontrol et
docker exec nac-postgres psql -U radius -d radius -c "SELECT username, acctstarttime, acctstoptime, acctsessiontime FROM radacct;"
```

## 🚫 Rate Limiting Testi

5 başarısız denemeden sonra hesap 5 dakika bloklanır.
```bash
# Önce sayacı sıfırla
docker exec nac-redis redis-cli -a redis123 DEL ratelimit:admin

# 6 kez dene
for i in 1 2 3 4 5 6; do
  echo "Deneme $i:"
  curl -s -X POST http://localhost:8000/authorize \
    -H "Content-Type: application/json" \
    -d '{"User-Name": {"type": "string", "value": ["admin"]}, "User-Password": {"type": "string", "value": ["yanliksifre"]}}'
  echo ""
done
```

Beklenen çıktı:
- Deneme 1-5 → `Invalid credentials`
- Deneme 6 → `Too many attempts`

## 🌐 API Endpoints

| Endpoint | Metot | Açıklama |
|----------|-------|----------|
| `/health` | GET | Servis durumu |
| `/authorize` | POST | FreeRADIUS authorize isteği |
| `/auth` | POST | FreeRADIUS authenticate isteği |
| `/accounting` | POST | Oturum kaydı |
| `/users` | GET | Kullanıcı listesi |
| `/sessions/active` | GET | Aktif oturumlar (Redis) |

## 🔒 Güvenlik Özellikleri

- **Rate Limiting** — 5 başarısız denemede 5 dakika blok (Redis)
- **VLAN Segmentasyonu** — Grup bazlı ağ ayrımı
- **Şifre Kontrolü** — API katmanında doğrulama
- **İzole Docker Network** — Servisler arası güvenli iletişim
- **Environment Variables** — Şifreler `.env` dosyasında, Git'e gitmiyor

## ⚠️ Önemli Notlar

- `.env` dosyasını asla Git'e commit etme
- Üretim ortamında `testing123` secret'ını değiştir
- `docker compose up -d --build` komutu ile tüm sistem ayağa kalkar
