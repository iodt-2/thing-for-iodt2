# 2026/1. Dönem Raporu — İP2 Bölümü İçin Plan

**Rapor:** AGY303-02, Proje 9230044 (IODT2), 2026/1. dönem
**Doldurulacak yer:** Bölüm 1.1.2 — İP2 (489003) Dağıtık Dijital İkiz Mimarisi → **İNNOVA** alt başlığı
**Teslim:** Salı, proje yürütücüsüne

Bu doküman rapor metni değil, metnin planı: hangi paragrafta hangi kabiliyetin
anlatılacağı ve bunun İP2 hedefiyle nasıl ilişkilendirileceği.

---

## 1. Anlatı yayı — önceki rapordan devir

2025/2'de İNNOVA'nın İP2 metni üç faaliyet ekseninde yazılmıştı. 2026/1 aynı
eksenlerde devam etmeli, yoksa okuyucu kopukluk görür.

| Eksen | 2025/2'de söylenen | 2026/1'de söylenecek |
|---|---|---|
| **Faaliyet 2.1 — Açık Bilgi Modeli** | Ayrık ikizlerin ortak bir semantik çerçevede tanımlanmasına temel oluşturuldu | Model **tek otorite** hâline geldi, standart vokabülerlere bağlandı ve dışarıdan makine tarafından çekilebilir oldu |
| **Faaliyet 2.2 — Ayrık dijital ikizler** | DTDL arayüz tanımları modelin uygulama katmanı olarak konumlandırıldı; RDF olarak saklanıp SPARQL ile sorgulanabilir hâle getirildi | İkizler artık **adı bilinmeden** bulunabiliyor: coğrafi konuma ve ölçüm yeteneğine göre keşif |
| **Faaliyet 2.3 — Kompozit ikizler** | Ayrık ikizler arasında bileşen / bağlılık / konum / işlev ilişkileri kuruldu | İlişki grafı **hesaplama yapan bir yapı** hâline geldi: bir olayın zincirleme etkisi graf üzerinden yayılıyor |

**Tek cümlelik dönem mesajı:**
> Dijital ikiz modeli, tarif eden bir kayıttan; keşfedilebilen, dış sistemlerle
> beslenebilen ve üzerinde etki hesabı yapılabilen işletilebilir bir yapıya dönüştü.

**Dil notu:** 2025/2 metninde "değerlendirilmiştir / incelenmiştir / ele alınmıştır"
baskın — bunlar gözlem fiilleri, faaliyet değil. Bizim bölümümüzde
"geliştirilmiştir / uygulanmıştır / doğrulanmıştır / ölçülmüştür" kullanılmalı.
Elimizde çalışan bir sistem ve canlı doğrulama var; bunu dil düzeyinde de göstermeliyiz.

---

## 2. Rapor metni planı — İP2 / İNNOVA

### Kutu 1 — "Dönem başındaki durumu özetleyiniz" (~130 kelime)

Anlatılacaklar:

- Açık Bilgi Modeli kavramsal olarak tanımlıydı; DTDL arayüzleri modelin
  uygulama katmanı olarak konumlandırılmıştı
- Thing tanımları RDF olarak saklanabiliyor ve SPARQL ile sorgulanabiliyordu
- Ayrık ikizler arasında anlamsal ilişki kurma yaklaşımı belirlenmişti
- **Ancak:** model tek bir yerde durmuyordu — aynı kavram hem ontolojide hem
  uygulama kodunda hem arayüzde ayrı ayrı tanımlıydı; dışarıya yayınlanmıyordu;
  standart vokabülerlere bağlı değildi; ikizler yalnızca adıyla bulunabiliyordu
- Dönem başı hedefi: modeli tek kaynağa indirmek, dışarıdan tüketilebilir kılmak
  ve üzerinde keşif yapılabilir hâle getirmek

> Dönem başında **eksik olanı** açıkça söylemek, dönem içinde yapılanı anlamlı
> kılıyor. 2025/2 metni hep "olgunlaştı" demiş; bu dönem farklılaşmak lehimize.

