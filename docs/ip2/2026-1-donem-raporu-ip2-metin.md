# 2026/1. Dönem Raporu — İP2 / İNNOVA Metni (Taslak)

**Rapor:** AGY303-02, Proje 9230044 (IODT2), 2026/1. dönem
**Bölüm:** 1.1.2 — İP2 (489003) Dağıtık Dijital İkiz Mimarisi → **İNNOVA**

> Aşağıdaki metin doğrudan forma aktarılmak üzere hazırlanmıştır. Rapor diline
> (2025/2 dönem raporu) uyumlu, kavram ve faaliyet düzeyinde yazılmıştır.
> Metnin sonundaki "Hazırlayan notları" bölümü forma girmeyecektir.

---

## 2026/1. Dönem başındaki durumu özetleyiniz

Dönem başında, Açık Bilgi Modeli'nin kavramsal çerçevesi tanımlanmış ve DTDL tabanlı
arayüz tanımları bu modelin uygulama katmanı olarak konumlandırılmıştı. Dijital ikiz
tanımlarının RDF temsilleri üzerinden Description Repository ve Graph Database
katmanlarında yönetilmesi sağlanmış; söz konusu tanımların SPARQL ile sorgulanabilir
hâle getirilmesiyle ayrık dijital ikizlerin makine tarafından yorumlanabilir varlıklar
olarak yapılandırılmasına zemin hazırlanmıştı. Ayrıca ayrık dijital ikizler arasında
bileşen, bağlılık, konum ve işlev ilişkileri üzerinden anlamsal bağ kurulmasına yönelik
yaklaşım belirlenmiş; kısmen kompozit dijital ikiz yapılandırmasına ilişkin ilk
çerçeve ortaya konmuştu.

Bununla birlikte dönem başı itibarıyla bilgi modelinin tek bir otorite altında
toplanmadığı; aynı kavram kümesinin ontoloji, uygulama servisleri ve kullanıcı arayüzü
katmanlarında birbirinden bağımsız biçimde tanımlandığı değerlendirilmiştir. Modelin
dış sistemler tarafından çekilebilir biçimde yayımlanmamış olması, uluslararası kabul
görmüş vokabülerlerle hizalanmamış bulunması ve dijital ikizlere yalnızca tanımlayıcıları
üzerinden erişilebilmesi; birlikte çalışabilirlik ve semantik keşif hedefleri açısından
öncelikli eksiklikler olarak tespit edilmiştir. Bu doğrultuda dönem hedefi, bilgi
modelinin tek kaynağa indirilmesi, standart vokabülerlere bağlanması ve model üzerinde
keşif ile çıkarım yapılabilir bir yapıya kavuşturulması olarak belirlenmiştir.

---

## 2026/1. Dönemi içinde yapılan çalışmaları açıklayınız

Bu dönemde İP2 kapsamında, Açık Bilgi Modeli'nin dağıtık dijital ikiz mimarisi içinde
işletilebilir bir bileşen hâline getirilmesine yönelik çalışmalar yürütülmüştür.
Çalışmaların temel yönelimi, modelin yalnızca dijital ikizleri tarif eden bir tanım
kümesi olmaktan çıkarılarak; üzerinde keşif yapılabilen, dış sistemlerden beslenebilen
ve sistem davranışına ilişkin çıkarım üretebilen bir yapıya dönüştürülmesi olmuştur.

**Faaliyet 2.1 kapsamında** Açık Bilgi Modeli'nin sistem içindeki tek otorite hâline
getirilmesine yönelik çalışmalar gerçekleştirilmiştir. Bu kapsamda, daha önce ontoloji,
uygulama servisleri ve kullanıcı arayüzü katmanlarında ayrı ayrı tanımlanan kavram
kümeleri tek bir semantik kaynak altında birleştirilmiş; uygulama katmanlarının bu
kavramları doğrudan modelden okuması sağlanmıştır. Böylece modelin genişletilmesi
yazılım geliştirme faaliyetinden bağımsız hâle getirilmiş, yeni bir ilişki türünün
veya kavramın modele kazandırılması yalnızca ontoloji düzeyinde bir düzenleme ile
mümkün kılınmıştır. Söz konusu yaklaşım, İP2'nin ontoloji tabanlı ve kodun dışında
yaşayan model hedefinin doğrudan karşılığı olarak değerlendirilmiştir.

