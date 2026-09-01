# 2026/1 Dönem Raporu — İP2 İddialarının Doğrulama Notu

**Proje:** 9230044 — IODT2 | **İş paketi:** İP2 (489003) | **Kuruluş:** İNNOVA
**Hazırlayan:** Hayri Can Akyıldırım | **Tarih:** 28 Ağustos 2026

Rapor taslağındaki teknik iddialar kod tabanı ve proje dokümantasyonu üzerinden
tek tek doğrulanmıştır. Aşağıda her iddianın karşılığı, dayanağı ve varsa
düzeltme ihtiyacı yer almaktadır.

---

## 1. Öncelikli konu — çalışmaların takvimi

Doğrulama sırasında ortaya çıkan en önemli bulgu, iddiaların bir kısmının rapor
dönemi (Ocak–Haziran 2026) dışında gerçekleşmiş olmasıdır.

| Çalışma | Gerçekleşme tarihi | 2026/1 içinde mi |
|---|---|---|
| Prototip platform, ilişki modeli, mimari karar kayıtları, graf görselleştirme | Şubat–Nisan 2026 | Evet |
| Kadıköy demo veri seti | 1 Haziran 2026 | Evet |
| Ontoloji hizalama ve yayınlama | 28 Temmuz 2026 | **Hayır** |
| Keşif servisleri (Discovery Services) | 29 Temmuz 2026 | **Hayır** |
| Dış sistem entegrasyonu, simülasyon eşleşmesi, zincir etki | 18 Ağustos 2026 | **Hayır** |

**Değerlendirme:** Rapor metninin önemli bir bölümü dönem dışı çalışmaları
anlatmaktadır. İki seçenek bulunmaktadır: (i) Temmuz–Ağustos çalışmalarının
2026/2 dönemine bırakılması, (ii) mevcut kapsamın korunarak takvim durumunun
açıkça beyan edilmesi. Konunun proje yönetimiyle netleştirilmesi gerekmektedir.

---

## 2. İddia doğrulama tablosu