### Kutu 2 — "Dönem içinde yapılan çalışmaları açıklayınız" (~6 paragraf, 700–800 kelime)

#### P1 — Açık Bilgi Modeli'nin tek otorite hâline getirilmesi

- Bilgi modeli sistemin **tek otoritesi** oldu: uygulama servisleri ve kullanıcı
  arayüzü, kavram listelerini kendi içlerinde tutmak yerine modelden okuyor
- Somut sonuç: modele yeni bir ilişki tipi eklemek artık **yalnızca modeli**
  değiştirmeyi gerektiriyor — uygulama kodu ve arayüz kendiliğinden uyum sağlıyor
- Bu, İP2'nin "ontoloji tabanlı, kodun dışında yaşayan model" hedefinin doğrudan
  karşılığı; modelin evrilmesi artık yazılım geliştirme maliyeti doğurmuyor

#### P2 — Standart vokabülerlere hizalama ve modelin yayınlanması

- Model, uluslararası kabul görmüş vokabülerlere hizalandı: **SOSA/SSN**
  (sensör ve gözlem semantiği), **QUDT** (ölçüm birimleri), **WGS84** (coğrafi konum)
- Böylece dışarıdaki bir sistem, bizim modelimizi kendi standart terimleriyle
  yorumlayabiliyor — birlikte çalışabilirlik iddiasının somut karşılığı
- Model dışarıya **dört farklı serileştirmede** yayınlandı ve makine tarafından
  çekilebilir hâle geldi. Bu, İP2 tanımındaki **Description Repository**
  bileşeninin ilk çalışan karşılığıdır
- Coğrafi konum modele dâhil edildi: konum artık yalnızca bir form alanı değil,
  sorgulanabilir bir model öğesi

#### P3 — Keşif servisleri (Discovery Services)

Dönemin en görünür kabiliyet kazanımı: **bir dijital ikizi adını bilmeden bulmak.**

- Sistem kendini standart bir **dijital ikiz dizini** olarak tanıtıyor; dışarıdaki
  bir istemci hangi yetenekleri sunduğunu keşif yoluyla öğrenebiliyor
- **Coğrafi keşif** — "şu noktanın belirli bir yarıçapındaki ikizler". Deprem
  kullanım senaryosunun temel sorgusu; etkilenen altyapıyı bulmanın yolu
- **Yetenek keşfi** — "sıcaklık ölçen ikizler", "ivme ölçen ikizler". Hangi ikizin
  hangi büyüklüğü hangi birimde ölçtüğü bilgisi modelden okunuyor
- Sık kullanılan keşif sorguları, uygulama kodunda değil **modelin yanında** bir
  katalogda duruyor; yeni sorgu eklemek yazılım değişikliği gerektirmiyor
- **W3C WoT Discovery** standardına uyum matrisi çıkarıldı; karşılanan ve
  karşılanmayan yetenekler açıkça belgelendi

> Uyum matrisinde karşılanmayanları da yazmak önemli — raporun Ar-Ge niteliğini
> ve dürüstlüğünü güçlendirir, denetimde soru bırakmaz.

#### P4 — Kompozit ikizler ve zincir etki hesabı

Faaliyet 2.3'ün bu dönemdeki asıl çıktısı. İlişki grafı, tarif eden bir yapıdan
**hesaplama yapan** bir yapıya dönüştü.

- İlişki artık kendi başına bir varlık: kaynağı, hedefi, tipi ve **durumu** olan
  sorgulanabilir bir düğüm
- Ters ilişkiler kendiliğinden üretiliyor — "besler" kurulduğunda karşı tarafta
  "beslenir" oluşuyor; graf iki yönden de yürünebiliyor
- İlişkiler silinmiyor, **durumu değişiyor** (aktif / pasif / bozulmuş); böylece
  geçmiş izlenebilirliği korunuyor
- **Zincir etki:** bir olayın doğrudan etkilediği ikizlerden başlayarak, ilişki
  grafı üzerinden yayılım hesaplanıyor. Deprem senaryosunda doğrudan sarsılan
  sensörlerin yanı sıra; onlardan beslendiği için işlevini yitiren hava istasyonu,
  baz istasyonu, izleme sistemi ve hastane de etkilenen olarak çıkıyor