Aynı faaliyet kapsamında modelin uluslararası kabul görmüş vokabülerlerle hizalanmasına
yönelik çalışmalar yürütülmüştür. Sensör ve gözlem semantiği SOSA/SSN, ölçüm birimleri
QUDT, coğrafi konum bilgisi ise WGS84 vokabüleri üzerinden ilişkilendirilmiş; hizalama
matrisi ve gerekçeleri dokümante edilmiştir. Bu hizalama sayesinde dış sistemlerin
modeli kendi standart terimleri üzerinden yorumlayabilmesine olanak sağlanmış ve
birlikte çalışabilirlik iddiası somut bir karşılığa kavuşturulmuştur. Ayrıca daha önce
yalnızca tanım düzeyinde tutulan coğrafi konum bilgisinin semantik model içine
taşınması sağlanmış; konum, sorgulanabilir bir model öğesi hâline getirilmiştir. Model,
farklı serileştirme biçimleriyle dış sistemlerin erişimine açılarak makine tarafından
çekilebilir duruma getirilmiş; böylece referans mimarideki Description Repository
bileşeninin işlevsel karşılığı ortaya konmuştur.

**Faaliyet 2.2 kapsamında**, ayrık dijital ikizlerin yalnızca tanımlayıcıları üzerinden
değil, taşıdıkları semantik nitelikler üzerinden bulunabilmesini sağlayan keşif
servisleri geliştirilmiştir. Bu kapsamda sistemin kendisini standart bir dijital ikiz
dizini olarak tanıtması sağlanmış; dış istemcilerin sunulan keşif yeteneklerini
önceden bilmeksizin öğrenebilmesine olanak tanınmıştır. Coğrafi yakınlığa dayalı keşif
ile belirli bir konumun etki alanındaki dijital ikizlerin belirlenmesi mümkün kılınmış;
yetenek tabanlı keşif ile hangi dijital ikizin hangi büyüklüğü hangi birimde ölçtüğü
bilgisinin model üzerinden sorgulanabilmesi sağlanmıştır. Sıklıkla kullanılan keşif
sorguları uygulama kodu yerine modelin yanında bir katalog altında tutularak, yeni
sorgu tanımlarının yazılım değişikliği gerektirmeden eklenebilmesi sağlanmıştır.
Geliştirilen keşif yapısının W3C WoT Discovery şartnamesi ile uyumu değerlendirilmiş;
karşılanan ve bu aşamada karşılanmayan yetenekler bir uyum matrisi altında açık biçimde
raporlanmıştır. Coğrafi ve yetenek tabanlı keşif, şartnamede yer almayan ancak proje
kullanım senaryolarının ihtiyaç duyduğu ek yetenekler olarak modele kazandırılmıştır.

**Faaliyet 2.3 kapsamında**, kompozit dijital ikiz yapısının yalnızca ilişki tanımlayan
bir kurgudan, sistem davranışına ilişkin çıkarım üretebilen bir yapıya dönüştürülmesine
yönelik çalışmalar gerçekleştirilmiştir. Bu kapsamda ilişkiler, kaynak, hedef, tür ve
durum bilgisi taşıyan sorgulanabilir varlıklar olarak yapılandırılmış; ters yönlü
ilişkilerin model tarafından türetilmesi sağlanarak ilişki grafının her iki yönde de
yürünebilmesi mümkün kılınmıştır. İlişkilerin sistemden çıkarılması yerine durum
değişikliği ile yönetilmesi yaklaşımı benimsenmiş, böylece tarihsel izlenebilirlik
korunmuştur. Bu yapı üzerine, bir olayın doğrudan etkilediği dijital ikizlerden
başlayarak ilişki grafı boyunca zincirleme etkinin hesaplanmasını sağlayan bir yayılım
mekanizması geliştirilmiştir. Deprem kullanım senaryosu üzerinde yürütülen çalışmalarda,
doğrudan etkilenen ölçüm birimlerinin yanı sıra bu birimlerden beslendiği için işlevini
yitiren haberleşme, izleme ve kritik tesis bileşenlerinin de etkilenen varlıklar olarak
belirlenebildiği gözlenmiştir. Özellikle izleme ilişkisi üzerinden yayılımın ters yönde
ilerlediği; izlenen bileşenin devre dışı kalması durumunda izleyen bileşenin işlevsel
körlüğe uğradığı tespit edilmiştir. Bu bulgu, yalnızca fiziksel etki modellerinin
üretemeyeceği bir çıkarım niteliği taşımakta olup, kompozit dijital ikiz yaklaşımının
katma değerini doğrudan ortaya koymaktadır.

