# NAC Sistemi — Network Access Control

FreeRADIUS + FastAPI + PostgreSQL + Redis ile PAP tabanlı Network Access Control sistemi.

## Mimari

Kullanıcı/NAS → FreeRADIUS (1812/udp) → FastAPI Policy Engine (8000/tcp) → PostgreSQL + Redis

## Kurulum

1. Repoyu klonla

git clone https://github.com/BatuhanBaskurt/nac-project.git
cd nac-project

2. .env dosyasını oluştur

cp .env.example .env

3. Sistemi başlat

docker compose up -d --build

4. Kontrol et

docker ps

4 container calisiyor olmali: nac-freeradius, nac-api, nac-postgres, nac-redis

## Test Kullanicilari

| Kullanici | Sifre     | Grup     | VLAN |
|-----------|-----------|----------|------|
| admin     | admin123  | admin    | 10   |
| employee  | emp123    | employee | 20   |
| guest     | guest123  | guest    | 30   |

## Authentication Testleri

Basarili giris:
docker exec nac-freeradius radtest admin admin123 localhost 0 testing123

Basarisiz giris:
docker exec nac-freeradius radtest admin yanliksifre localhost 0 testing123

Olmayan kullanici:
docker exec nac-freeradius radtest olmayan sifre123 localhost 0 testing123

## API Endpoint Testleri

Health check:
curl http://localhost:8000/health

Kullanici listesi:
curl http://localhost:8000/users

Aktif oturumlar:
curl http://localhost:8000/sessions/active

## Accounting Testi

Oturum baslat:
echo "User-Name=admin,Acct-Status-Type=Start,Acct-Session-Id=test123,NAS-IP-Address=127.0.0.1" | radclient localhost acct testing123

Oturum bitir:
echo "User-Name=admin,Acct-Status-Type=Stop,Acct-Session-Id=test123,NAS-IP-Address=127.0.0.1,Acct-Session-Time=120" | radclient localhost acct testing123

## API Endpoints

| Endpoint          | Metot | Aciklama                  |
|-------------------|-------|---------------------------|
| /health           | GET   | Servis durumu             |
| /authorize        | POST  | FreeRADIUS authorize      |
| /auth             | POST  | FreeRADIUS authenticate   |
| /accounting       | POST  | Oturum kaydi              |
| /users            | GET   | Kullanici listesi         |
| /sessions/active  | GET   | Aktif oturumlar (Redis)   |

## Guvenlik Ozellikleri

- Rate Limiting: 5 basarisiz denemede 5 dakika blok (Redis)
- VLAN Segmentasyonu: Grup bazli ag ayrimi
- Sifre Kontrolu: API katmaninda dogrulama
- Izole Docker Network: Servisler arasi guvenli iletisim
- Environment Variables: Sifreler .env dosyasinda, Git'e gitmez

## Onemli Notlar

- .env dosyasini asla Git'e commit etme
- Uretim ortaminda testing123 secret'ini degistir
- docker-compose up -d --build komutu ile tum sistem ayaga kalkar
