#!/usr/bin/env bash
#
# bbsync — GitHub (tam gecmis) -> Bitbucket (gecmissiz ayna) senkronizasyonu.
#
# GitHub kaynaktir. Bitbucket'a commit'ler tek tek YENIDEN yazilir: ayni tree,
# JIRA key ile oneklenmis mesaj, ayri bir kok (orphan) uzerinde. Calisma dizinine
# dokunulmaz — checkout, stash, branch degistirme yok.
#
# Kullanim:
#   scripts/bbsync.sh setup <JIRA-KEY>   # bir kez: ayarlari yaz
#   scripts/bbsync.sh init               # bir kez: Bitbucket trunk'ini tek commit ile baslat
#   scripts/bbsync.sh status             # ne aktarilacak, goster
#   scripts/bbsync.sh push               # GitHub'a push + Bitbucket'a ayna
#   scripts/bbsync.sh mirror             # sadece Bitbucket'a ayna (GitHub'a dokunma)
#   scripts/bbsync.sh rebuild            # aynayi sifirdan kur (gecmis yeniden yazildiysa)
#
set -euo pipefail

cfg() { git config --get "$1" 2>/dev/null || printf '%s' "${2-}"; }

GH_REMOTE=$(cfg mirror.githubRemote origin)
BB_REMOTE=$(cfg mirror.bitbucketRemote bitbucket)
SRC_BRANCH=$(cfg mirror.sourceBranch main)
BB_BRANCH=$(cfg mirror.bitbucketBranch main)
JIRA_KEY=${MIRROR_JIRA_KEY:-$(cfg mirror.jiraKey '')}
MODE=$(cfg mirror.mode mirror)          # mirror | snapshot
ROOT_MSG=$(cfg mirror.initMessage 'Initial import from internal repository')

BB_REF="refs/mirror/bb/${BB_BRANCH}"    # Bitbucket tarafindaki ayna head'i
SRC_REF="refs/mirror/src/${SRC_BRANCH}" # en son aynalanan kaynak commit

