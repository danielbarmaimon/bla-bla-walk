#!/usr/bin/env bash
# hack-guard: mandatory privacy and credential check. Blocks commits and pushes that
# would put secrets, personal data or local profile files on GitHub.
#
#   bash scripts/hack-guard.sh --staged   what you are about to commit (pre-commit hook)
#   bash scripts/hack-guard.sh --push     commits you are about to push (pre-push hook, reads stdin)
#   bash scripts/hack-guard.sh --all      whole repo and full history (CI, or manual audit)
#
# Private words (e.g. your real name) go one per line in
# .hack/private-terms.txt. That file is gitignored and never leaves your computer.
# Never bypass this check with --no-verify.

set -u
MODE="${1:---staged}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "hack-guard: not inside a git repo"; exit 1; }
cd "$ROOT" || exit 1

FAIL=0
REPORT=""
add() { REPORT="${REPORT}  - $1"$'\n'; FAIL=1; }

# Files that must never be committed, whatever their content (.env.example is allowed).
FORBIDDEN_PATHS='(^|/)\.env$|(^|/)\.env\.|(^|/)\.hack/|(^|/)profile\.md$|\.pem$|\.key$|\.p12$|\.pfx$|\.keystore$|(^|/)id_(rsa|dsa|ecdsa|ed25519)|(^|/)credentials(\.json)?$|(^|/)service[-_]?account[^/]*\.json$|(^|/)\.(npmrc|pypirc|netrc)$|(^|/)secrets?\.(json|ya?ml|toml|txt)$'

# Content patterns: credentials.
SECRET_PATTERNS=(
  'AKIA[0-9A-Z]{16}'                                   # AWS access key
  'sk-(proj-|ant-|svcacct-)?[A-Za-z0-9_-]{20,}'       # OpenAI / Anthropic style keys
  'gh[pousr]_[A-Za-z0-9]{30,}'                        # GitHub tokens
  'github_pat_[A-Za-z0-9_]{30,}'
  'xox[abprs]-[A-Za-z0-9-]{10,}'                      # Slack
  'AIza[0-9A-Za-z_-]{35}'                             # Google API key
  'hf_[A-Za-z0-9]{30,}'                               # Hugging Face
  'glpat-[A-Za-z0-9_-]{20,}'                          # GitLab
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  '(api[_-]?key|secret|passw(or)?d|token|auth)[A-Za-z_]*["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{8,}["'"'"']'
  '(postgres|postgresql|mysql|mongodb(\+srv)?|redis|amqp)://[^:/[:space:]]+:[^@/[:space:]]+@'
)

# Content patterns: personal data.
PERSONAL_PATTERNS=(
  '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'    # e-mail (noreply/example filtered below)
  '(\+41|0041)[ .]?[0-9]{2}[ .]?[0-9]{3}[ .]?[0-9]{2}[ .]?[0-9]{2}'   # Swiss phone
  '(^|[^0-9])07[5-9][ .]?[0-9]{3}[ .]?[0-9]{2}[ .]?[0-9]{2}([^0-9]|$)' # Swiss mobile, national format
  '756\.?[0-9]{4}\.?[0-9]{4}\.?[0-9]{2}'             # AHV / AVS number
  'CH[0-9]{2}[ ]?([0-9A-Z]{4}[ ]?){4}[0-9A-Z]'        # Swiss IBAN
)
EMAIL_OK='^git@|noreply|no-reply|example\.(com|org|ch)|users\.noreply\.github\.com|@anthropic\.com>?$'

# The guard itself contains the patterns; don't flag it.
SELF_SKIP='^(scripts/hack-guard\.(sh|ps1)|\.githooks/)'

# ---------- collect changed paths and added lines for the chosen mode ----------
PATHS=""
ADDED=""   # lines "path<TAB>content"

# Main worktree: in a linked worktree, .hack/ (profile, private word list) lives only there.
MAIN_WT="$(git worktree list --porcelain 2>/dev/null | sed -n '1s/^worktree //p')"
[ -z "$MAIN_WT" ] && MAIN_WT="$ROOT"

# Identity check for a range of commits: author AND committer e-mail must be noreply.
# Names are checked only locally (strict=1); on GitHub, web merges carry the account's
# public profile name, which is already public and outside this repo's control.
check_identities() {  # $1 = git log range args, $2 = strict names (1/0)
  local range="$1" strict="$2" line email name
  while IFS=$'\t' read -r email name; do
    [ -z "$email" ] && continue
    echo "$email" | grep -Eiq 'users\.noreply\.github\.com|noreply@' \
      || add "A commit carries a personal e-mail address ($email). Use your GitHub noreply address, see \$hack-guard."
    if [ "$strict" = "1" ] && echo "$name" | grep -q ' '; then
      add "A commit carries what looks like a real name ('$name'). Use your GitHub username as git name, see \$hack-guard."
    fi
  done <<< "$( { git log --format='%ae%x09%an' $range; git log --format='%ce%x09%cn' $range; } 2>/dev/null | sort -u )"
}

diff_to_added() { awk '/^\+\+\+ /{f=$2; sub(/^b\//,"",f); next} /^\+/{print f "\t" substr($0,2)}'; }

