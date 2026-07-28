# İP2 — Ağustos ve sonrası backlog

> Planlanmış, henüz başlanmamış dilimler. Sıra bağlayıcı değil; her ay başında
> önceki ayın çıktısına göre gözden geçirilir.

---

## Ağustos 2026 — Description Repository olgunluğu

**Tema:** Twin tanımı artık bir "kayıt" — sürümü, geçerlilik süresi ve yaşam
döngüsü olan bir varlık.

| # | İş | Not |
|---|---|---|
| A1 | **Versiyonlama** — `ts:version` + eski grafı `http://twin.io/graphs/{tenant}/{thing}/v{n}` altına arşivle | CLAUDE.md'deki "aynı thing_id ile iki kez create etme, önceki grafı override eder" kısıtını ortadan kaldırır |
| A2 | **TD registration lifecycle** — `ts:registeredAt`, `ts:ttl`, `ts:expiresAt`; süresi dolmuş kayıtlar listelerden düşer | W3C WoT Discovery §7.3 |
| A3 | **Per-thing content negotiation** — `GET /rdf/interfaces/{name}` için `Accept: text/turtle \| application/ld+json \| application/n-triples` | Haziran H3'teki ontoloji negotiation'ının aynısı, thing seviyesinde |
| A4 | **Değişiklik geçmişi** — `GET /rdf/interfaces/{name}/history`, sürümler arası diff | A1'e bağımlı |

---

## Eylül 2026 — SHACL doğrulama

**Tema:** Model uyumu makine tarafından denetlenir; "açık bilgi modeli" iddiası
doğrulanabilir hâle gelir.

| # | İş | Not |
|---|---|---|
| E1 | `shapes/twin-shapes.ttl` — TwinInterface/Property/Relationship için SHACL shape'leri | Haziran H2'deki SOSA/QUDT alignment üstüne oturur |
| E2 | `pyshacl` entegrasyonu + `POST /api/v2/twin/validate/shacl` | |
| E3 | Create akışında opsiyonel SHACL kapısı (`?validate=strict`) | Varsayılan kapalı; geriye dönük uyum |
| E4 | Frontend'de doğrulama raporu paneli | Mevcut `DTDLValidationPanel.jsx` deseni |

---

## Ekim 2026 — Dağıtık mimari PoC

**Tema:** Tek düğümden çok düğüme. İlk kez gerçek "dağıtık" iddia edilir.

| # | İş | Not |
|---|---|---|
| O1 | Compose'a ikinci düğüm (`fuseki-edge`) + ayrı dataset | |
| O2 | Federated SPARQL — `SERVICE <http://fuseki-edge:3030/...>` ile düğümler arası sorgu | |
| O3 | `ts:TwinRegistry` — her düğüm kendi dizinini duyurur; `GET /discovery/directories` | Temmuz T1'deki self-description'ın çok düğümlü hâli |
| O4 | `docs/ip2/distributed-architecture.md` + sequence diagram | Ar-Ge raporu çıktısı |

**Risk notu:** Bu dilim PoC seviyesindedir. Üretim garantisi verilmez.

---

## Kasım 2026 — Düğümler arası ilişki

**Tema:** Bir düğümdeki twin, başka düğümdeki twin'e ilişki kurabilir.

| # | İş | Not |
|---|---|---|
| K1 | `ts:targetInterface` uzak düğüm URI'si kabul etsin | |
| K2 | `_insert_inverse_relationships` uzak SPARQL endpoint'ine INSERT | En riskli parça |
| K3 | Eventual consistency — retry kuyruğu, başarısız propagasyonun `ts:Degraded` işaretlenmesi | Mevcut RelationshipStatus vokabüleri zaten uygun |
| K4 | Düğüm sağlık takibi + kısmi sonuç dönen federated sorgu | |

---

## Sıraya alınmamış fikirler

- **Seviye 3 — WebSocket event sistemi.** Relationship Seviye 2 planında tanımlıydı, hiç başlanmadı. Twin durum değişikliklerinin canlı yayını.
- **GeoSPARQL tam desteği.** Haziran H1 Basic Geo (WGS84) ile yetiniyor; poligon/bölge sorguları için GeoSPARQL + `geof:sfWithin` gerekir.
- **DTDL → RDF tam dönüşüm.** Şu an DTDL bağlaması yalnızca literal (`ts:dtdlInterface "dtmi:..."`). `extends` / `Component` / `Relationship` semantiği RDF'e taşınmıyor.
- **OWL RL reasoning.** Fuseki inference kuralları ile `owl:inverseOf` çıkarımının sorgu anında yapılması — açık inverse triple yazmaya gerek kalmaz.
- **Ontoloji sürüm yönetimi.** `owl:versionInfo` + değişiklik günlüğü.
- **`backend/tests/` altındaki demo script'leri.** `test_dtdl_loader.py`,
  `test_dtdl_converter.py`, `test_dtdl_validator.py`, `test_seismic_dtdl.py` —
  dördü de `main()` içeren, `print` ile çıktı veren script'ler; pytest hiçbirini
  toplamıyor. DTDL katmanı bu yüzden testsiz. Gerçek pytest testlerine çevrilmeli.
- **SQLAlchemy 2.0 geçişi.** `app/core/database.py:25` `declarative_base()`
  çağrısı `MovedIn20Warning` üretiyor; `sqlalchemy.orm.declarative_base` ile
  değiştirilmeli.
- **`frontend/src/services/domainOntologyService.js` ölü kod.** Frontend'in hiçbir
  yerinden import edilmiyor. Haziran H5'te içindeki çakışan ilişki sözlüğü kaldırıldı;
  geriye kalan `DOMAIN_ONTOLOGIES` bölümü de kullanılmıyor. Tamamen silinip
  silinmeyeceğine karar verilmeli.
- **`debug_dump_service.py` kopya RDF mantığı.** Servis, `TwinRDFService`'in triple
  üretimini elle kopyalıyor ve zamanla ayrışıyor (Haziran H1'de JSON-LD'de ontolojide
  hiç tanımlı olmayan `ts:latitude` kullandığı tespit edildi). Konum kısmı ortak
  helper'a bağlandı; property/relationship/command üretimi hâlâ çift. Tamamının
  `TwinRDFService`'ten türetilmesi gerekir.
