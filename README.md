---

## Klasor Yapisi

nac-project/
├── api/
│   └── main.py              FastAPI policy engine
├── freeradius/
│   ├── Dockerfile
│   ├── clients.d/
│   │   └── local.conf       NAS client tanimlari
│   ├── mods-available/
│   │   └── rest             REST modulu config
│   └── sites-available/
│       └── default          Virtual server config
├── postgres/
│   └── init.sql             Veritabani semasi ve test verileri
├── docker-compose.yml
├── .env.example
└── README.md

---

## Kurulum

1. Repoyu klonla

git clone https://github.com/BatuhanBaskurt/nac-project.git
cd nac-project

2. .env dosyasini olustur

cp .env.example .env

Gerekirse sifreler degistirilebilir.

3. Sistemi baslat

docker compose up -d --build

4. Servisleri kontrol et

docker ps

Su 4 container calisiyor olmali:
  nac-freeradius   RADIUS sunucusu
  nac-api          FastAPI policy engine
  nac-postgres     Veritabani
  nac-redis        Cache ve rate limiting

---

## Test Kullanicilari

Kullanici   Sifre      Grup      VLAN
--------    -------    --------  ----
admin       admin123   admin     10
employee    emp123     employee  20
guest       guest123   guest     30

---

## Authentication Testleri

Basarili giris:
docker exec nac-freeradius radtest admin admin123 localhost 0 testing123

Basarisiz giris:
docker exec nac-freeradius radtest admin yanliksifre localhost 0 testing123

Olmayan kullanici:
docker exec nac-freeradius radtest olmayan sifre123 localhost 0 testing123

---

## API Testleri

Health check:
curl http://localhost:8000/health

Kullanici listesi:
curl http://localhost:8000/users

Aktif oturumlar:
curl http://localhost:8000/sessions/active

---

## Accounting Testleri

Oturum baslat:
docker exec nac-freeradius bash -c 'echo "User-Name=admin,Acct-Status-Type=Start,Acct-Session-Id=session001,NAS-IP-Address=127.0.0.1" | radclient localhost acct testing123'

Aktif oturumu goruntule:
curl http://localhost:8000/sessions/active

Oturum bitir:
docker exec nac-freeradius bash -c 'echo "User-Name=admin,Acct-Status-Type=Stop,Acct-Session-Id=session001,NAS-IP-Address=127.0.0.1,Acct-Session-Time=120" | radclient localhost acct testing123'

PostgreSQL kaydi kontrol et:
docker exec nac-postgres psql -U radius -d radius -c "SELECT username, acctstarttime, acctstoptime, acctsessiontime FROM radacct;"

---

## Rate Limiting Testi

5 basarisiz denemeden sonra hesap 5 dakika bloklanir.

docker exec nac-redis redis-cli -a redis123 DEL ratelimit:admin

for i in 1 2 3 4 5 6; do
  echo "Deneme $i:"
  curl -s -X POST http://localhost:8000/authorize \
    -H "Content-Type: application/json" \
    -d '{"User-Name": {"type": "string", "value": ["admin"]}, "User-Password": {"type": "string", "value": ["yanliksifre"]}}'
  echo ""
done

Beklenen cikti:
  Deneme 1-5: Invalid credentials
  Deneme 6:   Too many attempts

---

## API Endpoints

Endpoint           Metot   Aciklama
/health            GET     Servis durumu
/authorize         POST    FreeRADIUS authorize istegi
/auth              POST    FreeRADIUS authenticate istegi
/accounting        POST    Oturum kaydi
/users             GET     Kullanici listesi
/sessions/active   GET     Aktif oturumlar (Redis)

---

## Guvenlik Ozellikleri

Rate Limiting     5 basarisiz denemede 5 dakika blok (Redis)
VLAN              Grup bazli ag segmentasyonu
Sifre Kontrolu    API katmaninda dogrulama
Docker Network    Servisler arasi izole iletisim
Env Variables     Sifreler .env dosyasinda, Git'e gitmiyor

---

## Onemli Notlar

- .env dosyasini asla Git'e commit etme
- Uretim ortaminda testing123 secret'ini degistir
- docker compose up -d --build komutu ile tum sistem ayaga kalkar
