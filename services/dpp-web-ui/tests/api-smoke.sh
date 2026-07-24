#!/usr/bin/env sh
set -eu

API_BASE="${API_BASE:?Set API_BASE, for example https://192.168.1.100}"
USER_PASSWORD="${BASYX_USER_PASSWORD:?Set BASYX_USER_PASSWORD}"
ADMIN_PASSWORD="${BASYX_ADMIN_PASSWORD:?Set BASYX_ADMIN_PASSWORD}"
REALM="${KEYCLOAK_REALM:-basyx}"
CLIENT_ID="${KEYCLOAK_API_CLIENT_ID:-basyx-api}"
CLIENT_SECRET="${KEYCLOAK_API_CLIENT_SECRET:-basyx-api-secret}"
AAS_ID="https://example.org/aas/schunk/pgn-plus-p-64-1"
TIMESERIES_ID="https://example.org/submodels/schunk/pgn-plus-p-64-1/timeseries"

CURL_FLAGS="-fsS"
if [ "${CURL_INSECURE:-0}" = "1" ]; then
  CURL_FLAGS="$CURL_FLAGS -k"
fi

encode_id() {
  printf %s "$1" | base64 | tr '+/' '-_' | tr -d '=\n'
}

expect_status() {
  expected="$1"
  url="$2"
  token="${3:-}"
  if [ -n "$token" ]; then
    actual=$(curl $CURL_FLAGS -o /dev/null -w '%{http_code}' \
      -H "Authorization: Bearer $token" "$url" || true)
  else
    actual=$(curl $CURL_FLAGS -o /dev/null -w '%{http_code}' "$url" || true)
  fi
  if [ "$actual" != "$expected" ]; then
    echo "FAIL $url: expected $expected, got $actual" >&2
    exit 1
  fi
  echo "PASS $expected $url"
}

token_for() {
  username="$1"
  password="$2"
  curl $CURL_FLAGS \
    -X POST "$API_BASE/auth/realms/$REALM/protocol/openid-connect/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "grant_type=password" \
    --data-urlencode "client_id=$CLIENT_ID" \
    --data-urlencode "client_secret=$CLIENT_SECRET" \
    --data-urlencode "username=$username" \
    --data-urlencode "password=$password" |
    sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'
}

shell_id=$(encode_id "$AAS_ID")
timeseries_id=$(encode_id "$TIMESERIES_ID")

expect_status 200 "$API_BASE/public/shell-descriptors"
expect_status 200 "$API_BASE/public/shells/$shell_id"
expect_status 200 "$API_BASE/public/submodels"
expect_status 401 "$API_BASE/submodels/$timeseries_id"

user_token=$(token_for basyx-user "$USER_PASSWORD")
admin_token=$(token_for basyx-admin "$ADMIN_PASSWORD")
[ -n "$user_token" ] || { echo "FAIL no basyx-user token" >&2; exit 1; }
[ -n "$admin_token" ] || { echo "FAIL no basyx-admin token" >&2; exit 1; }

expect_status 403 "$API_BASE/submodels/$timeseries_id" "$user_token"
expect_status 200 "$API_BASE/submodels/$timeseries_id" "$admin_token"