- **En anlamlı bulgu:** "izler" ilişkisinde yayılım **ters yönde** ilerliyor —
  izlenen istasyon devre dışı kaldığında izleyen sistem körelmiş oluyor. Bu,
  yalnızca yer hareketi modelinin veremeyeceği bir cevaptır ve kompozit dijital
  ikiz iddiasının doğrudan kanıtıdır

> Bu paragraf raporun manşeti olmalı. Deprem kullanım senaryosunda "dijital ikiz
> ne katıyor?" sorusunun cevabı tam olarak burasıdır.

#### P5 — Dış sistem entegrasyonu ve konsorsiyum içi veri birleşimi

- **Sağlayıcıdan bağımsız** bir entegrasyon mimarisi kuruldu: her kurum bir
  adaptör, çekirdek akış kurumdan habersiz. Yeni bir kurum eklemek mimariyi
  değiştirmiyor. IoDT2'nin çok paydaşlı yapısı için tasarım gereği
- İlk adaptör konsorsiyum ortağının coğrafi veri servisiyle gerçekleştirildi:
  bina envanteri, telekom kuleleri ve idari sınırlar dış sistemden alınıp
  dijital ikizlere dönüştürüldü; idari birim ile içindeki yapılar arasında
  **kapsama ilişkileri** modele yazıldı
- **Köken (provenance) bilgisi** modelde tutuluyor: hangi veri nereden, hangi
  kimlikle, ne zaman geldi. Federe bir yapıda aynalanan veriyi kendi verisinden
  ayırt edebilmek için ön koşul
- Tekrarlı içe alma güvenliği sağlandı — değişmemiş kayıt yeniden yazılmıyor
- **İki kurumun çıktısı tek modelde birleşti:** bizim ikizlerimizin konumları
  ortağın deprem simülasyon servisine gönderiliyor, hasar tahmini geri alınıyor
  ve zincir etki hesabına besleniyor
- Simülasyon çalıştırmaları **ayrı bir grafa** yazılıyor: varsayım senaryosu
  envanter verisini bozmuyor, çalıştırma geçmişi birikiyor
- **Bulgu olarak raporlanmalı:** ortağın hasar modelinin mutlak değerleri
  güvenilir değil (merkez üssüne yakın her yapı doyuma ulaşıyor); sıralama
  olarak anlamlı, mutlak değer olarak değil. Adaptör veriyi olduğu gibi
  aktarıyor, sessizce düzeltmiyor

#### P6 — Doğrulama ve olgunluk

- Dönem başında projede çalışan otomatik test yoktu; dönem sonunda kapsamlı bir
  **regresyon test altyapısı** kuruldu ve her kabiliyet testle korunuyor
- Sistem, çalışan yığın üzerinde **uçtan uca canlı doğrulandı**: dış veri içe
  alma, keşif sorguları, simülasyon ve zincir etki, model yayınlama
- Çalışmalar sırasında modelde tespit edilip giderilen tutarsızlıklar belgelendi
  (ör. coğrafi verinin modele hiç ulaşmaması, ters ilişkinin semantik olarak
  yanlış kurulmuş olması, salt-okunur sorgu erişiminin atlatılabilir olması)
- Kiracı (tenant) izolasyonu, çok paydaşlı senaryolarda ayrı ayrı doğrulandı

### Kutu 3 — "Gerçekleşen çıktıları belirtiniz"

| Çıktı | Neye karşılık geliyor |
|---|---|
| **Açık Bilgi Modeli — yayınlanan ontoloji** (standart vokabüler hizalamalı, çoklu serileştirme) | Faaliyet 2.1 · Description Repository |
| **Dijital İkiz Keşif Servisleri** (coğrafi + yetenek + standart dizin) ve W3C WoT Discovery uyum matrisi | Faaliyet 2.2 · Discovery Services · SPARQL tabanlı keşif |
| **Kompozit dijital ikiz ilişki modeli ve zincir etki hesaplama uygulaması** | Faaliyet 2.3 · Graph Database |
| **Dış sistem entegrasyon çerçevesi ve konsorsiyum ortağı adaptörü** | İP5 entegrasyon/gösterim faaliyetlerine girdi |
| **Deprem kullanım senaryosu demo veri seti ve prototip arayüzü** | İP5 gösterim · UC-2 |

