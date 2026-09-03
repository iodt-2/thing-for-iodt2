# Elle deploy (CI/CD yok)

Şirket içi sunucuda iodt2'yi ayağa kaldırma adımları. Registry kullanılmaz —
imajlar sunucunun kendisinde build edilir.

---

## Sunucuda ne olmalı

| Gereksinim | Kontrol |
|---|---|
| Docker Engine + Compose v2 | `docker compose version` |
| İnternet çıkışı | `docker pull hello-world` |
| Bitbucket'a erişim | `git ls-remote https://tlcbitbucket.innova.com.tr/scm/iodt/dt_prototype.git` |
| Root olmayan bir kullanıcı | `docker` grubunda olmalı |

Frontend build'i `npm ci`, backend build'i `pip install` çalıştırır — ikisi de
internet ister. Sunucu kapalı ağdaysa bu akış çalışmaz, imajları başka yerde
üretip `docker save/load` ile taşımak gerekir.

---

## İlk kurulum

```bash
# 1. Kodu al
sudo mkdir -p /opt/iodt2 && sudo chown "$USER" /opt/iodt2
cd /opt/iodt2
git clone https://tlcbitbucket.innova.com.tr/scm/iodt/dt_prototype.git .

# 2. Ortam dosyası
cp .env.example .env
chmod 600 .env
openssl rand -base64 24        # çıktıyı FUSEKI_PASSWORD'e yaz
$EDITOR .env                   # FUSEKI_PASSWORD + CORS_ORIGINS doldur
```

`.env` içinde doldurulması **zorunlu** iki alan:

- `FUSEKI_PASSWORD` — boş bırakılırsa compose hata verir. `admin123` kullanma.
- `CORS_ORIGINS` — kullanıcının tarayıcıda gördüğü adres, ör.
  `https://iodt2.sirket.local`. Yanlışsa arayüz açılır ama hiçbir istek geçmez.

```bash
# 3. Build + test + başlat
scripts/deploy.sh --build v1

# 4. Fuseki dataset'ini oluştur — BİR KEZ, ilk deploy'dan sonra
scripts/bootstrap-fuseki.sh
```

4. adım atlanamaz. Backend dataset'i kendisi oluşturmaz, var olduğunu varsayar
([twin_rdf_service.py:63](backend/app/services/twin_rdf_service.py#L63)) — boş
volume'de her SPARQL isteği 404 döner.

Sonra `http://<sunucu>:3005` açılır.

---

## Güncelleme

```bash
cd /opt/iodt2
scripts/update.sh
```

Hepsi bu: pull → build → testler → `up -d` → smoke test. Smoke başarısızsa
**bir önceki etikete kendiliğinden geri döner**.

Etiketi sen vermezsin — pull sonrası commit SHA'sından üretilir, yani çalışan
sürümün hangi commit olduğu her zaman bellidir. Sunucuda elle düzenlenmiş dosya
varsa script pull'a girmeden durur.

Testleri atlamak (sadece acil durum):

```bash
scripts/update.sh --skip-tests
```

Adımları ayrı ayrı sürmek istersen `update.sh` yerine:

```bash
git pull && scripts/deploy.sh --build <ETIKET>
```

`git pull` her seferinde token soruyorsa bir kez önbelleğe al:

```bash
git config --global credential.helper 'cache --timeout=86400'
```

---

## Geri alma

```bash
scripts/deploy.sh v1      # --build YOK: o etiketli imaj makinede zaten var
```

Hangi etiketlerin durduğunu görmek için:

```bash
docker images 'local/iodt2-*'
cat /opt/iodt2/.deploy-last-tag    # şu an çalışan
```

---

## Yedek — prod'a çıkmadan önce kur

Tüm twin verisi `iodt2-fuseki-data` volume'ünde. Kaybı geri alınamaz.

```bash
# Günlük yedek — cron: 0 3 * * *
docker run --rm \
  -v iodt2-fuseki-data:/data:ro \
  -v /var/backups/iodt2:/backup \
  alpine tar -czf "/backup/fuseki-$(date +\%F).tar.gz" -C /data .
```

Geri yükleme provası yapılmamış yedek yedek değildir — bir kez boş bir
volume'e açıp doğrula.

---

## Sorun giderme

```bash
cd /opt/iodt2
C="docker compose -f docker-compose.prod.yml"

$C ps                      # durum + health
$C logs -f backend
$C logs -f fuseki
$C exec backend python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:3015/health').read())"
```

| Belirti | Sebep |
|---|---|
| `frontend` hiç başlamıyor | `backend` unhealthy — compose sağlıklı olmasını bekliyor |
| Arayüz açılıyor, istekler CORS hatası | `.env`'de `CORS_ORIGINS` yanlış |
| Her SPARQL isteği 404 | `bootstrap-fuseki.sh` çalıştırılmamış |
| `FUSEKI_PASSWORD tanimli degil` | `.env` boş bırakılmış |
| Build'de npm/pip hatası | Sunucunun internet çıkışı yok veya proxy gerekiyor |

Fuseki ve backend **host'a açılmaz** (compose'da `ports` yok), sadece
`iodt2-network` içinden erişilir. Dışarı sadece frontend çıkar. Fuseki'ye
bakman gerekirse ağın içinden tek seferlik bir istemci çalıştır:

```bash
. /opt/iodt2/.env
docker run --rm --network iodt2-network curlimages/curl:latest   -sS -u "admin:$FUSEKI_PASSWORD" 'http://fuseki:3030/$/datasets'
```
