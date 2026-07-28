# Temmuz 2026 — Discovery Services & SPARQL tabanlı keşif

**İş paketi:** İP2 — Dağıtık dijital ikiz mimarisi ve Açık Bilgi Modeli
**Dilim teması:** Haziran'da yayınlanan model üstüne keşif katmanı kur.
**Durum:** 🟡 Devam ediyor

---

## Hedef

Sistemde bugün "keşif" diye bir katman yok — yalnız isim üzerinde substring
araması var. Bu dilim, W3C WoT Discovery profiline yaklaşan bir **Thing Description
Directory** davranışı ekler ve iki anlamlı keşif yeteneği getirir:

- **Nerede?** — coğrafi yakınlık keşfi
- **Ne yapabiliyor?** — yetenek (capability) keşfi

Hedef cümle: *"Bu binanın 500 m çevresinde sıcaklık ölçen tüm twin'leri getir"*
tek HTTP çağrısıyla cevaplanır.

---

## Haziran'a bağımlılık

| Temmuz işi | Gerektirdiği Haziran işi | Neden |
|---|---|---|
| T3 — yakınlık keşfi | H1 — geo triple'ları | Koordinat RDF'te yoksa sorgulanacak veri yok |
| T4 — yetenek keşfi | H2 — SOSA/QUDT alignment | Yetenek sorgusu standart sınıflar üzerinden yürür |
| T5 — sorgu kataloğu | H4 — vokabüler ontolojide | Katalog da ontolojide durur, koda gömülmez |

Haziran dilimi tamamlanmadan T3/T4/T5 başlatılmaz.

---

## Tespit edilen durum

### Bulgu 1 — Discovery Services karşılığı yok

