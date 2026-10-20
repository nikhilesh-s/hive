#!/usr/bin/env bash
# Build a public release zip from HEAD and verify it. Uploads nothing.
#
#   scripts/make_release_archive.sh VERSION      # e.g. 0.5.0 -> dist/hiveblot-0.5.0.zip
#
# Verifies that (1) no path matching an `export-ignore` line in .gitattributes
# is inside the zip and (2) the zip contents contain no secret-looking strings.
# Hits are printed with the value masked. Exit status is non-zero on any hit.
set -euo pipefail
export LC_ALL=C

VERSION="${1:?usage: $0 VERSION}"
[[ "$VERSION" =~ ^[0-9A-Za-z._-]+$ ]] || { echo "bad VERSION: $VERSION" >&2; exit 2; }

cd "$(git rev-parse --show-toplevel)"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "warning: working tree has uncommitted changes; the archive is built from HEAD only" >&2
fi

PREFIX="hiveblot-$VERSION/"
OUT="dist/hiveblot-$VERSION.zip"
mkdir -p dist
git archive --format=zip --prefix="$PREFIX" -o "$OUT" HEAD

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

# --- 1. nothing from the export-ignore list may be in the archive ------------
patterns=()
while read -r pat attrs; do
  if [[ "$attrs" == *export-ignore* && "$pat" != \#* ]]; then patterns+=("$pat"); fi
done < <(git show HEAD:.gitattributes)
if ((${#patterns[@]} == 0)); then
  echo "FAIL: no export-ignore patterns in HEAD:.gitattributes (commit it first)"; exit 1
fi

unzip -Z1 "$OUT" | sed "s#^$PREFIX##" | grep -v '^$' > "$TMP/entries.txt"   # files + dir entries
grep -v '/$' "$TMP/entries.txt" > "$TMP/files.txt"
while IFS= read -r path; do
  for pat in "${patterns[@]}"; do
    p="${pat#/}"                                   # leading / = root-anchored
    # shellcheck disable=SC2053  (glob match is intended; ** acts as * here)
    if [[ "$path" == $p ]] || [[ "$path" == $p/* ]] || { [[ "$pat" != */* ]] && [[ "${path##*/}" == $p ]]; }; then
      echo "FAIL export-ignore: $path (matches $pat)"; fail=1
    fi
  done
done < <(sed 's#/$##' "$TMP/entries.txt")

# --- 2. secret scan over the archive contents ---------------------------------
unzip -q "$OUT" -d "$TMP/x"
mask() { awk '{ n = length($0); if (n > 8) print substr($0, 1, 4) "...[" n " chars masked]"; else print "[masked]" }'; }

# Project refs are assembled from pieces so this script does not match itself.
BETA_REF="zafombwswz""tvnjikcsdm"
LEGACY_REF="belalrbfrn""dxvdwvjxte"

scan() { # label ERE
  { grep -rIEno -e "$2" "$TMP/x" || true; } | while IFS=: read -r f l m; do
    printf 'HIT %-14s %s:%s  %s\n' "$1" "${f#"$TMP"/x/}" "$l" "$(mask <<<"$m")"
  done
}

hits="$(
  scan anthropic-key 'sk-ant-[A-Za-z0-9]'
  scan aws-key       'AKIA[0-9A-Z]{16}'
  scan jwt           'eyJhbGciOi[A-Za-z0-9_-]{5,}'
  scan supabase-ref  "$BETA_REF|$LEGACY_REF"
)"

# postgres(ql)://user:pass@host with a real-looking password on a non-local host
scan_pg() {
  { grep -rIEno -e "postgres(ql)?://[^:/@[:space:]'\"]+:[^@[:space:]'\"]+@[^[:space:]'\"/]+" "$TMP/x" || true; } |
  while IFS=: read -r f l m; do
    cred="${m#*://}"; user="${cred%%:*}"; rest="${cred#*:}"; pass="${rest%%@*}"; host="${rest#*@}"
    shopt -s nocasematch
    case "$host" in localhost*|127.0.0.1*|'[::1]'*) continue ;; esac   # local dev DB
    case "$pass" in                                                   # documented placeholders
      '<'*'>'|'['*']'|'$'*|'{'*'}'|x|xx|xxx|xxxx|test|stub|password|pass|postgres|changeme|your*|...) continue ;;
    esac
    printf 'HIT %-14s %s:%s  postgres://%s:[masked]@%s\n' postgres-cred "${f#"$TMP"/x/}" "$l" "$user" "$host"
  done
}
pg="$(scan_pg)"
hits="$(printf '%s\n%s\n' "$hits" "$pg" | sed '/^$/d')"

if [[ -n "$hits" ]]; then
  printf '%s\n' "$hits"
  fail=1
fi

# --- summary --------------------------------------------------------------------
echo "archive: $OUT"
echo "size:    $(du -h "$OUT" | cut -f1) ($(wc -c < "$OUT" | tr -d ' ') bytes)"
echo "files:   $(wc -l < "$TMP/files.txt" | tr -d ' ')"
if ((fail)); then
  echo "RESULT:  FAIL (see above)"; exit 1
fi
echo "RESULT:  OK (no export-ignore paths, no secret hits)"
