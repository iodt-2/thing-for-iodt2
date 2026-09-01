# GitHub ↔ Bitbucket senkronizasyonu

GitHub (`origin`) **kaynak** repodur: tam git geçmişi orada kalır.
Bitbucket (`bitbucket`) **ayna**dır: geçmişsiz başlar, her yeni commit oraya
JIRA anahtarıyla yeniden yazılarak aktarılır.

## Neden tek `git push` iki tarafa yetmiyor

`remote.origin.pushurl` ile aynı push'u iki sunucuya göndermek mümkündür ama
burada işe yaramaz: Bitbucket'ta eski commit'ler olmayacağı için iki taraf farklı
köklerden başlar, dolayısıyla commit SHA'ları da farklı olur. Ortak obje yok.

Bunun yerine `git commit-tree` ile GitHub commit'inin **tree**'si aynen alınıp
Bitbucket kökü üzerinde yeni bir commit olarak yazılır:

```
GitHub (origin)             yerel ref'ler                Bitbucket
main: A→B→C→D→E   ────►  refs/mirror/src/main = E
                          refs/mirror/bb/main  = R→D'→E'  ────►  main: R→D'→E'

R  = "Initial import" — tek commit, C'deki dosya ağacı
D',E' = D,E ile BİREBİR aynı içerik; mesaj JIRA key ile öneklenmiş
```

İçerik byte-byte aynıdır (tree hash'leri eşittir). Çalışma dizinine
dokunulmaz — checkout, stash, branch değiştirme yoktur.

## Kurulum (bir kez)

```bash
# 1. Bitbucket remote'u (zaten tanımlıysa atla)
git remote add bitbucket https://tlcbitbucket.innova.com.tr/scm/iodt/dt_prototype.git

# 2. Varsayılanları yaz. JIRA anahtarı opsiyoneldir:
scripts/bbsync.sh setup            # anahtar yok — mesajlar olduğu gibi gider
scripts/bbsync.sh setup IODT-123   # anahtar varsa mesajlara eklenir

# 3. Geçmiş tutulmayacaksa snapshot modu (bu projenin tercihi)
git config mirror.mode snapshot

# 4. Bitbucket'ın varsayılan branch'i master
git config mirror.bitbucketBranch master

# 5. Bitbucket kimliği — sunucu commit e-postasının geçerli bir Bitbucket
#    kullanıcısı olmasını isteyebilir. Boş bırakılırsa GitHub yazarı korunur.
git config mirror.authorName  "Hayri Can AKYILDIRIM"
git config mirror.authorEmail "cakyildirim@innova.com.tr"

# 6. Bitbucket trunk'ını tek commit ile başlat  (Bitbucket repo BOŞ olmalı)
scripts/bbsync.sh init
```

Windows/PowerShell'de aynısı: `.\scripts\bbsync.ps1 setup IODT-123`

`init`, `mirror.sourceBranch` (varsayılan `main`) branch'inin o anki halini tek
bir "Initial import" commit'i olarak Bitbucket'a gönderir. Bundan önce
**aktarmak istediğin her şeyin o branch'te olduğundan emin ol** — feature
branch'te duran işler kök commit'e girmez.

## Günlük kullanım

```bash
git commit -m "feat(twin): ..."     # normal commit, JIRA key gerekmez
scripts/bbsync.sh push              # GitHub'a push + Bitbucket'a ayna
```

| Komut     | Ne yapar                                                        |
|-----------|-----------------------------------------------------------------|
| `push`    | GitHub'a push, ardından yeni commit'leri Bitbucket'a aynalar     |
| `mirror`  | Sadece Bitbucket'a aynalar (GitHub'a dokunmaz)                   |
| `status`  | Hangi commit'lerin aktarılacağını ve mesajlarını gösterir        |
| `init`    | Bitbucket trunk'ını tek kök commit ile başlatır (bir kez)        |
| `rebuild` | Bitbucket geçmişini silip sıfırdan kurar (force push, onay ister)|

## İki mod

**`snapshot`** (bu projenin tercihi) — her `push` Bitbucket'a **tek bir commit**
ekler; içerik GitHub `main`'in o anki hali, mesaj kapsanan commit'lerin özeti:

```
Sync main @ 9b51962

- feat(twin): add status filter
- fix(rdf): handle empty graph

Source-Commit: 9b519629d7ec327d4130d6ab237b8dbfca473e78
```

