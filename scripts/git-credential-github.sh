#!/bin/sh
# Git credential helper for GitHub (ComputerVision repo).
# Uses token from: (1) GIT_TOKEN env var, or (2) .git-credentials-token in repo root.
# Configure: git config credential.helper '!f() { sh /path/to/scripts/git-credential-github.sh "$@"; }; f'
# Create token at: https://github.com/settings/tokens (scope: repo)

get_token() {
	if [ -n "$GIT_TOKEN" ]; then
		echo "$GIT_TOKEN"
		return
	fi
	# Repo root: parent of scripts/
	root="$(cd "$(dirname "$0")/.." && pwd)"
	if [ -f "$root/.git-credentials-token" ]; then
		cat "$root/.git-credentials-token" | tr -d '\n\r'
	fi
}

case "$1" in
get)
	token=$(get_token)
	[ -z "$token" ] && exit 0
	host=""
	while read -r line; do
		[ -z "$line" ] && break
		case "$line" in host=*) host="${line#host=}"; break;; esac
	done
	[ "$host" != "github.com" ] && exit 0
	echo "username=masquerade83"
	echo "password=$token"
	;;
store|erase)
	# No-op
	;;
esac
