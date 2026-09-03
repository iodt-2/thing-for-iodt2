#!/usr/bin/env bash
# Fuseki'de 'iodt2-thing-description' dataset'ini olusturur — BIR KEZ.
#
#   scripts/bootstrap-fuseki.sh
#
# NEDEN GEREKLI: backend dataset'i kendisi OLUSTURMAZ, var oldugunu varsayar
# (twin_rdf_service.py:63 endpoint'i dogrudan kurar). Bos bir Fuseki volume'unde
# bu adim atlanirsa her SPARQL istegi 404 doner.
#
# Idempotent: dataset varsa dokunmaz.

set -euo pipefail
cd "$(dirname "$0")/.."

DATASET="iodt2-thing-description"
NETWORK="iodt2-network"

err()  { printf '\033[31m[hata]\033[0m %s\n' "$*" >&2; }
info() { printf '\033[36m[bilgi]\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m[ok]\033[0m %s\n' "$*"; }

[ -f .env ] || { err ".env yok. .env.example'dan kopyala."; exit 1; }
set -a; . ./.env; set +a
: "${FUSEKI_PASSWORD:?FUSEKI_PASSWORD degeri .env dosyasinda bos}"
FUSEKI_USERNAME="${FUSEKI_USERNAME:-admin}"

# Fuseki imajinda curl olup olmadigi belirsiz — ayri bir curl container'i kullan.
# Ayni docker network'unde oldugu icin fuseki'ye ismiyle erisir.
fcurl() {
  docker run --rm --network "$NETWORK" curlimages/curl:latest \
    -sS -u "${FUSEKI_USERNAME}:${FUSEKI_PASSWORD}" "$@"
}

info "Fuseki bekleniyor..."
for i in $(seq 1 30); do
  if fcurl -f "http://fuseki:3030/\$/ping" >/dev/null 2>&1; then break; fi
  [ "$i" -eq 30 ] && { err "Fuseki 60 sn icinde ayaga kalkmadi"; exit 1; }
  sleep 2
done

if fcurl -f "http://fuseki:3030/\$/datasets" 2>/dev/null | grep -q "\"/${DATASET}\""; then
  ok "dataset '${DATASET}' zaten var — dokunulmadi"
  exit 0
fi

info "dataset olusturuluyor: ${DATASET} (tdb2)"
fcurl -f -X POST \
  --data "dbType=tdb2&dbName=${DATASET}" \
  "http://fuseki:3030/\$/datasets" >/dev/null

ok "dataset '${DATASET}' olusturuldu"
