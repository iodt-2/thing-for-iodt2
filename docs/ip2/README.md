# İP2 — Dağıtık Dijital İkiz Mimarisi ve Açık Bilgi Modeli

> Ar-Ge iş paketi. Aylık dilimler hâlinde ilerler. Her ay kendi başına çalışan,
> test edilmiş ve dokümante edilmiş bir çıktı bırakır.

**İş paketi tanımı:** Discovery Services, Description Repository, Graph Database,
DTDL tabanlı arayüzler, RDF temsilleri ve SPARQL tabanlı keşif yapısı üzerinde
çalışmalar yürütülmesi.

**Yaklaşım:** Büyük yeniden yazım yok. Her ay mevcut sistemi bozmadan bir katman
ekler; hedef sistemi daha **stabil** (test + doğrulama + guard) ve daha **dinamik**
(model kodun dışında, davranış ontolojiden okunur) hâle getirmektir.

---

## Ay ay durum

| Ay | Dilim | Doküman | Durum |
|----|-------|---------|-------|
| 2026-06 | Açık Bilgi Modeli temeli + ontoloji dinamikleştirme | [2026-06-acik-bilgi-modeli.md](2026-06-acik-bilgi-modeli.md) | ✅ Tamamlandı |
| 2026-07 | Discovery Services & SPARQL keşif | [2026-07-discovery-services.md](2026-07-discovery-services.md) | ✅ Tamamlandı |
| 2026-08 | Dış sistem entegrasyonu — sağlayıcı-agnostik adaptörler | [2026-08-dis-sistem-entegrasyonu.md](2026-08-dis-sistem-entegrasyonu.md) | 🟡 Faz 1–2 tamam |
| 2026-09+ | Repository olgunluğu, SHACL, dağıtık PoC | [backlog.md](backlog.md) | ⚪ Planlandı |

---

## İş paketi bileşenleri — kapsanma haritası

Hangi ayın hangi İP2 bileşenini karşıladığı:

| İP2 bileşeni | Haziran | Temmuz | Ağustos+ |
|---|---|---|---|
| **Açık Bilgi Modeli / RDF temsilleri** | ✅ Ana odak | — | Genişletme |
| **Graph Database** | Guard + tutarlılık | Text index (Lucene) | Federasyon |
| **DTDL tabanlı arayüzler** | Ontoloji eşlemesi | Yetenek keşfinde kullanım | DTDL→RDF tam dönüşüm |
| **SPARQL tabanlı keşif** | Guard sertleştirme | ✅ Ana odak | Federated SPARQL |
| **Discovery Services** | — | ✅ Ana odak | Directory federasyonu |
| **Description Repository** | Ontoloji yayınlama | TDD listeleme | Versiyonlama + TTL |
| **Dağıtık mimari** | — | — | ✅ PoC |

---

## Aylar arası bağımlılık

Diliminler kasıtlı olarak birbirine kilitli — Temmuz, Haziran'ın ürettiği model
üstünde çalışır:

```
Haziran H1 (geo triple'ları RDF'e yaz)
   └──► Temmuz T3 (yakınlık keşfi) — H1 olmadan sorgulanacak veri yok

Haziran H2 (SOSA/SSN/QUDT alignment)
   └──► Temmuz T4 (yetenek keşfi) — standart sınıflar üzerinden sorgulanır

Haziran H4 (vokabüler ontolojiden okunur)
   └──► Temmuz T5 (SPARQL keşif profilleri) — sorgu kataloğu da ontolojide durur
```

---

## Ortak kabul kriterleri

Her ayın dilimi şunları sağlamadan "bitti" sayılmaz:

1. `docker compose up -d --build` temiz ayağa kalkar, health check'ler yeşil
2. Yeni davranış için `backend/tests/` altında test var ve geçiyor
3. Mevcut endpoint imzaları kırılmamış (yalnız ekleme)
4. Testler `docker` olmadan da çalışır — `LocalTwinStore` fixture'ı gerçek
   SPARQL metnini rdflib üzerinde koşturur, servis metotlarını mock'lamaz
5. Ay dokümanındaki **Çıktılar** bölümü doldurulmuş (ne üretildi, nerede)

---

## Mimari referanslar

- W3C WoT Thing Description 1.1 — https://www.w3.org/TR/wot-thing-description11/
- W3C WoT Discovery — https://www.w3.org/TR/wot-discovery/
- SOSA/SSN — https://www.w3.org/TR/vocab-ssn/
- QUDT — https://qudt.org/
- W3C Basic Geo (WGS84) — https://www.w3.org/2003/01/geo/
- DTDL v2 — https://github.com/Azure/opendigitaltwins-dtdl

Proje içi: [../../CLAUDE.md](../../CLAUDE.md), [../NAMED_GRAPHS.md](../NAMED_GRAPHS.md),
[../DTDL_INTEGRATION.md](../DTDL_INTEGRATION.md), [../adr/](../adr/)
