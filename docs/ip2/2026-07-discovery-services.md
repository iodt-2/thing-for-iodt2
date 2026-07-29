# Temmuz 2026 — Discovery Services & SPARQL tabanlı keşif

**İş paketi:** İP2 — Dağıtık dijital ikiz mimarisi ve Açık Bilgi Modeli
**Dilim teması:** Haziran'da yayınlanan model üstüne keşif katmanı kur.
**Durum:** ✅ Tamamlandı — T1–T8, 221 test geçiyor

---

## Hedef

Sistemde keşif diye bir katman yoktu; yalnız isim üzerinde substring araması vardı.
Bu dilim W3C WoT Discovery profiline yaklaşan bir **Thing Description Directory**
davranışı ekledi ve iki anlamlı keşif yeteneği getirdi:

- **Nerede?** — coğrafi yakınlık
- **Ne yapabiliyor?** — yetenek (capability)

Hedef cümle karşılandı: *"Bu noktanın 1 km çevresindeki twin'leri getir"* ve
*"sıcaklık ölçen twin'leri getir"* birer HTTP çağrısı.

---

## Haziran'a bağımlılık — karşılandı

| Temmuz işi | Gerektirdiği Haziran işi | Durum |
|---|---|---|
| T3 — yakınlık keşfi | H1 — geo triple'ları | ✅ (aşağıdaki bulguya bakınız) |
| T4 — yetenek keşfi | H2 — SOSA/QUDT alignment | ✅ |
| T5 — sorgu kataloğu | H4 — vokabüler ontolojide | ✅ |

---

## İş kalemleri

### T1 — Self-description (`/.well-known/wot`) ✅

- [x] `backend/app/api/v2/discovery.py` — `well_known_router` kök seviyede kayıtlı
- [x] `GET /.well-known/wot` — `application/td+json` (TD 1.1'de kayıtlı medya tipi)
- [x] Affordance'lar **kayıtlı rotalardan türetiliyor**
- [x] Spec-tanımlı ve iodt2 uzantısı ayrımı belgede açıkça işaretli (`ts:extension`)

**Tasarım kararı:** yetenek listesi elle yazılmıyor. `register_affordance()` bir
FastAPI rota adına bağlanıyor; rota yoksa affordance yayınlanmıyor ve uyarı
loglanıyor. Testle kanıtlandı: var olmayan bir rotaya bağlı sahte affordance
TD'ye çıkmıyor. **Directory var olmayan bir ucu ilan edemez.**

---

### T2 — TDD uyumlu listeleme ✅

- [x] `GET /api/v2/things` — gerçek WoT Thing Description dizisi, `application/ld+json`
- [x] `GET /api/v2/things/{name}` — tekil TD, `application/td+json`
- [x] `Link: rel="next"` sayfalama + `X-Total-Count`
- [x] `thing_description_service.py` — TwinInterface → TD dönüşümü
- [x] Mevcut `/rdf/interfaces` bozulmadan duruyor (paralel yol)

**Dönüşüm:** property'ler TD affordance'ına (`readOnly`, `unit`, `minimum`,
`maximum`), komutlar `actions`'a, ilişkiler `links`'e, konum `geo:lat`/`geo:long`'a.

**Sayfalama iki adımlı yapıldı.** Tek sorguda yapılsaydı property/command/relationship
satırları çarpacağı için `LIMIT` bir thing'i **ortasından kesecekti**. Önce interface
URI'lerinin bir sayfası, sonra o URI'ler için detay sorgusu.

#### ⚠ Uyum eksiği — `forms` yok

WoT TD'lerinde property'ler normalde protokol uçlarına işaret eden `forms` taşır.
Bu platform twin'leri **tarif ediyor**, **proxy'lemiyor** — okunacak bir cihaz ucu
yok. 404 verecek uçlar uydurmak yerine belgede `ts:noProtocolBinding: true` ile
durum açıkça belirtiliyor. Testle korunuyor.

---

### T3 — Coğrafi yakınlık keşfi ✅

- [x] `GET /api/v2/discovery/nearby?lat=&lon=&radius_km=&limit=`
- [x] `backend/app/core/geo.py` — saf haversine + bounding box
- [x] SPARQL'de bbox ön-filtresi, Python'da kesin haversine + sıralama
- [x] Yanıtta `ts:distanceKm`
- [x] Koordinatsız twin'ler sessizce eleniyor

**Bounding box'ta bilinçli tercih:** üç uç durumda (kutba yakın, antimeridyen
geçişi, çok büyük yarıçap) tek bir min/max boylam aralığı alanı ifade edemiyor.
Bu durumlarda **boylam sınırı düşürülüyor**. Box yalnız bir optimizasyon; gevşek
olabilir, **dar olamaz** — dar olsaydı sonuç sessizce kaybolurdu. Kesin sınırı
haversine koyuyor. 24 yönde test edilerek daire içindeki hiçbir noktanın box
dışında kalmadığı doğrulandı.

