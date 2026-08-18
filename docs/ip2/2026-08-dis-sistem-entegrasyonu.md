# Ağustos 2026 — Dış sistem entegrasyonu

**İş paketi:** İP2 — Dağıtık dijital ikiz mimarisi ve Açık Bilgi Modeli
**Dilim teması:** Platform, IoDT2 içindeki diğer kurumların servislerinden veri
alır ve kendi verisini onlara verir. Her karşı taraf **bir adaptör**, çekirdek
kod sağlayıcıdan bağımsız kalır.
**Durum:** 🟡 Faz 1 ve Faz 2 tamam (`feat/external-integration-phase1`)

---

## Kapsam — tek bir kuruma özel değil

IoDT2 çok paydaşlı. NETCAD ilk **canlı** karşı taraf olduğu için ilk adaptör o,
ama mimari tek entegrasyona göre kurulmaz. Kural:

- Çekirdek (`importer`, provenance, tenant ayrımı, idempotency) **sağlayıcıdan
  habersizdir**
- Her kurum bir `ExternalProvider` uygulaması: kendi base URL'i, kendi veri
  kümeleri, kendi alan eşlemesi
- Yeni kurum eklemek = yeni bir dosya + registry'ye bir satır. API uçları,
  testler ve RDF yazma yolu değişmez

```
backend/app/services/integrations/
  base.py        — ExternalProvider sözleşmesi, ExternalThing veri sınıfı
  registry.py    — sağlayıcı kaydı (key → provider)
  netcad.py      — ilk adaptör
  <kurum>.py     — sonraki adaptörler buraya
  importer.py    — sağlayıcı-agnostik içe alma akışı
```

API de sağlayıcı-agnostik:

```
GET  /api/v2/integrations/providers
GET  /api/v2/integrations/{provider}/health
POST /api/v2/integrations/{provider}/import/{dataset}
```

---

## Fazlar ve sıralama gerekçesi

Sıra **bağımlılık ve risk**e göre; işlevsel çekiciliğe göre değil.

| Faz | İçerik | Yön | Dışa açılma gerekir mi |
|---|---|---|---|
| Adım 0 | Karşı tarafa cevap: arayüz dokümanı + örnek veri | — | hayır |
| **Faz 1** | **Tüketim — dış veriden twin üretimi** | dış → biz | hayır |
| Faz 2 | Simülasyon eşleşmesi + zincir etki | dış → biz | hayır |
| Faz 3 | Auth / TLS / rate limit | — | ön koşul |
| Faz 4 | Yayınlama (GeoJSON + ingest) | biz → dış | evet |
| Faz 5 | Sürekli senkron, federasyon | çift yön | evet |

1. **Tüketim önce.** Karşı tarafın API'si zaten açık. Onu çağırmak için bizden
   hiçbir şey yayına çıkmaz — public deploy, TLS, auth, kurumsal veri onayı
   gerekmez. Sıfır güvenlik yüzeyi ile ilk somut çıktı.
2. **Simülasyon ikinci.** O da bize doğru akıyor. Platformun asıl iddiası —
   ilişki grafı üzerinden zincir etki — burada kanıtlanır, hâlâ dışa açılmadan.
3. **Dışa açılma üçüncü.** Kendi başına demo üretmez; gösterilecek bir şey
   oluştuktan sonra yapılır.
4. **Yayınlama dördüncü.** Faz 3 olmadan yapılamaz, Faz 1–2 olmadan da
   gönderilecek anlamlı içerik yok.

```
Adım 0 ─── bağımsız

Faz 1 (tüketim) ──► Faz 2 (simülasyon + zincir etki)
                         │
Faz 3 (auth/TLS) ────────┴──► Faz 4 (yayınlama) ──► Faz 5 (sürekli senkron)
                                                          ▲
                     backlog A1 (versiyonlama), A2 (TTL) ─┘
```

Faz 1 ile Faz 3 paralel yürütülebilir; aralarında teknik bağ yok.

---

## Adım 0 — Karşı tarafa cevap (kod yok)

| Talep | Bizdeki karşılık |
|---|---|
| Servis/API uç adresi + arayüz dokümanı | `GET /.well-known/wot` (WoT Thing Directory self-description, makine okunur), `GET /api/v2/ontology` (bilgi modeli, Turtle/JSON-LD), OpenAPI `/docs` |
| Örnek veri seti / test senaryosu | Kadıköy demo — 14 twin (`backend/data/seed/kadikoy_demo/`) |
| Erişim/yetki bilgisi | **Faz 3'te** — şu an auth katmanı yok |
| Teknik iletişim kişisi | — |

