# Haziran 2026 — Açık Bilgi Modeli temeli + ontoloji dinamikleştirme

**İş paketi:** İP2 — Dağıtık dijital ikiz mimarisi ve Açık Bilgi Modeli
**Dilim teması:** Bilgi modelini kodun dışına çıkar, standart ontolojilere bağla, dışarıya yayınla.
**Durum:** ✅ Tamamlandı — H1–H7, 100 test geçiyor

---

## Hedef

Bugün bilgi modeli üç yerde birden yaşıyor: RDF ontolojisinde, Python sabitlerinde
ve React bileşenlerinde. Bu dilim modeli **tek kaynağa** indirir (ontoloji), onu
**standart vokabülerlere** (SOSA/SSN, QUDT, WGS84) bağlar ve **dışarıdan çekilebilir**
hâle getirir.

Ayrıca modelin hiç RDF'e yazılmayan bir parçası tespit edildi (coğrafi konum) —
bu dilimde giderilir.

Bu dilim **yalnız ekleme** yapar; hiçbir mevcut endpoint imzası değişmez.

---

## Tespit edilen durum

### Bulgu 1 — Coğrafi veri RDF'e hiç ulaşmıyor

`latitude` / `longitude` / `address` form üzerinden alınıyor, YAML annotation'a
yazılıyor, **ama grafa eklenmiyor.**