| # | İddia | Durum | Dayanak ve açıklama |
|---|---|---|---|
| 1 | Açık Bilgi Modeli tek semantik kaynak hâline getirildi | ✅ Doğrulandı | Ontoloji tek kaynak olarak tutulmakta; servis ve arayüz kavramları buradan okumaktadır. `test_service_keeps_no_private_copy_of_the_vocabulary` ve `test_adding_a_type_to_the_ontology_is_enough` testleri bunu doğrulamaktadır. |
| 2 | Model dış sistemlerce çekilebilir biçimde yayımlandı | ✅ Doğrulandı | `GET /api/v2/ontology` ucu çalışmaktadır. Turtle, JSON-LD, RDF/XML ve N-Triples serileştirmeleri sunulmakta olup ontoloji 409 triple içermektedir. |
| 3 | SOSA/SSN, QUDT ve WGS84 hizalaması yapıldı | ✅ Doğrulandı | Ontolojide `ts:` ad alanı dışına çıkan 10 hizalama triple'ı ve 5 schema.org bağı bulunmaktadır. Eşleme matrisi ilgili dilim dokümanında yer almaktadır. 34 hizalama testi geçmektedir. |
| 4 | Semantik keşif servisi geliştirildi | ✅ Doğrulandı | Çalışan 9 uç bulunmaktadır: dizin self-description, TD listeleme, tekil TD, coğrafi yakınlık, yetenek keşfi, yetenek envanteri, salt okunur SPARQL, sorgu kataloğu ve tekil kayıtlı sorgu. |
| 5 | Konum bazlı keşif çalışıyor | ✅ Doğrulandı | `GET /discovery/nearby` ucu enlem, boylam ve yarıçap parametreleriyle çalışmakta; `geo:lat` ve `geo:long` yüklemleri üzerinde sorgulamaktadır. Gerçek veriyle alınmış mesafe sıralı çıktı dokümante edilmiştir. |
| 6 | Yetenek bazlı keşif çalışıyor | ⚠️ Kısmen | `GET /discovery/by-capability` ucu çalışmakta ve canlı çıktısı belgelenmiştir. Ancak demo veri setindeki birim gösterim tutarsızlığı filtrenin ayrıştırma gücünü düşürmektedir. |
| 7 | Sorgu kataloğu model yanında tutuluyor | ✅ Doğrulandı | Katalog uygulama kodunda değil, yapılandırma dosyası olarak tutulmaktadır; 20 kayıtlı sorgu içermektedir. Yeni sorgu eklemek arayüz derlemesi gerektirmemektedir. |
| 8 | W3C WoT Discovery uyum matrisi oluşturuldu | ✅ Doğrulandı | Temmuz dilimi dokümanında yer almaktadır. 5 karşılanan, 5 karşılanmayan ve 2 şartname dışı ek yetenek açıkça listelenmiştir. Ara çıktı olarak sunulabilir. |
| 9 | Kompozit ikiz ilişkileri birinci sınıf sorgulanabilir varlıklara dönüştürüldü | ✅ Doğrulandı | Ontolojide kaynak, hedef, tür ve durum ayrı birer özellik olarak tanımlıdır. Modelleme kararı ADR-0001'de gerekçelendirilmiştir. |
| 10 | Ters ilişkiler otomatik türetiliyor | ⚠️ İfade düzeltilmeli | Ters tip eşlemesi ontolojiden okunmakta, ancak üretim bir çıkarım motoru tarafından değil uygulama katmanında SPARQL INSERT ile yapılmaktadır. Rapordaki "model tarafından türetilmesi" ifadesi yanıltıcıdır. |
| 11 | İlişkiler silinmeyip durum değişikliğiyle yönetiliyor | ✅ Doğrulandı | Hem tasarım kararı (ADR-0003) hem uygulama karşılığı mevcuttur. Kaynak silindiğinde hedef graftaki ters düğüm pasif duruma alınmakta, kaydı düşürülmemektedir. |
| 12 | Zincirleme etki hesaplama mekanizması geliştirildi | ✅ Doğrulandı | Bağımsız test edilebilir saf fonksiyon olarak geliştirilmiştir; genişlik öncelikli yayılım, derinlik ve zayıflama hesabı içermektedir. 16 test bulunmaktadır. Canlı koşumda 2 doğrudan ve 5 zincir etki üretilmiştir. |
| 13 | "İzleme ilişkisi ters yönde yayılıyor" bulgusu | ⚠️ İfade düzeltilmeli | Davranış gerçektir: ontolojide etki yönü açıkça tanımlıdır, adanmış testi bulunmakta ve canlı koşumda gözlenmiştir. Ancak bu bir tasarım kararıdır, kendiliğinden ortaya çıkan bir bulgu değildir. "Tespit edilmiştir" yerine "modellenmiş ve doğrulanmıştır" denmelidir. |
| 14 | Sağlayıcıdan bağımsız entegrasyon çerçevesi geliştirildi | ⚠️ Kısmen | Soyut sağlayıcı arayüzü ve kayıt mekanizması mevcuttur; REST katmanı ve içe alma akışı hiçbir kurum modülünü doğrudan çağırmamaktadır. Yeni kurum eklemek tek satırlık kayıt işlemidir. Ancak hâlihazırda tek uyarlama bulunduğundan mimari ikinci bir sağlayıcıyla sınanmamıştır. |
| 15 | Netcad verileri içe alındı | ❌ Dönem dışı | Çalışma 18 Ağustos 2026 tarihinde gerçekleşmiştir; 30 Haziran 2026 öncesine ait değildir. |
| 16 | Provenance/köken bilgisi tutuluyor | ✅ Doğrulandı | Kaynak kurum, dış tanımlayıcı, dış adres ve alınma zamanı ontolojide tanımlı özelliklerdir; içe alma akışı bunları yazmakta ve canlı ortamda doğrulanmıştır. |
| 17 | Tekrarlı içe alma için bütünlük kontrolü var | ✅ Doğrulandı | İçerik özeti (hash) tabanlıdır. Depolama öncesi karşılaştırma yapılmakta, değişmemiş kayıt yeniden yazılmayıp ayrı sayaçta raporlanmaktadır. |
| 18 | Netcad deprem simülasyon servisiyle entegrasyon var | ❌ Dönem dışı | Entegrasyon 18 Ağustos 2026 tarihinde gerçekleştirilmiştir; 2026/1 dönemi içinde değildir. |
| 19 | Simülasyon koşuları envanterden ayrı tutuluyor | ✅ Doğrulandı | Her koşum kendi adlandırılmış grafına yazılmakta, dijital ikiz envanter grafına dokunulmamaktadır. Böylece varsayım senaryoları envanteri etkilememekte ve koşum geçmişi birikmektedir. |
| 20 | Otomatik regresyon altyapısı kuruldu | ⚠️ Kısmen | 285 test bulunmakta ve tümü geçmektedir (28 Ağustos 2026 tarihli koşum, 12 saniye). Ancak sürekli entegrasyon (CI) hattı kurulu değildir; testler elle çalıştırılmaktadır. |
| 21 | Uçtan uca doğrulama yapıldı | ⚠️ İfade düzeltilmeli | Dış veri alma, keşif, simülasyon eşleşmesi ve model yayınlama zinciri 18 Ağustos 2026'da çalışan ortam üzerinde uçtan uca koşturulmuş ve belgelenmiştir. Ancak bu zinciri baştan sona koşan otomatik bir test bulunmamaktadır; doğrulama elle yapılmıştır. |
| 22 | Çok kiracılı veri izolasyonu test edildi | ✅ Doğrulandı | İzolasyon, adlandırılmış graf adresinin kiracı kimliğini içermesiyle sağlanmaktadır. Konuya özel 7 test bulunmaktadır. |
| 23 | Belirli hatalar bulundu ve düzeltildi | ✅ Doğrulandı | Bulgular dilim dokümanlarında tablo hâlinde kayıtlıdır. Başlıcaları: coğrafi verinin semantik modele hiç aktarılmaması, ters ilişki tanımının OWL açısından karşılığı bulunmayan biçimde kurgulanmış olması ve salt okunur sorgu korumasının atlatılabilir olması. |
| 24 | QUDT hizalaması temel düzeyde kaldı | ✅ Doğrulandı | Tek bir referans bağı kurulmuştur. Bu bilinçli bir tercihtir: ilgili alan birim sembolünü metin olarak taşıdığından daha güçlü bir bağ yanlış beyan olurdu. Birimlerin ortak bir birim sözlüğü altında normalize edilmesi sonraki döneme bırakılmıştır. |
| 25 | İP2 çıktısı İP3'e teknik olarak bağlandı | ❌ Bağlanmadı | Olay tabanlı iletişim, mesajlaşma veya sunucusuz çalışma zamanına ilişkin herhangi bir kod bulunmamaktadır. Yalnızca mimari hazırlık düzeyindedir. Rapor metninde "temel teşkil edecek niteliktedir" ifadesi kullanılmış olup bu doğrudur; "entegre edilmiştir" denmemelidir. |