> ⚠ Ara çıktı tablosuna (2.1.6) girecek **planlanan tarihler** AGY100 iş
> planından teyit edilmeli — bunlar çıktı adı önerisidir, takvim değil.

---

## 3. İş paketi bileşenleri — kapsanma tablosu

İP2 tanımı şu bileşenleri sayıyor. Raporda bu eşleşmeyi bir yerde göstermek,
"iş paketi kapsamında kalındı" iddiasını kanıtlar:

| İP2 bileşeni | Bu dönem karşılığı |
|---|---|
| Açık Bilgi Modeli / RDF temsilleri | Tek otoriteye indirildi, standart hizalama, dört serileştirmede yayın |
| Discovery Services | Coğrafi keşif, yetenek keşfi, standart dizin self-description |
| Description Repository | Model ve twin tanımları dışarıdan çekilebilir |
| Graph Database | İlişki grafı üzerinde zincir etki hesabı, kiracı izolasyonu |
| DTDL tabanlı arayüzler | Alan bazlı arayüz kütüphanesi; yetenek keşfinde kullanılıyor |
| SPARQL tabanlı keşif | Salt-okunur keşif profili + sorgu kataloğu + erişim sertleştirme |
| Dağıtık mimari | Entegrasyon çerçevesi ve köken bilgisi ile zemin hazırlandı |

---

## 4. Başkasından alınacak veriler

Bu bölümü tek başımıza kapatamayız. Salı'ya yetişmesi için bugün istenmeli:

| Veri | Kimden | Nereye |
|---|---|---|
| İNNOVA 2026/1 adam-ay gerçekleşmesi (İP2 = 489003) | İnnova PMO / mali sorumlu | Tablo 2.1.1 |
| İş paketi gerçekleşme oranı (%) | Proje yönetimi | Tablo 2.1.5 |
| AGY100'deki ara çıktı planlanan tarihleri | Proje yürütücüsü | Tablo 2.1.6 |
| Personel değişikliği var mı | İnnova İK | Bölüm 2.2 |
| İP4 (Q-Learning) metni | Kübra Buzlu | Bölüm 1.1.4 |

**Referans:** 2025/2'de İNNOVA İP2 satırı → öngörülen 7,43 (13) AA, dönem içi
1,06 (1,85) AA, birikimli 3,51 (6,15) AA. Yeni sayı bununla tutarlı olmalı.

---

## 5. Rapora yazmadan önce doğrulanacaklar

| # | Konu |
|---|---|
| 1 | **Test sayısı doğrulanmadı.** Bu makinede Docker kapalı ve host Python'da bağımlılıklar kurulu değil; test takımı koşturulamadı. Rapora sayısal bir test iddiası girecekse önce `docker compose up -d --build` ile koşulmalı |
| 2 | DTDL katmanının otomatik testi yok. Rapor iddiası "tüm katmanlar test edildi" biçiminde kurulmamalı |
| 3 | Demo veri setinde birim tutarsızlığı var (aynı büyüklük iki farklı birim gösterimiyle kayıtlı). QUDT hizalaması "başlatıldı / temel atıldı" tonuyla anlatılmalı, "tamamlandı" denmemeli |
| 4 | Ortağın hasar modelinin mutlak değerleri güvenilir değil — P5'te bulgu olarak yazılmalı, sonuçlar mühendislik çıktısı gibi sunulmamalı |

---

## 6. Salı'ya kadar iş sırası

1. §4'teki verileri bugün e-postayla iste — en uzun bekleyen kalem bu
2. Test takımını canlı ortamda koştur (§5.1)
3. Kutu 1 + Kutu 2 metnini yaz (§2 planına göre, ~800 kelime)
4. Kutu 3 çıktılarını AGY100 tarihleriyle eşle
5. Kübra'nın İP4 metniyle birleştirip yürütücüye tek dosya hâlinde ilet
