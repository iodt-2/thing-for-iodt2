#!/usr/bin/env bash
# Sunucuda tek komutluk guncelleme: pull -> build -> test -> up -> smoke.
#
#   scripts/update.sh                # normal
#   scripts/update.sh --skip-tests   # testleri atla (acil durum)
#
# Etiketi SEN vermezsin — pull sonrasi commit SHA'sindan uretilir. Boylece
# calisan surumun hangi commit oldugu her zaman bellidir:
#   docker images 'local/iodt2-*'
#   cat .deploy-last-tag
#
# Asil isi scripts/deploy.sh yapar; burasi sadece pull + etiket uretimi.

set -euo pipefail
cd "$(dirname "$0")/.."

err()  { printf '\033[31m[hata]\033[0m %s\n' "$*" >&2; }
info() { printf '\033[36m[bilgi]\033[0m %s\n' "$*"; }

# Sunucuda elle degistirilmis dosya varsa pull yarim kalir — once bunu soyle.
if ! git diff --quiet || ! git diff --cached --quiet; then
  err "calisma dizininde kaydedilmemis degisiklik var:"
  git status --short >&2
  err "sunucuda elle duzenleme yapma. 'git checkout -- <dosya>' ile geri al."
  exit 1
fi

OLD_SHA=$(git rev-parse --short=12 HEAD)
info "mevcut: ${OLD_SHA}"

info "pull..."
# --ff-only: sunucuda merge commit'i olusmasin, sapma varsa gorunur hata versin
git pull --ff-only

NEW_SHA=$(git rev-parse --short=12 HEAD)

if [ "$OLD_SHA" = "$NEW_SHA" ]; then
  info "yeni commit yok (${NEW_SHA}) — yine de yeniden build edilecek."
  info "NOT: etiket ayni kalacagi icin bu deploy'da rollback hedefi olmayacak."
fi

info "deploy: ${NEW_SHA}"
exec scripts/deploy.sh --build "$@" "$NEW_SHA"