die()  { printf 'hata: %s\n' "$*" >&2; exit 1; }
info() { printf '  . %s\n' "$*"; }
ok()   { printf '  + %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }

require_clean() {
  git diff --quiet && git diff --cached --quiet \
    || die "calisma dizini kirli. Once commit'le veya stash'le."
}

resolve_src() {
  git rev-parse --verify --quiet "refs/heads/${SRC_BRANCH}" >/dev/null \
    || die "kaynak branch '${SRC_BRANCH}' yok. 'git config mirror.sourceBranch <branch>' ile degistir."
}

# Herhangi bir JIRA anahtari: ABC-123
JIRA_RE='[A-Z][A-Z0-9]+-[0-9]+'

# Bitbucket icin commit mesaji: JIRA key oneki + kaynak izi.
# Mesajda zaten bir JIRA anahtari varsa (or. "fix: IODT-456 ...") dokunulmaz.
bb_message() {
  local src=$1 msg
  msg=$(git log -1 --pretty=%B "$src")
  if [ -n "$JIRA_KEY" ] && ! printf '%s' "$msg" | grep -qE "(^|[^A-Za-z0-9-])${JIRA_RE}([^A-Za-z0-9-]|$)"; then
    msg="${JIRA_KEY} ${msg}"
  fi
  printf '%s\n\nSource-Commit: %s\n' "$msg" "$(git rev-parse "$src")"
}

# snapshot modu: tek commit, kapsadigi tum commit'lerin ozetiyle
bb_snapshot_message() {
  local last=$1 head=$2 subject
  subject="Sync ${SRC_BRANCH} @ $(git rev-parse --short "$head")"
  if [ -n "$JIRA_KEY" ]; then subject="${JIRA_KEY} ${subject}"; fi
  printf '%s\n\n' "$subject"
  git log --reverse --first-parent --pretty='- %s' "${last}..${head}"
  printf '\nSource-Commit: %s\n' "$(git rev-parse "$head")"
}

# tree + parent + kaynak commit [+ hazir mesaj] -> yeni Bitbucket commit'i.
# Yazar/tarih kaynak commit'ten korunur. Mesaj stdin uzerinden verilir:
# Git Bash/Windows'ta <(...) sureclerarasi acilmiyor.
make_commit() {
  local tree=$1 parent=${2:-} src=$3 msg=${4:-}
  local args=("$tree")
  if [ -n "$parent" ]; then args+=(-p "$parent"); fi
  if [ -z "$msg" ]; then msg=$(bb_message "$src"); fi
  printf '%s\n' "$msg" | \
  GIT_AUTHOR_NAME=$(git log -1 --pretty=%an "$src") \
  GIT_AUTHOR_EMAIL=$(git log -1 --pretty=%ae "$src") \
  GIT_AUTHOR_DATE=$(git log -1 --pretty=%aI "$src") \
  GIT_COMMITTER_NAME=$(git log -1 --pretty=%cn "$src") \
  GIT_COMMITTER_EMAIL=$(git log -1 --pretty=%ce "$src") \
  GIT_COMMITTER_DATE=$(git log -1 --pretty=%cI "$src") \
    git commit-tree "${args[@]}" -F -
}

check_jira() {
  if [ -z "$JIRA_KEY" ]; then
    warn "JIRA key tanimli degil — Bitbucket hook'u push'u reddedebilir."
    warn "  scripts/bbsync.sh setup IODT-123"
  fi
}

# JIRA anahtari opsiyoneldir: verilmezse mesajlar oldugu gibi gonderilir.
cmd_setup() {
  local key=${1:-}
  if [ -n "$key" ]; then
    git config mirror.jiraKey "$key"
  else
    git config --unset mirror.jiraKey 2>/dev/null || true
  fi
  git config mirror.githubRemote "$GH_REMOTE"
  git config mirror.bitbucketRemote "$BB_REMOTE"
  git config mirror.sourceBranch "$SRC_BRANCH"
  git config mirror.bitbucketBranch "$BB_BRANCH"
  git config mirror.mode "$MODE"
  ok "ayarlar yazildi (.git/config -> [mirror])"
  git config --get-regexp '^mirror\.' | sed 's/^/    /'
}

cmd_init() {
  resolve_src
  check_jira
  if git rev-parse --verify --quiet "$BB_REF" >/dev/null; then
    die "ayna zaten kurulu ($BB_REF). Sifirlamak icin: bbsync.sh rebuild"
  fi
  if [ -n "$(GIT_TERMINAL_PROMPT=0 git ls-remote --heads "$BB_REMOTE" "$BB_BRANCH" 2>/dev/null)" ]; then
    die "$BB_REMOTE/$BB_BRANCH zaten dolu. Elle temizle ya da mirror.bitbucketBranch'i degistir."
  fi

  local head tree root
  head=$(git rev-parse "$SRC_BRANCH")
  tree=$(git rev-parse "${SRC_BRANCH}^{tree}")
  root=$(GIT_AUTHOR_NAME=$(git log -1 --pretty=%an "$head") \
         GIT_AUTHOR_EMAIL=$(git log -1 --pretty=%ae "$head") \
         GIT_COMMITTER_NAME=$(git log -1 --pretty=%cn "$head") \
         GIT_COMMITTER_EMAIL=$(git log -1 --pretty=%ce "$head") \
         git commit-tree "$tree" -m "${JIRA_KEY:+$JIRA_KEY }${ROOT_MSG}")

  info "kok commit: ${root:0:8}  (tree: ${tree:0:8}, ${SRC_BRANCH} @ ${head:0:8})"
  git push "$BB_REMOTE" "${root}:refs/heads/${BB_BRANCH}"
  git update-ref "$BB_REF" "$root"
  git update-ref "$SRC_REF" "$head"
  ok "Bitbucket trunk'i kuruldu -> ${BB_REMOTE}/${BB_BRANCH}"
  if [ "$MODE" = snapshot ]; then
    ok "her 'push' bundan sonra tek bir ozet commit ekleyecek."
  else
    ok "bundan sonraki commit'ler tek tek aynalanacak."
  fi
}

pending() {
  local last
  last=$(git rev-parse --verify --quiet "$SRC_REF" || true)
  [ -n "$last" ] || return 1
  git rev-list --reverse --first-parent "${last}..refs/heads/${SRC_BRANCH}"
}

cmd_status() {
  resolve_src
  local last bb list
  last=$(git rev-parse --verify --quiet "$SRC_REF" || true)
  bb=$(git rev-parse --verify --quiet "$BB_REF" || true)
  [ -n "$last" ] || die "ayna kurulu degil. Once: bbsync.sh init"
  printf 'kaynak   : %s @ %s\n' "$SRC_BRANCH" "$(git rev-parse --short "$SRC_BRANCH")"
  printf 'son ayna : %s -> %s\n' "${last:0:8}" "${bb:0:8}"
  printf 'JIRA key : %s\n' "${JIRA_KEY:-<yok>}"
  printf 'mod      : %s\n\n' "$MODE"
  list=$(pending || true)
  if [ -z "$list" ]; then echo "aktarilacak commit yok."; return; fi
  echo "aktarilacak:"
  while read -r c; do
    [ -n "$c" ] || continue
    printf '  %s  %s\n' "${c:0:8}" "$(bb_message "$c" | head -1)"
  done <<< "$list"
}

cmd_mirror() {
  resolve_src
  check_jira
  local last bb head tip n c
  last=$(git rev-parse --verify --quiet "$SRC_REF" || true)
  bb=$(git rev-parse --verify --quiet "$BB_REF" || true)
  { [ -n "$last" ] && [ -n "$bb" ]; } || die "ayna kurulu degil. Once: bbsync.sh init"

  if ! git merge-base --is-ancestor "$last" "refs/heads/${SRC_BRANCH}"; then
    die "kaynak gecmisi yeniden yazilmis (${last:0:8} artik ${SRC_BRANCH} atasi degil). Aynayi sifirla: bbsync.sh rebuild"
  fi

  head=$(git rev-parse "$SRC_BRANCH")
  if [ "$head" = "$last" ]; then ok "Bitbucket zaten guncel."; return; fi

  tip=$bb
  n=0
  if [ "$MODE" = snapshot ]; then
    tip=$(make_commit "$(git rev-parse "${SRC_BRANCH}^{tree}")" "$tip" "$head" \
          "$(bb_snapshot_message "$last" "$head")")
    [ -n "$tip" ] || die "commit-tree basarisiz oldu."
    n=1
  else
    for c in $(pending); do
      tip=$(make_commit "$(git rev-parse "${c}^{tree}")" "$tip" "$c")
      [ -n "$tip" ] || die "commit-tree basarisiz oldu (${c:0:8})."
      n=$((n+1))
      printf '  %s -> %s  %s\n' "${c:0:8}" "${tip:0:8}" "$(git log -1 --pretty=%s "$c")"
    done
  fi

  info "${n} commit aynalandi, push ediliyor..."
  git push "$BB_REMOTE" "${tip}:refs/heads/${BB_BRANCH}"   # push basarisizsa ref'ler ilerlemez
  git update-ref "$BB_REF" "$tip"
  git update-ref "$SRC_REF" "$head"
  ok "Bitbucket guncel -> ${BB_REMOTE}/${BB_BRANCH} @ ${tip:0:8}"
}

cmd_push() {
  resolve_src
  require_clean
  info "GitHub'a push: ${GH_REMOTE}/${SRC_BRANCH}"
  git push "$GH_REMOTE" "${SRC_BRANCH}"
  cmd_mirror
}

cmd_rebuild() {
  resolve_src
  local a head tree root
  warn "Bitbucket gecmisi TAMAMEN silinip tek kok commit'ten yeniden kurulacak."
  printf 'Devam? (yes/hayir) '
  read -r a
  [ "$a" = yes ] || die "iptal edildi."
  git update-ref -d "$BB_REF" 2>/dev/null || true
  git update-ref -d "$SRC_REF" 2>/dev/null || true
  head=$(git rev-parse "$SRC_BRANCH")
  tree=$(git rev-parse "${SRC_BRANCH}^{tree}")
  root=$(git commit-tree "$tree" -m "${JIRA_KEY:+$JIRA_KEY }${ROOT_MSG}")
  git push --force "$BB_REMOTE" "${root}:refs/heads/${BB_BRANCH}"
  git update-ref "$BB_REF" "$root"
  git update-ref "$SRC_REF" "$head"
  ok "ayna sifirlandi -> ${root:0:8}"
}

case "${1:-}" in
  setup)   shift; cmd_setup "$@" ;;
  init)    cmd_init ;;
  status)  cmd_status ;;
  mirror)  cmd_mirror ;;
  push|"") cmd_push ;;
  rebuild) cmd_rebuild ;;
  *)       die "bilinmeyen komut '$1'. setup|init|status|push|mirror|rebuild" ;;
esac