Dönem içerisinde ayrıca, dağıtık dijital ikiz mimarisinin proje ortaklarının sistemleriyle
birlikte çalışabilmesine yönelik bir **dış sistem entegrasyon çerçevesi** oluşturulmuştur.
Çerçeve, IoDT2'nin çok paydaşlı yapısı gözetilerek tek bir kuruma özgü olmayacak biçimde
tasarlanmış; her kurumun kendi veri kümeleri ve alan eşlemeleriyle tanımlanan bağımsız
bir uyarlama katmanı üzerinden sisteme bağlanması, çekirdek içe alma akışının ise
sağlayıcıdan bağımsız kalması esası benimsenmiştir. Bu yaklaşım ile yeni bir kurumun
entegrasyona dâhil edilmesi mimari değişiklik gerektirmeyen bir işlem hâline getirilmiştir.
Çerçevenin ilk uygulaması Netcad'in coğrafi veri servisleri ile gerçekleştirilmiş; bina
envanteri, telekom kule bilgileri ve idari sınır verileri dış sistemden alınarak dijital
ikiz tanımlarına dönüştürülmüş, idari birimler ile bunların kapsadığı yapılar arasında
anlamsal kapsama ilişkileri kurulmuştur. İçe alınan verinin kaynağı, dış tanımlayıcısı
ve alınma zamanı köken bilgisi olarak model içinde tutulmuş; federe bir yapıda aynalanan
verinin kuruma ait veriden ayırt edilebilmesi sağlanmıştır. Ayrıca tekrarlı içe alma
işlemlerinde değişmemiş kayıtların yeniden yazılmasını önleyen bir bütünlük denetimi
uygulanmıştır.

Entegrasyon çerçevesi üzerine, proje ortağının deprem simülasyon servisi ile dijital
ikiz grafının eşleştirilmesine yönelik çalışmalar yürütülmüştür. Bu kapsamda dijital
ikizlerin konum bilgileri ortağın simülasyon servisine iletilmekte, dönen yer hareketi
ve hasar tahminleri modele işlenmekte ve elde edilen doğrudan etki, ilişki grafı üzerinden
hesaplanan zincirleme etki ile birleştirilmektedir. Böylece iki farklı kurumun ürettiği
çıktının ortak bir semantik model altında bütünleştirilmesi sağlanmış; İP5 kapsamındaki
entegrasyon ve gösterim faaliyetlerine doğrudan girdi oluşturacak bir yapı ortaya
konmuştur. Simülasyon çalıştırmalarının envanter verisinden ayrı bir alanda tutulması
yaklaşımı benimsenerek, varsayım senaryolarının mevcut dijital ikiz tanımlarını
etkilememesi ve çalıştırma geçmişinin birikmesi sağlanmıştır. Yürütülen doğrulama
çalışmalarında, ortağın hasar modelinin merkez üssüne yakın bölgelerde doyuma ulaştığı
ve mutlak değerlerinin mühendislik çıktısı olarak kullanılmaya elverişli olmadığı; buna
karşılık göreli sıralama açısından anlamlı sonuçlar ürettiği tespit edilmiştir. Söz
konusu bulgu ortakla paylaşılmış, entegrasyon katmanının veriyi dönüştürmeden aktarması
yaklaşımı korunmuştur.

Dönem boyunca yürütülen çalışmalar, geliştirilen yeteneklerin bozulmadan sürdürülebilmesini
sağlamak amacıyla otomatik bir **regresyon doğrulama altyapısı** ile desteklenmiştir.
Model üzerinde tanımlanan her yeteneğin doğrulama kapsamına alınması sağlanmış; ayrıca
sistem, ayağa kaldırılmış çalışma ortamı üzerinde uçtan uca doğrulanarak dış veri içe
alma, semantik keşif, simülasyon eşleştirmesi ve model yayımlama akışlarının birlikte
işlediği gösterilmiştir. Çok kiracılı yapının veri izolasyonu, farklı kurumlara ait veri
kümeleri üzerinde ayrı ayrı sınanmıştır. Çalışmalar sırasında modelde tespit edilen
tutarsızlıklar giderilmiş; bu kapsamda coğrafi bilginin semantik modele hiç aktarılmadığı,
ters ilişki tanımının anlamsal olarak karşılığı bulunmayan bir biçimde kurgulandığı ve
salt okunur sorgu erişiminin öngörülen sınırların dışına çıkabildiği belirlenerek ilgili
düzenlemeler yapılmıştır. Ölçüm birimlerinin QUDT hizalaması bu dönemde temel düzeyde
kurulmuş olup, demo veri kümesindeki birim gösterim farklılıklarının tek bir birim
sözlüğü altında birleştirilmesi çalışması sonraki döneme bırakılmıştır.