Haversine bilinen mesafelerle sınandı: İstanbul–Ankara 349 km, Londra–Paris 344 km,
1 derece enlem 111.2 km.

---

### T4 — Yetenek keşfi ✅

- [x] `GET /api/v2/discovery/by-capability?property=&unit=&thing_type=&dtdl=`
- [x] Kriterler AND ile birleşiyor; en az bir kriter zorunlu (yoksa 400)
- [x] `property` alt dizge (harf duyarsız), diğerleri tam eşleşme (harf duyarsız)
- [x] `GET /api/v2/discovery/capabilities` — facet envanteri

**Facet envanteri sabit liste değil** — store'da gerçekten ne varsa onu raporluyor,
böylece arayüz boş dönecek filtre önermiyor.

---

### T5 — SPARQL keşif profili + sorgu kataloğu ✅

- [x] `GET /api/v2/discovery/sparql?q=` veya `?saved=<id>` — salt okunur
- [x] Haziran'ın H6 guard'ı **yeniden kullanılıyor**, ayrı kontrol yazılmadı
- [x] `backend/app/queries/discovery_queries.yaml` — 20 sorgu
- [x] `GET /api/v2/discovery/queries` (+ `?category=`) ve `/queries/{id}`
- [x] `query_catalog_service.py` — yükleme anında SPARQL doğrulaması

**Katalog koddan çıktı.** `SearchThings.jsx` içine gömülü 16 şablon programatik
olarak çıkarıldı ve her biri `prepareQuery` ile doğrulandı (16/16). Üstüne keşif
odaklı 4 sorgu eklendi. Artık yeni bir kayıtlı arama eklemek frontend derlemesi
gerektirmiyor.

**Yükleyici bozuk girdiye dayanıklı:** geçersiz SPARQL, eksik alan ve mükerrer id
uyarıyla düşürülüyor; dosya yoksa veya YAML bozuksa boş liste dönüyor, çökmüyor.

---

### T6 — Jena text index (Lucene) ✅ (opt-in)

- [x] `fuseki/text-index.ttl` — TDB2 + `text:TextDataset` assembler
- [x] `docker-compose.yml` — config salt-okunur mount
- [x] `FUSEKI_TEXT_INDEX` ayarı, **varsayılan kapalı**
- [x] `search()` text yolu + `CONTAINS` fallback
- [x] **Çalışma anı yetenek kontrolü** (aşağıda)
- [x] Canlı Fuseki 5.1.0'da ayrı bir deneme dataset'inde doğrulandı

**Kapsam kararı:** indeks çalışan dataset'e **kurulmadı**. Dataset tanımını
değiştirmek geri alınması zor bir işlem; ayrı bir onaylı adım olmalı. Bu haliyle
sistem indekssiz çalışıyor ve bayrak yanlışlıkla açılsa bile güvenli.

---

### T7 — Keşif arayüzü ✅

- [x] `frontend/src/services/discoveryService.js`
- [x] `SearchThings.jsx`'e iki yeni mod: **Yakındakiler**, **Yeteneğe Göre**
- [x] Mevcut üç mod (`standard`/`value`/`sparql`) **hiç değiştirilmedi**
- [x] Yakınlık modunda harita ile merkez seçimi + yarıçap kaydırıcısı
- [x] Yetenek modunda facet endpoint'inden dolan seçiciler
- [x] Sorgu kataloğu backend'den, gömülü dizi **fallback** olarak korundu
- [x] i18n 15 anahtar, TR ve EN eşit
- [x] `vite build` temiz, container 200

---

### T8 — Testler ✅

- [x] `conftest.py` — `LocalTwinStore` fixture'ı
- [x] `test_discovery_geo.py` (40), `test_discovery_capability.py` (36),
      `test_tdd_conformance.py` (21), `test_discovery_queries.py` (24)

**Test altyapısı kararı:** servis metotları mock'lanmadı. `LocalTwinStore`,
servisin **gerçek SPARQL metnini** aynı named-graph düzenine sahip bir rdflib
Dataset'ine karşı çalıştırıyor. Mock'lasaydık sorgular hiç sınanmazdı — ilginç
hatalar tam da orada.

---

## Kabul kriterleri

| # | Kriter | Durum |
|---|---|---|
| 1 | `docker compose up -d --build` temiz kalkıyor | ✅ Canlı doğrulandı |
| 2 | `pytest` geçiyor | ✅ **221 passed** |
| 3 | Mevcut `/rdf/*` ve `/fuseki/*` bozulmadı | ✅ Canlı 200 |
| 4 | Hedef demo cümlesi tek çağrıyla | ✅ |
| 5 | W3C WoT Discovery uyum matrisi | ✅ Aşağıda |
| 6 | `vite build` temiz, arayüz ayakta | ✅ |