**`mirror`** — GitHub'daki her commit Bitbucket'ta ayrı bir commit olur (aynı
içerik, yeniden yazılmış mesaj). Geçmiş istenmiyorsa gereksizdir.

## Commit mesajları

JIRA anahtarı **opsiyoneldir**. `mirror.jiraKey` boşsa mesajlar olduğu gibi
gönderilir (script uyarı basar, çünkü sunucu hook'u reddedebilir). Anahtar
tanımlıysa ve mesajda zaten bir JIRA anahtarı yoksa (`ABC-123` deseni) başa
eklenir. Her iki durumda kaynak commit izi trailer olarak eklenir:

```
IODT-123 feat(discovery): geographic bbox search

Fuseki üzerinde GEO sorgusu için bounding-box filtresi eklendi.

Source-Commit: f3e6e2fe8598d373ee3ba7a96640c09659f9d0a2
```

Belirli bir commit'i başka bir task'a bağlamak için mesajı doğrudan o anahtarla
yaz (`git commit -m "IODT-456 fix: ..."`) — script ona karışmaz.
Tek seferlik geçersiz kılma: `MIRROR_JIRA_KEY=IODT-789 scripts/bbsync.sh push`

## Ayarlar (`.git/config` → `[mirror]`)

| Anahtar                   | Varsayılan  | Açıklama                                    |
|---------------------------|-------------|---------------------------------------------|
| `mirror.jiraKey`          | —           | Mesajlara eklenecek JIRA anahtarı           |
| `mirror.githubRemote`     | `origin`    | Kaynak remote                               |
| `mirror.bitbucketRemote`  | `bitbucket` | Hedef remote                                |
| `mirror.sourceBranch`     | `main`      | Aynalanan yerel branch                      |
| `mirror.bitbucketBranch`  | `main`      | Bitbucket'taki hedef branch (bu repoda `master`) |
| `mirror.authorName`       | —           | Bitbucket commit'lerinin yazarı (boşsa kaynak korunur) |
| `mirror.authorEmail`      | —           | Bitbucket commit'lerinin e-postası          |
| `mirror.mode`             | `mirror`    | `mirror` = 1:1 commit, `snapshot` = tek commit |
| `mirror.initMessage`      | `Initial import from internal repository` | Kök commit mesajı |

Ayarlar `.git/config`'de tutulur, commit edilmez — her klonda `setup` bir kez
çalıştırılmalıdır.

## Branch politikası

Bitbucket'ta **tek bir trunk** (`main`) tutulur. Sebep: geçmişsiz kurgu her
branch'i ayrı bir orphan kök yapar, bunlar Bitbucket'ta birbirine merge
edilemez. Doğru akış:

```
feature branch → GitHub'da PR → main'e merge → scripts/bbsync.sh push
```

## Dayanıklılık notları

- **Push başarısız olursa ref'ler ilerlemez.** `refs/mirror/*` ancak push
  başarıyla döndükten sonra güncellenir; hook reddederse tekrar denemek yeterli.
- **Geçmiş yeniden yazılırsa** (main'de rebase/amend), script bunu fark eder ve
  durur: `rebuild` ile ayna sıfırdan kurulur (Bitbucket'a force push).
- **`refs/mirror/*` yereldir** ve klonlanmaz. Başka bir makineden senkron
  edeceksen o makinede `init` değil, mevcut aynayı devralman gerekir — pratikte
  senkronu tek makineden yürütmek en sağlıklısı.
- **Merge commit'leri** `--first-parent` ile tek commit olarak aynalanır.

## Dikkat

- Bitbucket'ın hook'u sadece JIRA anahtarını değil, commit yazarının e-postasını
  da doğrulayabilir. `mirror.authorName` / `mirror.authorEmail` ile Bitbucket
  tarafındaki kimlik ayrıca ayarlanır; GitHub'daki yazar bilgisi etkilenmez.
  Commit tarihleri her durumda kaynak commit'ten korunur.
- `git config --global user.email` **değiştirme** — o GitHub tarafını da etkiler.
  Bitbucket kimliği yalnızca yukarıdaki `mirror.*` anahtarlarıyla verilmelidir.
- İlk push'tan sonra `git ls-remote bitbucket` ile hedefte **beklenmedik ref
  olmadığını** doğrula. Ortamdaki bazı araçlar (IDE eklentileri, git notes
  senkronu) tanımlı her remote'a kendi ref'lerini gönderebilir. Fazlalık varsa:
  `git push bitbucket :refs/notes/ai`