**Özet:** 25 iddianın 15'i doğrudan doğrulanmış, 6'sı kısmen karşılanmakta veya
ifade düzeltmesi gerektirmekte, 4'ü ise dönem dışı ya da karşılanmamış durumdadır.

---

## 3. Rapor metninde yapılması gereken düzeltmeler

| # | Bulunduğu yer | Mevcut ifade | Önerilen ifade |
|---|---|---|---|
| 1 | Faaliyet 2.3 paragrafı | "ters yönlü ilişkilerin model tarafından türetilmesi sağlanarak" | "ters yönlü ilişkilerin, ontolojiden okunan ters tip eşlemesi kullanılarak uygulama katmanında üretilmesi sağlanarak" |
| 2 | Faaliyet 2.3 paragrafı | "…işlevsel körlüğe uğradığı tespit edilmiştir" | "…işlevsel körlüğe uğradığı modellenmiş ve doğrulama koşumlarında teyit edilmiştir" |
| 3 | Doğrulama paragrafı | "uçtan uca doğrulanarak" | "çalışan ortam üzerinde yürütülen doğrulama koşumlarıyla uçtan uca sınanarak" |
| 4 | Genel | — | Takvim konusunda Bölüm 1'deki karar uygulanmalıdır |

---

## 4. Ara çıktı olarak sunulabilecek belgeler

Doğrulama sırasında, rapora ek olarak sunulabilecek nitelikte üç belge tespit
edilmiştir:

- **W3C WoT Discovery uyum matrisi** — karşılanan ve karşılanmayan yetenekleri
  açıkça listelemektedir
- **Ontoloji eşleme matrisi** — standart vokabülerlerle kurulan bağlar ve
  bunların gerekçeleri
- **Mimari karar kayıtları (ADR-0001 … ADR-0004)** — kompozit dijital ikiz
  ilişki modelinin tasarım gerekçeleri

Ayrıca Faaliyet 2.3 kapsamındaki çalışmaları tek başlık altında toplayan bir
prototip dokümanı hâlihazırda bulunmamaktadır. İçerik mimari karar kayıtları,
demo senaryosu ve zincir etki bölümlerine dağılmış durumdadır; talep edilmesi
hâlinde derlenerek ara çıktı hâline getirilebilir.