---

## W3C WoT Discovery uyum matrisi

| Yetenek | Durum | Not |
|---|---|---|
| Self-description (`/.well-known/wot`) | ✅ | `@type: ThingDirectory`, `application/td+json` |
| TD listeleme (`GET /things`) | ✅ | JSON-LD dizi |
| `Link: rel="next"` sayfalama | ✅ | Zincir baştan sona yürüyor |
| Tekil TD getirme | ✅ | `application/td+json`, 404 |
| SPARQL keşif profili | ✅ | GET, salt okunur, guard'lı |
| TD'lerde `forms` | ❌ | Protokol bağlaması yok; `ts:noProtocolBinding` ile bildiriliyor |
| JSONPath / XPath keşif profilleri | ❌ | Uygulanmadı |
| TD kaydı (POST/PUT/DELETE) | ❌ | Kayıt akışı form → YAML → RDF üzerinden; TDD yazma API'si yok |
| TTL / expiry | ❌ | Ağustos backlog'unda |
| DNS-SD / CoRE Link Format | ❌ | Kapsam dışı |
| Coğrafi keşif | ➕ | Spec'te yok, iodt2 uzantısı |
| Yetenek keşfi | ➕ | Spec'te yok, iodt2 uzantısı |

✅ karşılanıyor · ❌ karşılanmıyor · ➕ spec dışı ek yetenek

---

## Tespit edilip giderilen sorunlar

Docker'ın açılmasıyla yapılan canlı doğrulama, yerel koşumda görünmeyen iki
sorunu ortaya çıkardı. Testler ise üç tanesini daha yakaladı.

### 1. H1 çalışıyordu ama veri onu tetiklemiyordu

Canlı Fuseki'de **14 twin, 0 geo triple**. Zincir:
- Fuseki volume'ü H1 öncesi kodla yazılmış grafları taşıyor
- Seed servisi "graf zaten var" diye atlıyor (`loaded=0, skipped=14`)
- Seed YAML'larının 8'inde interface konumu var, **hiçbirinde** instance konumu yok,
  6'sında hiç konum yok

Temmuz'un manşet demosu gerçek veride boş dönecekti.

**Çözüm:** eksik 6 seed'e gerçek Kadıköy koordinatları eklendi, 14'ünün instance
dosyalarına da konum yazıldı, `SEED_FORCE_RELOAD` ayarı eklendi. Sonuncusu genel
bir operasyonel boşluktu — **seed YAML'ı değiştirmek mevcut kuruluma hiç
yansımıyordu**. Sonuç: 0 → 28 geo triple.

### 2. Katalog sorgularında tenant filtresi yok

`twins-without-location` 0 yerine 9 döndü; dokuzu da `iodt2` tenant'ında. Sorgular
frontend'den birebir taşınmıştı, orada da filtre yoktu — ama artık `X-Tenant-ID`
kabul eden bir uçtan servis ediliyorlar.

**Çözüm:** rastgele SPARQL'i yeniden yazmak fragile olduğu için açık bir yer
tutucu (`#{TENANT}`) kullanıldı. Sorgu onu taşıyorsa tenant filtresine dönüşüyor,
taşımıyorsa yanıtta `tenant_scoped: false` olarak **bildiriliyor**. Frontend'den
gelen 16 sorgunun davranışı değiştirilmedi — mevcut kayıtlı aramaların anlamı
sessizce kaymasın diye; yalnızca işaretlendiler.

### 3. Assembler endpoint adları — sistemi bozacaktı

İlk text-index config'i `405` verdi. `fuseki:endpoint` bloklarına `fuseki:name`
verilmediği için uçlar `/query`, `/update`, `/data` altında yayınlanmamıştı.
`TwinRDFService` tam da bu yolları kullanıyor — **config olduğu gibi kurulsaydı
sistem bozulurdu.** Adlar açıkça verildi.

### 4. `text:query` indeks yokken sessizce her şeyi döndürüyor