Elde edilen çıktılar, İP2'nin referans mimarideki konumu ile uyumlu biçimde diğer iş
paketlerine girdi oluşturacak şekilde ele alınmıştır. Semantik keşif yapısı, İP3
kapsamındaki olay tabanlı ve sunucusuz uç bilişim yaklaşımında dijital ikizlerin veri
akışlarına bağlanmasına; kompozit ikiz ve zincir etki yapısı ise İP5 kapsamındaki deprem
kullanım senaryosunun uçtan uca gösterimine temel teşkil edecek niteliktedir. Sonraki
dönemde, dijital ikiz tanımlarının sürüm ve yaşam döngüsü yönetimi, model uyumunun
makine tarafından denetlenmesi ve dağıtık düğümler arası federe sorgulama yapısının
kavram ispatı düzeyinde ele alınması planlanmaktadır.

---

## Gerçekleşen çıktıları belirtiniz

- Açık Bilgi Modeli — standart vokabüler hizalamalı, dış sistemlerce çekilebilir
  biçimde yayımlanan ontoloji ve hizalama matrisi
- Dijital İkiz Keşif Servisleri Uygulaması ve W3C WoT Discovery uyum matrisi
- Kompozit Dijital İkiz İlişki Modeli ve Zincir Etki Hesaplama Uygulaması
- Dış Sistem Entegrasyon Çerçevesi ve proje ortağı veri servisleri uyarlama katmanı
- Deprem kullanım senaryosu dijital ikiz veri seti ve prototip gösterim arayüzü

---

# Hazırlayan notları (forma girmeyecek)

## Metinde bilinçli olarak yapılmayanlar

- **Sayısal metrik verilmedi.** Test sayısı, uç sayısı, triple sayısı gibi değerler
  metne alınmadı. Bunların doğrulanması için çalışma ortamının ayağa kaldırılması
  gerekiyor; ayrıca 2025/2 raporunun İNNOVA bölümünde de bu tür metrikler kullanılmamış.
- **Ürün/teknoloji adı verilmedi.** Rapor dili bileşen ve kavram düzeyinde;
  kullanılan kütüphane ve altyapı adları metne alınmadı.
- **Netcad adı yalnızca entegrasyon bağlamında geçti.** 2025/2'de İNNOVA da Türk
  Telekom'u bu biçimde anmış; ortak raporda tutarlı.

## Metne dâhil edilen bulgular

Rapora Ar-Ge niteliği kazandıran, denetimde soru bırakmayan üç dürüst tespit
bilinçli olarak metne yerleştirildi:

1. İzleme ilişkisinde yayılımın ters yönde ilerlemesi — pozitif bulgu, manşet
2. Ortağın hasar modelinin mutlak değer olarak kullanılamaması — sınırlılık beyanı
3. QUDT birim hizalamasının temel düzeyde kaldığı — "tamamlandı" denmedi

## Teslimden önce tamamlanacaklar

| Konu | Kimden |
|---|---|
| İNNOVA 2026/1 adam-ay gerçekleşmesi (İP2 = 489003) — Tablo 2.1.1 | İnnova PMO / mali sorumlu |
| İş paketi gerçekleşme oranı (%) — Tablo 2.1.5 | Proje yönetimi |
| Ara çıktıların AGY100'deki planlanan tarihleri — Tablo 2.1.6 | Proje yürütücüsü |
| Personel değişikliği beyanı — Bölüm 2.2 | İnnova İK |
| İP4 (Q-Learning) metni — Bölüm 1.1.4 | Kübra Buzlu |

**Referans:** 2025/2'de İNNOVA İP2 satırı → öngörülen 7,43 (13) AA, dönem içi
1,06 (1,85) AA, birikimli 3,51 (6,15) AA.
