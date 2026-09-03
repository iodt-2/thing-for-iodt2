#!/usr/bin/env bash
# iodt2 production deploy — deploy sunucusunda calisir.
#
#   scripts/deploy.sh --build <TAG>    # kaynaktan build et + calistir
#   scripts/deploy.sh <TAG>            # daha once build edilmis <TAG> ile calistir
#                                      # (rollback icin: imaj makinede zaten var)
#
# Ne yapar:
#   1. --build ise imajlari kaynaktan uretir; degilse o etiketli imajlarin
#      makinede oldugunu dogrular (rollback yolu)
#   2. --build ise testleri uretilen imajin icinde kosar (--skip-tests ile atlanir)
#   3. Onceki calisan TAG'i kaydeder, compose up -d
#   4. Smoke test — backend /health + frontend /
#   5. Basarisizsa onceki TAG'e geri doner

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod.yml"
ENV_FILE=".env"
STATE_FILE=".deploy-last-tag"

err()  { printf '\033[31m[hata]\033[0m %s\n' "$*" >&2; }
info() { printf '\033[36m[bilgi]\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m[ok]\033[0m %s\n' "$*"; }

# --- argumanlar ------------------------------------------------------------
BUILD=0
RUN_TESTS=1
NEW_TAG=""

while [ $# -gt 0 ]; do
  case "$1" in
    --build)       BUILD=1 ;;
    --skip-tests)  RUN_TESTS=0 ;;
    -h|--help)     sed -n '2,12p' "$0"; exit 0 ;;
    -*)            err "bilinmeyen secenek: $1"; exit 1 ;;
    *)             NEW_TAG="$1" ;;
  esac
  shift
done

[ -n "$NEW_TAG" ] || { err "kullanim: scripts/deploy.sh [--build] <TAG>"; exit 1; }
[ -f "$ENV_FILE" ] || { err "$ENV_FILE yok. .env.example'dan kopyala."; exit 1; }

# REGISTRY degerini build/etiketleme icin bilmemiz gerek — .env'den oku.
set -a; . "./$ENV_FILE"; set +a
: "${REGISTRY:?REGISTRY degeri .env dosyasinda tanimli degil}"

BACKEND_IMAGE="${REGISTRY}/iodt2-backend:${NEW_TAG}"
FRONTEND_IMAGE="${REGISTRY}/iodt2-frontend:${NEW_TAG}"

# --- smoke test ------------------------------------------------------------
# Portlari host'a acmadigimiz icin testler container ICINDEN kosar.
smoke() {
  local tries=30
  info "smoke test..."
  while [ $tries -gt 0 ]; do
    # NOT: backend imajinda (python:3.11-slim) curl YOK, nginx:alpine'da da yok.
    # Her container'da GARANTI olan araci kullan.
    if $COMPOSE exec -T backend python -c \
         "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:3015/health', timeout=5).status==200 else 1)" >/dev/null 2>&1 \
    && $COMPOSE exec -T frontend wget -q -O /dev/null http://127.0.0.1/ >/dev/null 2>&1; then
      ok "smoke gecti"
      return 0
    fi
    tries=$((tries - 1))
    sleep 2
  done
  err "smoke test 60 sn icinde gecmedi"
  $COMPOSE ps
  $COMPOSE logs --tail=50 backend
  return 1
}

# --- imajlari hazirla ------------------------------------------------------
if [ "$BUILD" -eq 1 ]; then
  info "build: ${NEW_TAG}  (registry kullanilmiyor, imajlar bu makinede kaliyor)"
  docker build -t "$BACKEND_IMAGE"  ./backend
  docker build -t "$FRONTEND_IMAGE" ./frontend

  if [ "$RUN_TESTS" -eq 1 ]; then
    # Prod'a gidecek imajin TA KENDISINDE koser. Fuseki gerekmez —
    # testler bellek ici rdflib store kullanir (backend/tests/conftest.py).
    info "testler..."
    docker run --rm "$BACKEND_IMAGE" python -m pytest
    ok "testler gecti"
  else
    info "testler atlandi (--skip-tests)"
  fi
elif [ "$REGISTRY" = "local" ]; then
  # Imajlar bu makinede uretiliyor — cekilecek bir registry yok.
  # Rollback yolu: etiket daha once build edilmis olmali.
  for img in "$BACKEND_IMAGE" "$FRONTEND_IMAGE"; do
    docker image inspect "$img" >/dev/null 2>&1 || {
      err "imaj yok: ${img}"
      err "bu etiket bu makinede hic build edilmemis. Mevcutlar:"
      docker images 'local/iodt2-*' --format '  {{.Repository}}:{{.Tag}}' >&2
      err "yeni bir surum icin: scripts/deploy.sh --build ${NEW_TAG}"
      exit 1
    }
  done
  info "imajlar makinede mevcut: ${NEW_TAG}"
else
  info "pull: ${NEW_TAG}  (registry: ${REGISTRY})"
  TAG="$NEW_TAG" $COMPOSE pull
fi

# --- deploy ----------------------------------------------------------------
PREV_TAG=""
[ -f "$STATE_FILE" ] && PREV_TAG=$(cat "$STATE_FILE")

info "up -d: TAG=${NEW_TAG}"
TAG="$NEW_TAG" $COMPOSE up -d --remove-orphans

if smoke; then
  echo "$NEW_TAG" > "$STATE_FILE"
  ok "deploy tamam — TAG=${NEW_TAG}"
  exit 0
fi

# --- rollback --------------------------------------------------------------
if [ -z "$PREV_TAG" ] || [ "$PREV_TAG" = "$NEW_TAG" ]; then
  err "geri donulecek onceki TAG yok. Servisler bozuk halde — elle bak."
  exit 1
fi

err "rollback: TAG=${PREV_TAG}"
TAG="$PREV_TAG" $COMPOSE up -d --remove-orphans
if smoke; then
  err "rollback yapildi, calisan surum ${PREV_TAG}. ${NEW_TAG} basarisiz."
else
  err "rollback DA basarisiz. Elle mudahale gerekli."
fi
exit 1