Mevcut arama [twin_rdf_service.py:582-655](../../backend/app/services/twin_rdf_service.py#L582-L655):
`CONTAINS(LCASE(STR(?name)))` — isim, açıklama, graph URI ve original ID üzerinde
substring taraması. Coğrafi, semantik veya yetenek bazlı keşif yok.
`/.well-known/wot` self-description yok; sistem kendini tanıtmıyor.

### Bulgu 2 — Arama ölçeklenmiyor

`CONTAINS(LCASE())` her sorguda tam graf taraması yapar. Jena text index (Lucene)
yapılandırılmamış. Thing sayısı arttıkça arama doğrusal yavaşlar.

### Bulgu 3 — Örnek SPARQL sorguları koda gömülü

[SearchThings.jsx:294-302](../../frontend/src/pages/twin/SearchThings.jsx#L294-L302) —
hazır sorgu örnekleri React bileşeninin içinde string olarak duruyor. Yeni sorgu
eklemek frontend derlemesi gerektiriyor.

---

## İş kalemleri

### T1 — Self-description (`/.well-known/wot`)

- [ ] Yeni router `backend/app/api/v2/discovery.py`
- [ ] `GET /.well-known/wot` — Directory'nin kendi Thing Description'ı (JSON-LD)
- [ ] TD içeriği: `@context`, `title`, `security`, keşif endpoint'lerini gösteren `properties`/`actions` formları
- [ ] `main.py`'a kök seviyede kayıt (prefix'siz — spec kök yolu şart koşar)

**Kabul:** `curl localhost:3015/.well-known/wot` geçerli JSON-LD TD döner,
içinde `/api/v2/things` ve `/discovery/*` uçları listelenir.

---

### T2 — TDD uyumlu listeleme

- [ ] `GET /api/v2/things` — JSON-LD dizisi olarak twin listesi
- [ ] Sayfalama: `?limit=` + `Link: <...>; rel="next"` başlığı (W3C TDD profili)
- [ ] `Content-Type: application/ld+json`
- [ ] Tenant filtresi `X-Tenant-ID` üzerinden korunur
- [ ] Mevcut `/rdf/interfaces` bozulmadan kalır (paralel yol)

**Kabul:** Sayfalama zinciri `Link` başlığı takip edilerek sonuna kadar gezilebiliyor.

---

### T3 — Coğrafi yakınlık keşfi

- [ ] `GET /api/v2/discovery/nearby?lat=&lon=&radius_km=&limit=`
- [ ] SPARQL'de bbox ön-filtresi (`FILTER(?lat > … && ?lat < …)`) — indeks dostu
- [ ] Python tarafında haversine ile kesin mesafe + sıralama
- [ ] Yanıtta `distance_km` alanı
- [ ] Koordinatsız thing'ler sessizce elenir

**Dosyalar:** `backend/app/api/v2/discovery.py`, `backend/app/services/twin_rdf_service.py`

**Kabul:** Kadıköy demo verisiyle, bilinen bir noktanın 1 km çevresi doğru
sonuç kümesini ve artan mesafe sıralamasını döner.

---

### T4 — Yetenek (capability) keşfi

- [ ] `GET /api/v2/discovery/by-capability?property=&unit=&thing_type=&dtdl=`
- [ ] Sorgu `ts:hasProperty` → `ts:propertyName` / `ts:unit` üzerinden yürür; H2 sayesinde `sosa:ObservableProperty` ile de eşleşir
- [ ] DTDL bağlaması (`ts:dtdlInterface`) filtre olarak kullanılabilir
- [ ] Birden çok kriter AND ile birleşir
- [ ] `GET /api/v2/discovery/capabilities` — sistemde mevcut property adı + birim envanteri (facet listesi)

**Kabul:** `?property=temperature&unit=Cel` yalnız sıcaklık ölçen twin'leri döner;
facet endpoint'i arayüzün filtre seçeneklerini besler.

---

### T5 — SPARQL keşif profilleri ve sorgu kataloğu

- [ ] `GET /api/v2/discovery/sparql?q=` — TDD SPARQL keşif profili (GET, salt okunur; H6 guard'ı yeniden kullanır)
- [ ] Sorgu kataloğu ontolojide/`queries/` altında dursun: nearby, by-capability, dependency-chain, orphan-things, inactive-relationships
- [ ] `GET /api/v2/discovery/queries` — katalog listesi (ad, açıklama, parametreler, sorgu metni)
- [ ] `SearchThings.jsx` gömülü örnekleri bu endpoint'ten alsın

**Kabul:** Yeni bir hazır sorgu eklemek frontend derlemesi gerektirmiyor.

---

### T6 — Jena text index (Lucene)

- [ ] `fuseki/assembler.ttl` — TDB2 + `text:TextDataset` yapılandırması
- [ ] İndekslenen alanlar: `ts:name`, `ts:description`, `ts:originalId`, `ts:propertyName`
- [ ] `docker-compose.yml`: assembler'ı mount et, Fuseki'yi bu yapılandırmayla başlat
- [ ] `search()` metodunu `text:query` kullanacak şekilde güncelle, `CONTAINS` fallback olarak kalsın
- [ ] Mevcut veri için yeniden indeksleme notu (`docs/ip2/` altında)

**Kabul:** Arama sonuçları eşdeğer; sorgu süresi mevcut demo veri setinde ölçülüp
öncesi/sonrası kaydedildi.

**Risk:** Fuseki başlangıç yapılandırması değişiyor — bu dilimin en kırılgan işi.
Volume ve yeniden indeksleme adımı önceden denenmeli.

---

### T7 — Keşif arayüzü

- [ ] `SearchThings.jsx`'e sekmeler: **Metin** (mevcut) / **Yakındakiler** / **Yeteneğe göre** / **SPARQL** (mevcut)
- [ ] "Yakındakiler": harita üzerinden nokta seç + yarıçap kaydırıcısı (mevcut `MapComponent.jsx` ve `LocationPicker.jsx` yeniden kullanılır)
- [ ] "Yeteneğe göre": T4 facet endpoint'inden dolan property/birim seçicileri
- [ ] Sonuç kartlarında mesafe rozeti
- [ ] i18n anahtarları (TR/EN)

**Kabul:** Hedef demo cümlesi arayüzden tıklamayla üretilebiliyor.

---

### T8 — Testler

- [ ] `backend/tests/test_discovery_geo.py` — haversine doğruluğu, bbox sınır durumları, koordinatsız thing eleme
- [ ] `backend/tests/test_discovery_capability.py` — çoklu kriter, facet envanteri
- [ ] `backend/tests/test_tdd_conformance.py` — `/.well-known/wot` JSON-LD geçerliliği, `Link` sayfalama zinciri
- [ ] `backend/tests/test_discovery_queries.py` — katalog endpoint'i

**Kabul:** `pytest backend/tests/` tamamı geçiyor.

---

## Kabul kriterleri (dilim geneli)

1. `docker compose up -d --build` temiz kalkıyor (Fuseki assembler değişikliği dâhil), health check yeşil
2. `pytest backend/tests/` geçiyor
3. Mevcut `/rdf/*` ve `/fuseki/*` uçları bozulmadan çalışıyor
4. Hedef demo cümlesi tek HTTP çağrısıyla cevaplanıyor
5. W3C WoT Discovery uyum matrisi dokümante edildi (karşılanan / karşılanmayan bölümler)

---

## Riskler

| Risk | Etki | Önlem |
|---|---|---|
| T6 Fuseki yapılandırma değişikliği | Dataset erişilemez hâle gelebilir | Önce yedek al; `CONTAINS` fallback'i kaldırma |
| T3 haversine büyük veri setinde yavaş | Keşif gecikmesi | bbox ön-filtresi zorunlu; `limit` varsayılanı düşük tut |
| Haziran H1/H2 gecikirse T3/T4 bloke | Dilim kayması | Bağımlılık tablosu takip edilir; T1/T2/T6 bağımsız, önden yapılabilir |
| `/.well-known/` kök yolu router prefix'iyle çakışır | 404 | `main.py`'da prefix'siz kayıt, ayrı test |

---

## Çıktılar

> Dilim tamamlandığında doldurulur.

- [ ] W3C WoT Discovery uyum matrisi
- [ ] Keşif API referansı (örnek istek/yanıtlar)
- [ ] Arama başarım ölçümü: Lucene öncesi/sonrası
- [ ] Demo senaryosu: yakınlık + yetenek keşfi ekran akışı
- [ ] Test raporu