Belirtilecek mimari fark: karşı taraf 3B harita + GeoJSON katmanı üzerinden
çalışıyor, biz RDF/SPARQL + WoT TD + **ilişki grafı** üzerinden. Ortak payda
coğrafi nokta (`app/core/geo.py`). Katma değerimiz katman değil,
`feeds` / `dependsOn` / `controls` zinciri üzerinden **ikincil etki çıkarımı**.

---

## Faz 1 — Tüketim: dış veriden twin üretimi

**Dışa açılma gereksinimi:** yok. **Hedef tenant:** sağlayıcı başına ayrı
(`netcad`), `default` kirlenmez.

### İlk adaptör: NETCAD

Base URL: `https://netcad-iodt.westeurope.cloudapp.azure.com/api`
Şemalar canlı uçtan çekildi, örnekler: `docs/ip2/netcad-samples/`.

**Twin üretenler**

| Uç | Gerçek alanlar | Bizdeki karşılık |
|---|---|---|
| `GET /telecom/towers` | `tower_id`, `latitude`, `longitude`, `district`, `operator`, `height`, `tower_type`, `osm_id`, `source` | `netcad-tower-{id}` — TwinInterface + TwinInstance, geo triple'ları, `height` (m) sayısal attribute |
| `GET /buildings/inventory?use_osm=true` | `building_id`, `latitude`, `longitude`, `district`, `building_type`, `risk_level`, `data_quality`, `osm_type` | `netcad-building-{id}` |
| `GET /risk/assessment` | `district`, `riskScore`, `population`, `totalBuildings`, `highRisk`/`mediumRisk`/`lowRisk`, `casualties`, `economicValue`, `expectedLoss` | `netcad-district-{slug}` — `thing_type: system` |

**Twin üretmeyenler**

| Uç | Gerçek alanlar | Kullanım |
|---|---|---|
| `GET /earthquakes/real?days=&min_mag=` | `id`, `magnitude`, `depth`, `latitude`, `longitude`, `location`, `time`, `source` (AFAD) | Olay akışı — Faz 2. Twin değil |
| `POST /simulation/earthquake` | — | Faz 2 |
| `GET /scenarios/list` · `POST /scenarios/run` | `id`, `name`, `magnitude`, `buildingsAffected`, `casualties`, `economicLoss` | Faz 2 |
| `GET /system/health` | `status`, `components{}` | Import öncesi sağlık kontrolü |