- Üretim: [twin_generator_service.py:126-131](../../backend/app/services/twin_generator_service.py#L126-L131) — annotation'a yazar
- Tüketim: [twin_rdf_service.py:1104-1125](../../backend/app/services/twin_rdf_service.py#L1104-L1125) — `manufacturer`, `model`, `serialNumber`, `firmwareVersion`, `dtdl-*` okunur; koordinat **okunmaz**

Sonuç: harita arayüzü çalışıyor ama coğrafi SPARQL keşfi imkânsız. Temmuz dilimi
buna bağımlı.

### Bulgu 2 — İlişki vokabüleri 6 yerde tekrarlanıyor

`feeds` / `controls` / `contains` / `monitors` / `dependsOn` ve inverse'leri:

| Yer | Ne tutuyor |
|---|---|
| [twin_ontology.py:207-232](../../backend/app/core/twin_ontology.py#L207-L232) | `owl:inverseOf` + `propagationDirection` — **doğru kaynak bu olmalı** |
| [twin_rdf_service.py:35-47](../../backend/app/services/twin_rdf_service.py#L35-L47) | `INVERSE_TYPE_MAP` — Python kopyası |
| [CreateTwinThing.jsx:933-950](../../frontend/src/pages/twin/CreateTwinThing.jsx#L933-L950) | dropdown seçenekleri |
| [TwinGraphView.jsx:36-44](../../frontend/src/pages/twin/TwinGraphView.jsx#L36-L44) | renk eşlemesi + inverse listesi |
| [TwinThingDetails.jsx:13-21](../../frontend/src/pages/twin/TwinThingDetails.jsx#L13-L21) | badge renkleri |
| [domainOntologyService.js:128](../../frontend/src/services/domainOntologyService.js#L128) | ayrı bir tanım daha |

Yeni bir ilişki tipi eklemek bugün **6 dosya** düzenlemeyi gerektiriyor.
Bu dilimin sonunda **1 dosya** olacak.

### Bulgu 3 — Ontoloji izole

`ts:TwinInterface` hiçbir standart sınıfa bağlı değil. Dışarıdan gelen bir sistem
için model anlamsız. "Açık Bilgi Modeli" başlığının karşılığı yok.

### Bulgu 4 — SPARQL guard atlatılabilir

[twin.py:596-625](../../backend/app/api/v2/twin.py#L596-L625) — SELECT kontrolü ilk
`PREFIX` olmayan satıra bakıyor. Yorum satırı (`#`) ile başlayan sorgu kontrolü
atlatır. Ayrıca `LIMIT` zorunluluğu ve timeout yok.

---

## İş kalemleri

### H1 — Coğrafi triple'ları RDF'e yaz ✅

- [x] `twin_ontology.py`: WGS84 namespace (`http://www.w3.org/2003/01/geo/wgs84_pos#`) bind edildi
- [x] `ts:address` property + `TwinInterface`/`TwinInstance` → `geo:SpatialThing` bağı eklendi
- [x] `add_location_triples()` — konum→RDF eşlemesi için **tek kaynak** helper, `twin_ontology.py` içinde
- [x] `_add_interface_to_graph` ve `_add_instance_to_graph` bu helper'ı çağırıyor
- [x] Generator: konum annotation'ları `_location_annotations()`'a çıkarıldı, **instance YAML'ına da** yazılıyor (önceden yalnız interface'te vardı)
- [x] `debug_dump_service.py` aynı helper'a bağlandı; JSON-LD'deki uydurma `ts:latitude` yerine `geo:lat` kullanılıyor

**Dosyalar:** `backend/app/core/twin_ontology.py`, `backend/app/core/__init__.py`,
`backend/app/services/twin_rdf_service.py`, `backend/app/services/twin_generator_service.py`,
`backend/app/services/debug_dump_service.py`

**Kabul:** ✅ Konumlu bir thing için şu sorgu interface + instance olmak üzere 2 sonuç döner:
```sparql
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
SELECT ?uri ?lat ?lon WHERE { GRAPH ?g { ?uri geo:lat ?lat ; geo:long ?lon } }
```

**Uygulama notları:**

- **Geçersiz değer toleransı:** bozuk (`"abc"`) veya aralık dışı (lat > 90, lon > 180)
  koordinat uyarı loglanıp atlanır; thing'in tamamı kaybedilmez. Değerler
  `Decimal` üzerinden `xsd:decimal` olarak yazılır — float'ın bilimsel gösterime
  kaçma riski yok.
- **`geo:` prefix çakışması:** rdflib 7 `geo:` prefix'ini GeoSPARQL'a
  (`http://www.opengis.net/ont/geosparql#`) önceden bağlıyor. `bind(..., replace=True)`
  kullanılmazsa serileştirmede `geo1:` çıkıyor. Üç yerde de `replace=True` verildi.
  GeoSPARQL ileride eklenirse (Ekim backlog) ayrı bir prefix seçilmeli.
- **Kopya RDF üretimi:** `debug_dump_service.py`, `TwinRDFService`'in triple üretimini
  elle kopyalıyor ve zamanla ayrışmış (JSON-LD'de ontolojide hiç var olmayan
  `ts:latitude` kullanıyordu). Konum için ortak helper'a bağlandı; **geri kalan
  kopya mantık duruyor** — ayrı bir temizlik işi olarak backlog'a alınmalı.

---

### H2 — SOSA/SSN + QUDT alignment ✅

- [x] SOSA, SSN, QUDT, schema.org namespace'leri tanımlandı ve bind edildi
- [x] `owl:Ontology` başlığı + `owl:versionInfo "2.0.0"` + `rdfs:seeAlso` ile kaynak vokabülerler
- [x] Tüm `ts:` sınıfları `owl:Class` olarak da tiplendi (OWL araçları görsün)
- [x] Sınıf ve property eşlemeleri (aşağıdaki matris)
- [x] `owl:inverseOf` düzeltmesi — OWL 2 punning
- [x] Ontolojinin Fuseki'ye yüklenmesi idempotent hale getirildi

**Dosyalar:** `backend/app/core/twin_ontology.py`, `backend/app/core/__init__.py`,
`backend/main.py`, `backend/scripts/setup_twin_fuseki.py`

**Kabul:** ✅ Her `ts:` üst sınıfın en az bir dış vokabüler bağı var; ontoloji
Turtle / JSON-LD / RDF-XML / N-Triples olarak sorunsuz serileşiyor (218 triple).

#### Eşleme matrisi

| ts: terimi | Bağ | Hedef | Not |
|---|---|---|---|
| `ts:TwinInterface` | `rdfs:subClassOf` | `ssn:System` | |
| `ts:TwinInterface` | `rdfs:subClassOf` | `geo:SpatialThing` | H1'den |
| `ts:TwinInstance` | `rdfs:subClassOf` | `ssn:System`, `geo:SpatialThing` | |
| `ts:Property` | `rdfs:subClassOf` | `ssn:Property` | |
| `ts:hasProperty` | `rdfs:subPropertyOf` | `ssn:hasProperty` | birebir karşılık |
| `ts:Command` | `rdfs:subClassOf` | `sosa:Procedure` | |
| `ts:hasCommand` | `rdfs:subPropertyOf` | `ssn:implements` | |
| `ts:name` | `rdfs:subPropertyOf` | `rdfs:label` | |
| `ts:description` | `rdfs:subPropertyOf` | `rdfs:comment` | |
| `ts:model` | `rdfs:subPropertyOf` | `schema:model` | range Text, uyumlu |
| `ts:serialNumber` | `rdfs:subPropertyOf` | `schema:serialNumber` | range Text, uyumlu |
| `ts:firmwareVersion` | `rdfs:subPropertyOf` | `schema:softwareVersion` | range Text, uyumlu |
| `ts:manufacturer` | `rdfs:seeAlso` | `schema:manufacturer` | ⚠ subPropertyOf **değil** |
| `ts:unit` | `rdfs:seeAlso` | `qudt:Unit` | ⚠ subPropertyOf **değil** |
| `ts:address` | — | — | Basic Geo'da karşılığı yok |

#### Plandan sapmalar ve gerekçeleri

Planlanan üç eşleme, incelemede **semantik olarak yanlış** bulundu ve değiştirildi.
Doğrulanamayan bir eşleme koymak, hiç koymamaktan kötüdür — dışarıdan gelen bir
reasoner yanlış çıkarım üretir.

| Planlanan | Uygulanan | Neden |
|---|---|---|
| `TwinInterface → sosa:Platform` | `→ ssn:System` | `sosa:Platform` özellikle *barındıran* varlık demek. Buradaki twin'ler sensör, aktüatör, gateway veya bileşik sistem olabiliyor; `ssn:System` hepsini kapsar |
| `TwinInstance → sosa:FeatureOfInterest` | `→ ssn:System` | FeatureOfInterest "özelliği ölçülen şey" demek. Bir sensör twin'i için bu yanlış; blanket iddia olarak verilemez |
| `ts:Property → sosa:ObservableProperty` | `→ ssn:Property` | `ts:Property` `ts:writable` bayrağı taşıyor, yani aktüe edilebilir de olabilir. `ssn:Property`, `ObservableProperty` ve `ActuatableProperty`'nin ortak üst sınıfı |
| `ts:Command → sosa:Actuation` | `→ sosa:Procedure` | `sosa:Actuation` gerçekleşmiş bir *olay*; `ts:Command` ise çağrılabilir bir işlemin *tanımı* — bu bir Procedure |
| `ts:unit rdfs:subPropertyOf qudt:unit` | `rdfs:seeAlso qudt:Unit` | `qudt:unit`'in range'i `qudt:Unit` **kaynağı**; bizim değerimiz `"Cel"` gibi bir **metin sembolü**. subPropertyOf demek, string'in bir qudt:Unit olduğunu iddia etmek olurdu |
| — (planda yoktu) | `ts:manufacturer rdfs:seeAlso schema:manufacturer` | `schema:manufacturer` bir `Organization` kaynağı bekliyor; bizde üretici adı metin |

#### Ek düzeltme — `owl:inverseOf` birey üzerinde kullanılıyordu

`ts:feeds` gibi ilişki tipleri iki farklı rolde kullanılıyor: reified relationship
node'unun `ts:relationshipType` değeri olarak (**birey**) ve `owl:inverseOf` çiftinin
tarafı olarak (**property**). `owl:inverseOf` yalnız property'ler için anlamlıdır —
birey üzerinde hiçbir şey ifade etmiyordu.

Çözüm: OWL 2 **punning**. Her tip hem `ts:RelationshipType` bireyi hem
`owl:ObjectProperty` olarak tiplendi. OWL 2 birey/property punning'ine izin verir,
mevcut veri modeli hiç değişmez, `owl:inverseOf` artık gerçek bir anlam taşır.

#### Ek düzeltme — ontoloji Fuseki'ye ulaşmıyordu

[main.py](../../backend/main.py) ontolojiyi **yalnız dataset ilk kez yaratılırken**
default grafa POST ediyordu. Mevcut bir kurulumda ontoloji değişikliği store'a
hiç yansımıyordu — H1/H2'nin eklediği triple'lar da yansımayacaktı.

Değişiklik: ontoloji artık her açılışta kendi named graph'ına
(`http://twin.dtd/ontology`) **PUT** ediliyor. PUT yalnız o grafı değiştirir;
thing verisi `http://twin.io/graphs/...` altında, dokunulmuyor. Tenant filtresi
(`_build_tenant_graph_filter`) `http://twin.io/graphs/{tenant}/` ön ekiyle
çalıştığı için ontoloji grafı hiçbir thing listesine sızmaz.
`scripts/setup_twin_fuseki.py` de aynı şekilde PUT'a çevrildi (tekrarlı çalıştırmada
triple birikmiyor).

> ⚠ **Mevcut kurulum notu:** Eski sürümle yaratılmış bir dataset'te ontolojinin
> eski kopyası default grafta kalır. Zararsızdır (tenant filtreli sorgulara
> karışmaz), ama tam temizlik isteniyorsa `DROP DEFAULT` ile silinebilir —
> thing verisi named graph'larda olduğu için etkilenmez.

---

### H3 — Ontolojiyi dışarıya yayınla ✅

- [x] Yeni router `backend/app/api/v2/ontology.py`
- [x] `GET /api/v2/ontology` — q-değeri farkında content negotiation: `text/turtle` (varsayılan), `application/ld+json`, `application/rdf+xml`, `application/n-triples` + yaygın takma adlar
- [x] `Accept` yok veya `*/*` → Turtle; yalnız desteklenmeyen tip istenirse **406**
- [x] `?format=ttl|jsonld|xml|nt` ile başlık override (tarayıcı/curl kolaylığı); bilinmeyen değer **400**
- [x] `ETag` (ontoloji sürümü), `Cache-Control`, `Vary: Accept`, `X-Ontology-Version` başlıkları
- [x] `GET /api/v2/ontology/classes` ve `/properties` — CURIE'li JSON özet, dış alignment'lar ayrı alanda
- [x] `app/api/__init__.py`'a router kaydı

**Kabul:** ✅ Dört formatın **dördü de** rdflib ile parse edildi, hepsi 218 triple döndürdü.

**Doğrulanan davranışlar:**

| İstek | Sonuç |
|---|---|
| `Accept` yok | `text/turtle`, 218 triple |
| `Accept: application/ld+json` | `application/ld+json`, 218 triple |
| `Accept: text/html;q=0.9, application/ld+json;q=1.0` | JSON-LD (q-değeri doğru sıralandı) |
| `Accept: text/html;q=1.0, text/turtle;q=0.5` | Turtle (yüksek q desteklenmiyorsa bir sonrakine düşüyor) |
| `Accept: text/html` | **406** |
| `?format=bogus` | **400** |
| `/classes` | 8 sınıf; 4'ünün dış bağı var |
| `/properties` | 36 property; 7'sinin dış bağı var |

**Uygulama notu:** `/properties` yalnız `rdf:Property` tipli terimleri döner.
`ts:feeds` ve kardeşleri H2'de punning ile `owl:ObjectProperty` olarak da tiplendi;
bunlar yapısal property değil, ilişki tipi vokabüleridir ve H4'teki
`/relationship-types` ucundan servis edilir. Sızmadıkları test edildi.

---

### H4 — Vokabüleri tek kaynağa indir (backend) ✅

- [x] `RELATIONSHIP_TYPES` tablosu — vokabülerin **tek tanım yeri**, `twin_ontology.py` içinde
- [x] Ontoloji grafı bu tablodan üretiliyor: `owl:inverseOf`, `ts:propagationDirection`, `ts:onTargetDeleted`, `rdfs:label`, `rdfs:comment`, `ts:uiColor`, `ts:isDerived`
- [x] `get_relationship_types()` / `get_inverse_type_map()` — vokabüleri **graftan geri okur**
- [x] `INVERSE_TYPE_MAP` artık türetiliyor; elle yazılmış 10 satırlık dict silindi
- [x] `get_inverse_type()` imzası korundu — çağıran hiçbir kod değişmedi
- [x] `get_cached_ontology()` — paylaşılan salt-okunur graf, her çağrıda yeniden inşa yok
- [x] `GET /api/v2/ontology/relationship-types` (+ `?include_derived=false`)

**Dosyalar:** `backend/app/core/twin_ontology.py`, `backend/app/core/__init__.py`,
`backend/app/services/twin_rdf_service.py`, `backend/app/api/v2/ontology.py`

**Kabul:** ✅ `twin_rdf_service.py` içinde elle yazılmış ilişki tipi adı **kalmadı**
(regex ile doğrulandı). Teste ontolojiye çalışma anında `calibrates`/`isCalibratedBy`
çifti eklendi: tip sayısı 10 → 12 oldu ve inverse map yeni çifti tanıdı — **hiçbir
Python kodu değişmeden**.

#### Plandan sapma

| Planlanan | Uygulanan | Neden |
|---|---|---|
| `ts:uiLabel` özel property | `rdfs:label` | Etiket için zaten standart bir property var; ontolojiye eşdeğer ikinci bir terim eklemek modeli kirletir |
| — (planda yoktu) | `ts:isDerived` | Frontend'in create formunda yalnız kullanıcının ileri sürebileceği 5 tipi göstermesi gerekiyor. Bunu `owl:inverseOf`'tan çıkarmak mümkün değil (çift yönlü); ayrı bir bayrak şart |
| — (planda yoktu) | Her tipe `rdfs:comment` | i18n anahtarı olmayan yeni bir tip eklendiğinde frontend'in gösterecek bir açıklaması olsun diye (fallback) |

#### Bulgu — iki frontend paleti birbiriyle çelişiyordu

Aynı ilişki tipi iki ekranda farklı renkteydi:

| Tip | [TwinGraphView.jsx](../../frontend/src/pages/twin/TwinGraphView.jsx#L35-L41) | [TwinThingDetails.jsx](../../frontend/src/pages/twin/TwinThingDetails.jsx#L12-L23) |
|---|---|---|
| `feeds` | amber `#f59e0b` | yeşil |
| `controls` | kırmızı `#ef4444` | turuncu |
| `contains` | mor `#8b5cf6` | mavi |
| `dependsOn` | indigo `#6366f1` | kırmızı |
| `monitors` | yeşil `#10b981` | yeşil |

Detay sayfası ayrıca `feeds` ve `monitors`'a aynı yeşili veriyordu — iki farklı
semantik görsel olarak ayırt edilemiyordu. Graph görünümünün paleti kanonik kabul
edildi (her tip ayrı bir renk) ve `ts:uiColor` olarak ontolojiye taşındı. Inverse
tipler, ileri karşılıklarıyla aynı rengi alır — aynı ilişkinin diğer yönden
görünümüdür.

---

### H5 — Frontend'i ontolojiden besle ✅

- [x] `frontend/src/services/ontologyService.js` — ontoloji API istemcisi (RDF + JSON uçları)
- [x] `frontend/src/store/useOntologyStore.js` — vokabüleri çeker, önbellekler, seçici (selector) sunar
- [x] `CreateTwinThing.jsx` — dropdown store'dan doluyor, her seçeneğin yanında `ts:uiColor` noktası
- [x] `TwinGraphView.jsx` — `REL_COLORS` ve `INVERSE_TYPES` sabitleri silindi, `buildRelIndex()` ontolojiden türetiyor
- [x] `TwinThingDetails.jsx` — `REL_TYPE_COLORS` sabiti silindi, badge `getTypeBadgeStyle()` kullanıyor
- [x] `domainOntologyService.js` — çakışan üçüncü sözlük kaldırıldı
- [x] Ağ hatasında `FALLBACK_TYPES` devreye giriyor, `usingFallback` bayrağı ile işaretleniyor
- [x] `vite build` temiz geçiyor

**Kabul:** ✅ Üç sayfada da elle yazılmış ilişki tipi adı kalmadı. Tek istisna
`CreateTwinThing.jsx`'teki `selectableTypes[0]?.name || 'feeds'` — store yüklenmeden
önceki ilk render için son çare varsayılan.

#### Ek düzeltme — animasyon kuralı da hardcoded'dı

`TwinGraphView` kenarları `e.relType === 'feeds' || e.relType === 'monitors'`
koşuluyla animasyonluyordu. Bu ikisi tam olarak `propagation_direction ===
"source-to-target"` olan tiplerdir; kural artık ontolojiden türetiliyor. Görünüm
aynı kaldı ama yeni bir "source-to-target" tipi eklendiğinde otomatik doğru
davranıyor.

#### Bulgu — `domainOntologyService.js` ölü kod

Dosya frontend'in **hiçbir yerinden import edilmiyor**. İçinde ilişki tipleri için
üçüncü bir sözlük vardı: adlar ontolojiyle uyuşmuyordu (`containedIn` ↔ gerçek
`isContainedIn`, `controlledBy` ↔ `isControlledBy`) ve dördüncü bir renk şeması
taşıyordu. Çakışan bölüm (sözlük + `getRelationshipConfig` + `listRelationshipTypes`)
kaldırıldı, yerine yönlendirme notu bırakıldı. Dosyanın tamamının silinmesi ayrı
bir karar — backlog'a alındı.

#### Bulgu — `docs/` klasörü git'te takip edilmiyordu

`.gitignore` `docs/` klasörünün tamamını dışlıyordu; **0 doküman versiyonlanıyordu**
(mevcut `DTDL_INTEGRATION.md`, `NAMED_GRAPHS.md`, `adr/` dahil hepsi yalnız yereldeydi).
Ar-Ge çıktısı olacak İP2 dokümanları bu haliyle repoda yer almazdı.

Kural `docs/*` + `!docs/ip2/` olarak değiştirildi — yalnız İP2 klasörü versiyonlanıyor,
geri kalan docs içeriği eskisi gibi yerelde kalıyor. (`docs/` şeklindeki dizin dışlaması
alt klasör geri alınmasına izin vermez; bu yüzden `docs/*` biçimi gerekti.)

---

### H6 — SPARQL guard sertleştirme ✅

- [x] Yeni `backend/app/core/sparql_guard.py` — yorum farkında tarayıcı
- [x] Sorgu formu **varsayılan-red** ile belirleniyor: yalnız `SELECT`/`ASK`/`CONSTRUCT`/`DESCRIBE` geçer
- [x] `LIMIT` yoksa ekleniyor, varsa `SPARQL_MAX_LIMIT` tavanına kırpılıyor
- [x] Alt sorgudaki `LIMIT`e dokunulmuyor; `ASK`'a `LIMIT` eklenmiyor
- [x] `_execute_query`'ye `aiohttp.ClientTimeout` (`SPARQL_TIMEOUT_SECONDS`, varsayılan 30 sn)
- [x] Reddedilen sorgu için hangi formun neden reddedildiğini söyleyen 400 mesajı
- [x] `geo:` prefix'i otomatik enjeksiyon listesine eklendi (H1'in triple'ları sorgulanabilsin)

**Dosyalar:** `backend/app/core/sparql_guard.py` (yeni), `backend/app/core/config.py`,
`backend/app/api/v2/twin.py`, `backend/app/api/v2/fuseki.py`,
`backend/app/services/twin_rdf_service.py`

**Kabul:** ✅ `# yorum\nDROP ALL` reddediliyor; `LIMIT`siz SELECT otomatik sınırlanıyor.

#### Açığın kanıtı

Eski kontrol, PREFIX olmayan **ilk satıra** bakıp `SELECT` ile başlıyor mu diye
soruyordu. Önüne bir yorum satırı konan her şey kontrolü atlıyordu:

| Gövde | Eski davranış | Yeni davranış |
|---|---|---|
| `# zararsız yorum\nDROP ALL` | geçiyordu | **400** |
| `# yorum\nDELETE WHERE {...}` | geçiyordu | **400** |
| `\n\n # yorum\n INSERT DATA {...}` | geçiyordu | **400** |

> Not: Fuseki'nin query endpoint'i zaten UPDATE çalıştırmaz, dolayısıyla bu bir
> uzaktan veri silme açığı değildi. Ama guard hiçbir şey yakalamıyordu ve
> `LIMIT` tavanı da yoktu — asıl risk buradaydı.

#### Kapsam genişletmesi

Aynı zayıf kontrolün **üç kopyası** vardı: `twin.py` içinde satır içi, `fuseki.py`
içinde `_validate_select_query()` olarak, iki uçta birden kullanılıyordu. Üçü de
ortak guard'a bağlandı — açık artık tek yerde kapanıyor.

Etkilenen uçlar: `POST /v2/twin/rdf/query`, `POST /v2/fuseki/sparql`,
`POST /v2/fuseki/sparql/search`

#### Yorum ayıklamada dikkat edilenler

`#` her yerde yorum değil. Tarayıcı şunları ayırt ediyor (hepsi test edildi):

| Girdi | Beklenen |
|---|---|
| `<http://twin.dtd/ontology#name>` | IRI içindeki `#` korunur |
| `"renk #ff0000"` | string literal içindeki `#` korunur |
| `"""çok\nsatırlı # diyez"""` | üç tırnaklı literal içindeki `#` korunur |
| `FILTER(?o < 90) # yorum` | `<` küçüktür operatörü IRI sanılmaz, yorum silinir |

`<` karakteri için SPARQL **IRIREF** grameri (`<[^<>"{}|^\`\\\s]*>`) kullanıldı;
naif "`<`'ten `>`'e kadar IRI'dir" yaklaşımı `FILTER(?a < 5)` gibi ifadelerde
yanlış çalışıyordu.

---

### H7 — Regresyon testleri ✅

- [x] `backend/tests/conftest.py` — `sys.path` kurulumu + paylaşılan ontoloji fixture'ı
- [x] `backend/pytest.ini` — testpaths, `--strict-markers`, üçüncü parti uyarı filtreleri
- [x] `backend/tests/test_geo_triples.py` — H1 (7 test)
- [x] `backend/tests/test_ontology_alignment.py` — H2 + H4 (28 test)
- [x] `backend/tests/test_ontology_endpoint.py` — H3 + H4 endpoint'i (28 test)
- [x] `backend/tests/test_sparql_guard.py` — H6 (37 test)

**Kabul:** ✅ `pytest` → **100 passed**. `main.py` import ediliyor (52 rota),
`vite build` temiz geçiyor.

#### Bulgu — mevcut "testler" pytest testi değildi

`backend/tests/` altındaki dört dosya (`test_dtdl_loader.py`,
`test_dtdl_converter.py`, `test_dtdl_validator.py`, `test_seismic_dtdl.py`)
`main()` fonksiyonu içeren ve `print` ile çıktı veren demo script'leridir.
`pytest tests/` çalıştırıldığında **"no tests ran"** diyordu — yani projede
çalışan hiçbir otomatik test yoktu. Bu dosyalara dokunulmadı; yanlarına gerçek
pytest testleri eklendi. Script'lerin pytest'e çevrilmesi backlog'a alındı.

#### Test kapsamı

| Dosya | Neyi koruyor |
|---|---|
| `test_geo_triples.py` | Kabul sorgusu 2 subject döner; koordinatlar `xsd:decimal`; bozuk/aralık dışı değer thing'i düşürmez (7 vaka); debug dump ile store birebir aynı; uydurma `ts:latitude` geri gelmez |
| `test_ontology_alignment.py` | 13 alignment iddiası; **type-uyumsuz iki bağın `subPropertyOf` olarak iddia edilmediği**; her üst sınıfın dış bağı; 4 formatta round-trip; punning; `INVERSE_TYPE_MAP` türetimi; ontolojiye tip eklemenin yettiği; servise elle liste geri sızmadığı |
| `test_ontology_endpoint.py` | 8 content negotiation vakası; 4 serileştirmenin aynı triple sayısını verdiği; 406/400; cache başlıkları; `/classes` alignment'ları; ilişki tiplerinin `/properties`'e sızmadığı |
| `test_sparql_guard.py` | Yorum ile atlatma (3 vaka); 7 update formu; LIMIT ekleme/kırpma/alt sorgu/ASK; `#`'in IRI, tek/çift/üç tırnaklı literal ve `<` operatörü yanında doğru yorumlanması |

Testler yalnız "çalışıyor mu"yu değil, **alınan kararları** koruyor: örneğin
`test_type_incompatible_links_stay_unasserted`, birinin ileride `ts:unit`'e
`rdfs:subPropertyOf qudt:unit` eklemesini engeller.

#### Ek düzeltme — `datetime.utcnow()`

Yeni testler kendi kodumuzdan gelen bir uyarıyı görünür kıldı: 4 yerde
`datetime.utcnow()` kullanılıyordu (Python 3.12+'da kaldırılmak üzere işaretli).

Bu yalnız bir uyarı değil, üretilen RDF'te bir doğruluk hatasıydı:
`generated-at` `xsd:dateTime` olarak saklanıyor ve `utcnow().isoformat()`
saat dilimi eki **olmayan** bir dizge üretiyordu — XSD semantiğinde bu
"saat dilimi belirtilmemiş" demek, oysa değer UTC'ydi.

`datetime.now(timezone.utc).isoformat()` ile değiştirildi:
`2026-07-28T10:18:36.333687+00:00`. Eski kayıtlar geçerli kalır, ikisi de
`xsd:dateTime` olarak ayrıştırılır.

**Dosyalar:** `backend/app/services/twin_generator_service.py`,
`backend/app/services/dtdl_converter_service.py`

---

## Kabul kriterleri (dilim geneli)

| # | Kriter | Durum |
|---|---|---|
| 1 | `docker compose up -d --build` temiz kalkıyor, health check yeşil | ⏳ Ortamda doğrulanacak |
| 2 | `pytest` geçiyor | ✅ 100 passed |
| 3 | Mevcut endpoint imzalarında kırılma yok | ✅ Yalnız ekleme; `main.py` 52 rota ile import ediliyor |
| 4 | Yeni ilişki tipi yalnız `twin_ontology.py` düzenlemesi gerektiriyor | ✅ Testle doğrulandı |
| 5 | Konum bilgisi RDF'te sorgulanabilir (Temmuz T3'ün ön koşulu) | ✅ Kabul sorgusu sonuç dönüyor |
| 6 | `vite build` temiz | ✅ |

> Kriter 1 kod tarafında hazır; `docker compose` çalıştırması bu ortamda
> yapılmadı. Ontoloji artık her açılışta PUT edildiği için ilk kalkışta
> `Twin ontology v2.0.0 loaded (... triples)` logu beklenir.

---

## Riskler

| Risk | Etki | Önlem |
|---|---|---|
| `INVERSE_TYPE_MAP` türetimi modül yükleme sırasında ontoloji grafını inşa eder | Import maliyeti | Modül seviyesinde bir kez, önbelleklenir |
| Frontend ontoloji endpoint'ine bağımlı hâle gelir | Backend down → UI bozulur | Mevcut sabit listeler fallback olarak korunur |
| SOSA/SSN alignment mevcut sorguları etkiler | Regresyon | Alignment yalnız ontoloji grafında; veri grafları değişmez |

---

## Çıktılar

- [x] **Ontoloji eşleme matrisi** — H2 bölümünde; 13 asserted alignment + 2 gerekçeli `seeAlso`
- [x] **Yayınlanan model** — `GET /api/v2/ontology`, dört serileştirme, 218 triple
- [x] **Dinamiklik ölçümü** — aşağıdaki tablo
- [x] **Test raporu** — 100 pytest testi, dört dosya
- [x] **Tespit edilen ve giderilen 8 hata** — aşağıdaki tablo

### Dinamiklik ölçümü — yeni ilişki tipi eklemenin maliyeti

| | Öncesi | Sonrası |
|---|---|---|
| Düzenlenen dosya | **6** | **1** (`twin_ontology.py`) |
| Düzenlenen katman | ontoloji + Python + 4 React dosyası | yalnız ontoloji |
| Frontend derlemesi gerekir mi | evet | hayır |
| Testle korunuyor mu | hayır | evet (`test_adding_a_type_to_the_ontology_is_enough`) |

Öncesi 6 yer: `twin_ontology.py`, `twin_rdf_service.py` (`INVERSE_TYPE_MAP`),
`CreateTwinThing.jsx`, `TwinGraphView.jsx`, `TwinThingDetails.jsx`,
`domainOntologyService.js`.

### Dilim boyunca tespit edilip giderilen hatalar

| # | Hata | Nasıl bulundu |
|---|---|---|
| 1 | Konum verisi RDF'e hiç yazılmıyordu; coğrafi sorgu imkânsızdı | H1 kod incelemesi |
| 2 | Konum yalnız interface YAML'ındaydı, instance konumsuzdu | H1 |
| 3 | Debug dump'ın JSON-LD'si ontolojide **olmayan** `ts:latitude` property'sini kullanıyordu | H1 |
| 4 | `owl:inverseOf` birey üzerinde kullanılıyordu — OWL'de hiçbir şey ifade etmiyordu | H2 |
| 5 | Ontoloji Fuseki'ye yalnız dataset ilk yaratıldığında yükleniyordu; güncellemeler hiç ulaşmıyordu | H2 |
| 6 | İki frontend renk paleti çelişiyordu; `feeds`/`monitors` detay sayfasında ayırt edilemiyordu | H4 |
| 7 | SPARQL guard yorum satırıyla atlatılabiliyordu ve `LIMIT` tavanı yoktu (3 uçta birden) | H6 |
| 8 | `datetime.utcnow()` saat dilimsiz `xsd:dateTime` üretiyordu | H7 |

Ayrıca ikisi araç/süreç tarafında: `docs/` klasörü git'te hiç takip edilmiyordu
(0 doküman versiyonlanıyordu) ve `backend/tests/` altındaki dosyalar pytest testi
değil demo script'iydi — projede çalışan otomatik test yoktu.