case "$MODE" in
  --staged)
    PATHS="$(git diff --cached --name-only --diff-filter=ACMR)"
    ADDED="$(git diff --cached -U0 --no-color --diff-filter=ACMR | diff_to_added)"
    ;;
  --push)
    Z=0000000000000000000000000000000000000000
    while read -r lref lsha rref rsha; do
      [ -z "${lsha:-}" ] && continue
      case "$lsha" in *[!0]*) ;; *) continue ;; esac     # branch deletion
      # A branch update may include commits already published on another remote
      # branch (for example, when merging main). Only audit commits not yet
      # reachable from any remote ref; those are the commits newly sent to GitHub.
      case "$rsha" in *[!0]*) RANGE="$rsha..$lsha --not --remotes" ;; *) RANGE="$lsha --not --remotes" ;; esac
      PATHS="$PATHS"$'\n'"$(git log --name-only --format= $RANGE)"
      ADDED="$ADDED"$'\n'"$(git log -p -U0 --no-color --format= $RANGE | diff_to_added)"
      check_identities "$RANGE" 1
    done
    ;;
  --all)
    PATHS="$(git ls-files; git log --all --name-only --format= | sort -u)"
    ADDED="$(git log --all -p -U0 --no-color --format= | diff_to_added)"
    ADDED="$ADDED"$'\n'"$(git ls-files -z | xargs -0 grep -HnI '' 2>/dev/null | sed -E 's/^([^:]+):[0-9]+:/\1\t/')"
    check_identities "--all" 0
    ;;
  *) echo "usage: hack-guard.sh --staged | --push | --all"; exit 2 ;;
esac

# ---------- identity of the committer (staged mode) ----------
if [ "$MODE" = "--staged" ]; then
  EMAIL="$(git config user.email || true)"
  NAME="$(git config user.name || true)"
  if [ -n "$EMAIL" ] && ! echo "$EMAIL" | grep -Eiq 'users\.noreply\.github\.com|noreply@'; then
    add "Your git e-mail ($EMAIL) would be published in every commit. Run: git config user.email <id+username>@users.noreply.github.com (find it in GitHub, Settings, Emails)."
  fi
  if echo "$NAME" | grep -q ' '; then
    add "Your git name ('$NAME') looks like a real name and would be published. Run: git config user.name <your-github-username>"
  fi
fi

# ---------- 0b. setup done on this computer? (not in CI) ----------
if [ "$MODE" != "--all" ]; then
  if [ ! -f "$ROOT/.hack/profile.md" ] && [ ! -f "$MAIN_WT/.hack/profile.md" ]; then
    add "Setup isn't done on this computer yet. Ask your assistant: \$hack-start (the quick path takes under a minute)."
  fi
fi

# ---------- 1. forbidden files ----------
while IFS= read -r p; do
  [ -z "$p" ] && continue
  [ "$p" = ".env.example" ] && continue
  if echo "$p" | grep -Eq "$FORBIDDEN_PATHS"; then
    add "File must stay local: $p"
  fi
done <<< "$(echo "$PATHS" | sort -u)"

# ---------- 2-4. content checks ----------
# Private word list: this worktree first, else the main worktree
TERMS_FILE="$ROOT/.hack/private-terms.txt"
[ -f "$TERMS_FILE" ] || TERMS_FILE="$MAIN_WT/.hack/private-terms.txt"
TAB="$(printf '\t')"
CANDIDATES="$(echo "$ADDED" | grep -Ev "$SELF_SKIP" | grep -v 'hack-guard:allow')"
check_lines() {
  local label="$1"; shift
  for pat in "$@"; do
    echo "$CANDIDATES" | grep -E -- "${TAB}.*$pat" | head -20 | while IFS="$TAB" read -r f content; do
      if [ "$label" = "personal data" ] && echo "$pat" | grep -q '@'; then
        echo "$content" | grep -Eo -- "$pat" | grep -Eiqv "$EMAIL_OK" || continue
      fi
      echo "Possible $label in ${f:-?}"
    done
  done
}
while IFS= read -r msg; do [ -n "$msg" ] && add "$msg"; done <<< "$(check_lines "credential" "${SECRET_PATTERNS[@]}"; check_lines "personal data" "${PERSONAL_PATTERNS[@]}")"

if [ -f "$TERMS_FILE" ]; then
  while IFS= read -r term; do
    term="$(echo "$term" | sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')"
    [ ${#term} -lt 3 ] && continue
    f="$(echo "$CANDIDATES" | grep -Fi -- "$term" | head -1 | cut -f1)"
    [ -n "$f" ] && add "A private term from your local list appears in $f"
  done < "$TERMS_FILE"
fi

# ---------- 5. .gitignore must protect local files ----------
for must in '.env' '.hack/'; do
  grep -Fxq "$must" <(tr -d '\r' < .gitignore) 2>/dev/null || add ".gitignore is missing the line: $must"
done

# ---------- result ----------
if [ "$FAIL" -ne 0 ]; then
  echo
  echo "hack-guard BLOCKED this ($MODE). Nothing was sent to GitHub."
  echo
  printf '%s' "$REPORT" | sort -u
  echo
  echo "Fix: remove the file from the commit (git restore --staged <file>), move secrets to .env,"
  echo "replace personal data with placeholders. Ask your assistant: \$hack-guard."
  echo "False alarm? Only a human decides: add 'hack-guard:allow' to that line after checking it."
  exit 1
fi
echo "hack-guard: ok ($MODE)"
exit 0