**Veri kalitesi notu:** çekim anında `towers` ve `buildings` yanıtları
`"source": "Fallback Data"` döndü (OSM sorgusu düşmüş, 50'şer örnek kayıt).
Eşleme buna göre savunmacı yazıldı; alan yoksa attribute üretilmez.
`risk/assessment` **koordinat içermiyor** — ilçe twin'leri konumsuz, bu yüzden
`/discovery/nearby` sonuçlarında görünmezler. Beklenen davranış.

### İlişki üretimi

İlçe → `contains` → bina/kule. Yön kritik: `contains` kaynağı ilçedir, o yüzden
yükleme sırası **önce çocuklar, sonra ilçe** (seed'deki `_LOAD_ORDER` mantığı,
CLAUDE.md kısıtı). Ters yön (`isContainedIn`) `_insert_inverse_relationships`
tarafından otomatik yazılır — elle eklenmez.

### İş kalemleri

| # | İş | Durum |
|---|---|---|
| N1 | `integrations/base.py` — `ExternalProvider` sözleşmesi + `ExternalThing` | ✅ |
| N2 | `integrations/registry.py` — sağlayıcı kaydı | ✅ |
| N3 | `integrations/netcad.py` — NETCAD adaptörü, üç veri kümesi | ✅ |
| N4 | `integrations/importer.py` — sağlayıcı-agnostik akış: fetch → map → YAML → `store_twin_yaml` | ✅ |
| N5 | `api/v2/integrations.py` — providers / health / import uçları | ✅ |
| N6 | Köken triple'ları — `ts:externalSource`, `ts:externalId`, `ts:externalUrl`, `ts:fetchedAt` | ✅ |
| N7 | Idempotency — içerik hash'i (`ts:contentHash`); değişmemiş thing yeniden yazılmaz | ✅ |
| N8 | Ontoloji: yeni terimler yayınlanan modele eklendi (v2.1.0) | ✅ |
| N9 | Testler — eşleme, provenance, idempotency, uç davranışı | ✅ 28 test |

**Yeni RDF yazma kodu yok.** Akış mevcut zinciri kullanır:
`TwinGeneratorService` → `TwinRDFService.store_twin_yaml`.

### Riskler

- **Versiyonlama açığı.** N7 (hash ile atlama) tam çözüm değil; içerik
  değiştiğinde graf yine override ediliyor. Backlog **A1 (versiyonlama +
  arşivleme)** periyodik senkronun (Faz 5) gerçek ön koşulu.
- **Ölçek.** Şu an 50'şer kayıt geliyor, sorun yok. Gerçek OSM envanteri
  açıldığında binlerce kayıt gelir; her thing ayrı named graph = graf patlaması.
  `limit` ve `bbox` parametreleri bu yüzden baştan var.
- **Karşı taraf şeması sözleşmeli değil.** Alan adları haber verilmeden
  değişebilir. Eşleme savunmacı; testler `docs/ip2/netcad-samples/` altındaki
  gerçek yanıtlara bağlı, şema kayarsa test kırılır.

**Faz 1 çıktısı:** dış envanterle dolu `netcad` tenant'ı; Graph View,
`/discovery/nearby` ve `/discovery/capabilities` üzerinde çalışır durumda.

### Çıktılar

**Uçlar**

```
GET  /api/v2/integrations/providers
GET  /api/v2/integrations/{provider}/health
POST /api/v2/integrations/{provider}/import/{dataset}
       ?tenant=&limit=&bbox=&force=&dry_run=
```

Doğru yükleme sırası — ilçe, çocuklarına `contains` ile bağlanır:

```bash
curl -X POST "http://localhost:3015/api/v2/integrations/netcad/import/buildings"
curl -X POST "http://localhost:3015/api/v2/integrations/netcad/import/towers"
curl -X POST "http://localhost:3015/api/v2/integrations/netcad/import/districts"
```

Sıra bozulursa import başarısız olmaz; hedefi olmayan ilişkiler düşürülür ve
`dropped_links` sayacında raporlanır. Grafta hayalet düğüm bırakmak, eksik
ilişkiden daha kötü.

**Ontoloji — v2.0.0 → v2.1.0**

| Terim | Ne için |
|---|---|
| `ts:Attribute`, `ts:hasAttribute`, `ts:attributeName`, `ts:attributeValue` | Dış kaynaktan gelen **değerler** (operatör adı, kule yüksekliği, risk skoru). `ts:Property` şema bildirir ve değer taşımaz — envanter verisi oraya konsaydı bütün değerler sessizce kaybolurdu |
| `ts:externalSource`, `ts:externalId`, `ts:externalUrl`, `ts:fetchedAt` | Köken. Federe bir graf, aynadığı veriyi kendi verisinden ayırt edemezse güvenle yenileyemez |
| `ts:contentHash` | Idempotency. Store, named graph'ı bütünüyle değiştirir; değişmemiş kayıt yeniden yazılmamalı |

Sayısal attribute değerleri `xsd:decimal` yazılır, SPARQL'de karşılaştırılabilir.

**Doğrulama**

- 28 entegrasyon testi + mevcut 221 test → 249 test geçiyor
- Depolama testleri `LocalTwinStore` üstünde gerçek üretici ve gerçek triple
  yazıcı ile koşuyor; grafa ulaşmayan bir provenance triple'ı testi düşürür
- Canlı uçtan kuru çalıştırma: `towers` 50, `buildings` 50 (hepsi konumlu),
  `districts` 3 ve 54 `contains` ilişkisi
- **Fuseki'ye uçtan uca yazma denenmedi** — bu makinede Docker Desktop kapalı.
  `docker compose up -d --build` sonrası import uçlarının gerçek store üzerinde
  çalıştırılması gerekiyor

---

## Faz 2 — Simülasyon eşleşmesi ve zincir etki

**Bağımlılık:** Faz 1. **Dışa açılma gereksinimi:** yok.

```
POST /api/v2/scenarios/{id}/simulate
  1. tenant grafından twin'ler + koordinatlar
  2. karşı tarafın simülasyon ucu → yer hareketi + hasar tahmini
  3. hasar → etkilenen twin'lerin property değerlerine yazılır
  4. hasarlı twin'in ilişkileri → ts:Degraded
  5. graf yayılımı: feeds / dependsOn zinciri ile ikincil kesintiler
     (baz istasyonu düştü → hangi izleme sistemi kör kaldı)
  6. sonuç raporu
```

| # | İş | Durum |
|---|---|---|
| N10 | Simülasyon istemcisi + istek gövdesi eşlemesi | ✅ |
| N11 | Hasar sonucu → çalıştırma grafı + opsiyonel `ts:Degraded` | ✅ |
| N12 | Yayılım algoritması — derinlik sınırı, sönümleme, döngü koruması | ✅ |
| N13 | Gerçek deprem akışı (`/earthquakes/real`) → olay beslemesi | ✅ |
| N14 | Frontend — senaryo paneli, doğrudan hasar + zincir etki listesi | ✅ |

### Karşı tarafın simülasyon şeması (canlı uçtan çıkarıldı)

`POST /simulation/earthquake` — gövde:

```json
{ "epicenter_lat": 40.98, "epicenter_lon": 29.03, "magnitude": 6.5, "depth": 10,
  "buildings": [ { "building_id": "...", "latitude": 0, "longitude": 0, "building_type": "RC_Mid" } ] }
```

Kritik nokta: **`buildings` dizisini biz dolduruyoruz**. Twin'lerimizi kendi
interface adlarıyla gönderiyoruz, hasar da o adlarla geri geliyor — sonradan
koordinat eşleştirmeye gerek kalmıyor. Yanıt: `building_damages[]` içinde
`damage_state`, `damage_probability`, `pga`, `distance_km`, `casualties`,
`economic_loss`.

`epicenter_lat`/`epicenter_lon` dışındaki adlandırmalar (`latitude`, `epicenter{}`)
reddediliyor — şema deneyerek bulundu, `docs/ip2/netcad-samples/` altındaki
örnekler bunun kaydı.

### Zincir etki — yön nereden geliyor

Yayılım yönü kodda sabit değil, ontolojide: yeni `ts:impactDirection`.
Mevcut `ts:propagationDirection`'dan **kasıtlı olarak ayrı**, çünkü o bir arayüz
ipucu (kenar hangi yöne akar) ve iki soru aynı değil:

| Tip | Okunuş | Arıza yönü |
|---|---|---|
| `feeds` | kaynak besler | kaynak → hedef (besleme kesilir) |
| `controls` | kaynak yönetir | kaynak → hedef (yöneten gider) |
| `contains` | kaynak içerir | çift yönlü |
| `monitors` | kaynak izler | hedef → kaynak (**izlenen giderse izleyen körelir**) |
| `dependsOn` | kaynak muhtaç | hedef → kaynak (muhtaç olunan gider) |

Yeni bir ilişki tipi eklemek, onu otomatik olarak etki analizine dahil eder —
algoritmaya dokunmak gerekmez.

Algoritma `app/core/propagation.py` içinde saf fonksiyon: BFS, hop başına
sönümleme (varsayılan 0.6), derinlik sınırı (3), döngü koruması, `ts:Inactive`
ilişkiler taşımaz, en güçlü yol kazanır.

### Çıktılar

```
POST /api/v2/simulation/{provider}/earthquake
GET  /api/v2/simulation/runs?tenant=
GET  /api/v2/simulation/runs/{run_id}?tenant=
GET  /api/v2/integrations/{provider}/events?days=&min_magnitude=
```

Frontend: `/simulation` sayfası — senaryo formu, gerçek deprem listesinden
seçim, doğrudan hasar ve zincir etki panelleri.

**Ontoloji 2.1.0 → 2.2.0:** `ts:SimulationRun`, `ts:Impact`, `ts:ImpactKind`
(`ts:DirectImpact` / `ts:PropagatedImpact`), `ts:severity`, `ts:damageState`,
`ts:peakGroundAcceleration`, `ts:distanceKm`, `ts:propagationDepth`,
`ts:propagatedFrom`, `ts:viaRelationshipType`, `ts:impactDirection`.

### İki tasarım kararı

**Çalıştırma kendi grafına yazılır** — `http://twin.io/graphs/{tenant}/simulation/{run_id}`.
Twin graflarına dokunulmaz. Store bir named graph'ı bütünüyle değiştirdiği için
bir varsayım senaryosunun envanteri ezmesi kabul edilemez; ayrıca böylece
çalıştırma geçmişi birikiyor.

**İlişki degrade etmek opsiyonel** — `apply_status=true` (varsayılan kapalı).
Açıldığında etkilenen ilişkiler `ts:Degraded` olur; silme değil durum değiştirme,
mevcut kuralla aynı.

### Doğrulama

- 36 yeni test (16 yayılım + 20 simülasyon), toplam **285 test geçiyor**
- Canlı çalıştırma: M6.8 Kadıköy senaryosu, 3 twin gönderildi, hasar geri alındı
- **Fuseki'ye uçtan uca yazma hâlâ denenmedi** — Docker Desktop kapalı

### Karşı tarafın modeli hakkında not

Sonuçlar mühendislik çıktısı gibi kullanılmamalı. Merkez üssüne yakın her şey
`pga 2.0` / `Complete` olarak doyuma ulaşıyor, 186 km uzaktaki bir yapı için
M6.8'de `Extensive` dönüyor. Sıralama olarak anlamlı, mutlak değer olarak değil.
Adaptör bunu olduğu gibi aktarıyor, düzeltmiyor — düzeltmek sessizce başka bir
model uydurmak olurdu.

### Faz 2'ye alınmayanlar

`POST /scenarios/run` **karşı tarafta kayıt oluşturuyor** (kendi senaryo
listelerine yazıyor). Yani okuma değil yazma; dışa veri gönderme faz'ı olan
Faz 4'e ait. Faz 2 yalnızca `POST /simulation/earthquake` kullanıyor — o
tarafta hiçbir şey bırakmıyor.

---

## Faz 3 — Dışa açılma ve güvenlik

**Faz 4'ün ön koşulu.** Kod az, altyapı çok.

| # | İş | Not |
|---|---|---|
| N15 | Public HTTPS uç — reverse proxy + TLS | |
| N16 | `X-API-Key` auth, anahtar tenant'a bağlı | `X-Tenant-ID` şu an **doğrulanmıyor** — herkes her tenant'ı okuyabilir. Asıl açık bu |
| N17 | Rate limit | |
| N18 | `POST /twin/rdf/query` dışarıya read-only | `sparql_guard.py` sınırları var; UPDATE'in dışarıya kapalılığı testle sabitlensin |
| N19 | CORS whitelist | `docker-compose.yml` prod ortamında `CORS_ORIGINS` hâlâ `localhost` |
| N20 | Yazma uçlarının dışa kapalılığı | Okuma ve yazma ayrı yetki |

**Karar gerektiren:** hangi tenant'ın hangi verisi dışarı çıkabilir. Karşı tarafa
gönderilen her şey onların ortamında saklanır ve ortak 3B haritada yayınlanır.
Kurum verisi ise Faz 4'ten önce onay.

---

## Faz 4 — Yayınlama

**Bağımlılık:** Faz 3 (auth), Faz 1–2 (gönderilecek içerik).

| # | İş | Not |
|---|---|---|
| N21 | `GET /api/v2/export/geojson?tenant=&bbox=&type=` | TwinInstance + geo triple → `Point` feature; `properties` içinde `thing_id`, `interface`, `dtdl-interface` ve **TD linki** |
| N22 | `POST /api/v2/integrations/{provider}/register-layer` | Karşı tarafın katman kaydı ucu (NETCAD: `/partner/layers`) |
| N23 | `POST /api/v2/integrations/{provider}/push` | Karşı tarafın ingest ucu (NETCAD: `/ingest`, gövde `{ source, twins, features, events }`) |
| N24 | Tetikleme: önce manuel uç, sonra create/update sonrası event-driven | Cron değil |

Yayınlama uçları da sağlayıcı-agnostik: GeoJSON/TD üretimi ortak, gövde biçimi
adaptörde.

---

## Faz 5 — Sürekli senkron (opsiyonel)

**Bağımlılık:** Faz 1–4 + backlog A1 (versiyonlama), A2 (TTL).

- Periyodik yenileme; dış envanter değişince graf da güncellenir
- Süresi dolan olay twin'lerinin listelerden düşmesi — A2 doğrudan karşılıyor
- Federasyon: karşı tarafı ayrı bir dizin düğümü görmek — İP2 Ekim dilimi
  (O3 `ts:TwinRegistry`, K1–K2 düğümler arası ilişki) ile aynı problem
