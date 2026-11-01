#!/usr/bin/env bash
# UNO GitFlic read/backup utility. Existing GitFlic main is never changed.
set -euo pipefail
mode="$1"
case "$mode" in verify|backup) ;; *) echo "Expected verify or backup" >&2; exit 2 ;; esac
url="https://gitflic.ru/project/ivankondral/uno-andraid-ai-agent.git"
origin="$(git remote get-url origin)"
case "$origin" in
  https://github.com/ivankondral1998-dot/UNO-android-AI-Agent|https://github.com/ivankondral1998-dot/UNO-android-AI-Agent.git) ;;
  *) echo "Wrong GitHub origin; refusing to continue" >&2; exit 2 ;;
esac
if [[ -z "${UNO_GITFLIC_TOKEN:-}" ]]; then
  echo "UNO_GITFLIC_TOKEN is missing" >&2
  exit 2
fi
tmp="$(mktemp -d)"
chmod 700 "$tmp"
trap 'rm -rf -- "$tmp"' EXIT
cat > "$tmp/askpass" <<'END_ASKPASS'
#!/usr/bin/env bash
case "$1" in
  *Username*|*username*) printf '%s\n' "ivankondral" ;;
  *Password*|*password*) printf '%s\n' "$UNO_GITFLIC_TOKEN" ;;
  *) exit 1 ;;
esac
END_ASKPASS
chmod 700 "$tmp/askpass"
export GIT_ASKPASS="$tmp/askpass" GIT_TERMINAL_PROMPT=0
gitflic() { git -c credential.helper= "$@"; }
remote_hash() {
  local ref="$1"
  gitflic ls-remote "$url" "$ref" | awk -v wanted="$ref" '$2 == wanted {print $1}'
}
gitflic ls-remote --heads "$url" > /dev/null || { echo "GitFlic authentication failed" >&2; exit 1; }

count=0
missing=0
while IFS= read -r source; do
  [[ "$source" == "refs/remotes/origin/HEAD" ]] && continue
  name="$(printf '%s' "$source" | sed 's#^refs/remotes/origin/##')"
  [[ -n "$name" ]] || continue
  expected="$(git rev-parse "$source")"
  target="refs/heads/github/$name"
  actual="$(remote_hash "$target")"
  if [[ "$actual" != "$expected" && "$mode" == backup ]]; then
    echo "Backing up branch $name (non-force)"
    gitflic push "$url" "$source:$target"
    actual="$(remote_hash "$target")"
  fi
  if [[ "$actual" != "$expected" ]]; then
    echo "Branch not mirrored: $name" >&2
    missing=$((missing + 1))
  fi
  count=$((count + 1))
done < <(git for-each-ref --format='%(refname)' refs/remotes/origin)
if (( count == 0 )); then echo "No source branches" >&2; exit 1; fi

tag_count=0
while IFS= read -r source; do
  name="$(printf '%s' "$source" | sed 's#^refs/tags/##')"
  [[ -n "$name" ]] || continue
  expected="$(git rev-parse "$source")"
  target="refs/tags/github/$name"
  actual="$(remote_hash "$target")"
  if [[ "$actual" != "$expected" && "$mode" == backup ]]; then
    echo "Backing up tag $name (non-force)"
    gitflic push "$url" "$source:$target"
    actual="$(remote_hash "$target")"
  fi
  if [[ "$actual" != "$expected" ]]; then
    echo "Tag not mirrored: $name" >&2
    missing=$((missing + 1))
  fi
  tag_count=$((tag_count + 1))
done < <(git for-each-ref --format='%(refname)' refs/tags)

if (( missing > 0 )); then
  echo "Verification failed: $missing differences" >&2
  exit 1
fi
echo "Backed up $count GitHub branches and $tag_count tags with matching Git SHA."
gh_main="$(git rev-parse refs/remotes/origin/main)"
gf_main="$(remote_hash refs/heads/main)"
if [[ "$gh_main" == "$gf_main" ]]; then
  echo "GitFlic main matches GitHub main."
else
  echo "GitFlic main has independent history and was deliberately preserved."
  echo "Backup branches are available as github/* on GitFlic."
fi