Fallback `try/except` ile yazılmıştı. Ama indeksi olmayan dataset'te Jena **hata
vermiyor**: eşleşmesi imkânsız bir terim için bile tüm store'u döndürüyor
(28 = tüm twin'ler). Bayrağı yanlışlıkla açan biri, logda tek bir hata görmeden
aramanın "her şeyi döndürmesi" ile karşılaşırdı.

### 5. Yetenek kontrolünde yanlış pozitif

(4)'ün çözümü olarak yazılan probe'u test **yanlış pozitif** verirken yakaladı:
`text:query`'yi hiç bilmeyen bir motor sessizce **0** döndürüyor, probe bunu
"indeks var" sanıyordu. Bu durumda arama sessizce **hep boş** dönerdi — ters
yönde ama eşit derecede sessiz bir hata.

**Çözüm:** iki kontrollü probe.
- **Negatif kontrol:** var olması imkânsız bir terim 0 döndürmeli
- **Pozitif kontrol:** store'da bulunduğu bilinen bir token ≥1 döndürmeli

İkisi birden sağlanmazsa indeks çalışmıyor kabul edilip substring'e düşülüyor.
Sonuç bir kez ölçülüp önbelleğe alınıyor.

### 6. `MapComponent`'te olmayan prop

Arayüzde `onLocationSelect` prop'u kullanılmıştı — böyle bir prop yok, doğrusu
`onMapClick`. **Derleme sorunsuz geçiyordu**; haritaya tıklamak sessizce hiçbir
şey yapmayacaktı. Bileşenin gerçek sözleşmesi okunarak düzeltildi.

### 7. `'` kaçışı sorguları bozuyordu

Enjeksiyon testlerinden biri sorguyu parse hatasına düşürdü. Çift tırnaklı literal
içinde `'` kaçırmak gereksiz; SPARQL 1.1 `\'` ECHAR'ına izin verse de rdflib
reddediyor. `Kadıköy'de` gibi apostroflu meşru bir arama motor değişiminde
patlardı. Kaçış listesinden çıkarıldı, mevcut `search()` de ortak helper'a bağlandı.

> Bu, Fuseki/ARQ üzerinde muhtemelen çalışıyordu — rdflib daha katı. Yani
> "üretimde bozuktu" değil, **taşınabilirlik tuzağıydı**.

---

## Çıktılar

- [x] **W3C WoT Discovery uyum matrisi** — yukarıda, karşılanmayanlar dâhil
- [x] **Keşif API'si** — 9 yeni uç
- [x] **Test raporu** — 221 pytest testi (Haziran 100 + Temmuz 121)
- [x] **Canlı doğrulama** — gerçek Kadıköy verisiyle, aşağıda
- [x] **7 tespit edilip giderilen sorun** — yukarıda

### Yeni uçlar

| Uç | İşlev |
|---|---|
| `GET /.well-known/wot` | Directory self-description |
| `GET /api/v2/things` | TD listesi + Link sayfalama |
| `GET /api/v2/things/{name}` | Tekil TD |
| `GET /api/v2/discovery/nearby` | Coğrafi yakınlık |
| `GET /api/v2/discovery/by-capability` | Yetenek keşfi |
| `GET /api/v2/discovery/capabilities` | Facet envanteri |
| `GET /api/v2/discovery/sparql` | Salt okunur SPARQL keşfi |
| `GET /api/v2/discovery/queries` | Sorgu kataloğu |
| `GET /api/v2/discovery/queries/{id}` | Tekil kayıtlı sorgu |

### Canlı demo (gerçek Kadıköy verisi)

```
GET /api/v2/discovery/nearby?lat=40.9836&lon=29.0303&radius_km=1
  iodt2-seismic-sensor-1        0.0000 km
  iodt2-temp-sensor-hospital    0.0000 km
  iodt2-moda-caddesi            0.4625 km
  iodt2-kadikoy-baz             0.4899 km
  iodt2-sismik-sensor-z1        0.5425 km
  iodt2-moda-rezidans-a         0.5564 km
  iodt2-sismik-sensor-z2        0.5703 km
  iodt2-weather-station-1       0.7546 km
  iodt2-kadikoy-hospital        0.9533 km

GET /api/v2/discovery/by-capability?property=temperature
  iodt2-temp-sensor-hospital    temperature (°C), alertThreshold (°C)
  iodt2-temp-sensor-street      temperature (°C), alertThreshold (°C)
```

---

## Text index'i etkinleştirme (opt-in)

> Bu adım dataset tanımını değiştirir. Önce yedek alın.

1. Fuseki'yi durdurun: `docker compose stop fuseki`
2. `fuseki/text-index.ttl` içindeki yer tutucuları doldurup
   `/fuseki/configuration/<dataset>.ttl` olarak yerleştirin:
   - `${DATASET}` → `iodt2-thing-description`
   - `${DB_DIR}` → `/fuseki/databases/iodt2-thing-description`
   - `${IDX_DIR}` → `/fuseki/text-index/iodt2-thing-description`
3. Mevcut veri için indeksi bir kez inşa edin (`jena.textindexer`)
4. Backend ortamına `FUSEKI_TEXT_INDEX=true` ekleyip yeniden başlatın
5. Logda `text index` uyarısı **olmadığını** doğrulayın

Adım 3 atlanırsa: çalışma anı probe'u indeksin boş olduğunu tespit eder, hata
loglar ve substring aramasına düşer. **Sistem bozulmaz, arama çalışmaya devam eder.**
