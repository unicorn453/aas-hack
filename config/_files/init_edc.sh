#!/bin/sh

set -e

EDC_URL=http://edc-controlplane:19193
MANAGEMENT_PATH=/api/management
API_KEY=${EDC_API_KEY:-password}

echo "Waiting for EDC..."

while :; do
    # Probe a DB-backed management endpoint so we only continue once SQL stores are usable.
    status=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$EDC_URL$MANAGEMENT_PATH/v3/assets/request" \
        -H "Content-Type: application/json" \
        -H "X-Api-Key: $API_KEY" \
        -d '{"@context":{"@vocab":"https://w3id.org/edc/v0.0.1/ns/"},"@type":"QuerySpec","offset":0,"limit":1}' \
        --max-time 5 || true)

    case "$status" in
        2*|401|403)
            break
            ;;
    esac

    echo "EDC not ready yet (HTTP ${status:-n/a}), retrying..."
    sleep 2
done

echo "EDC is ready."

post_or_ok() {
    url="$1"
    payload="$2"
    max_retries="${EDC_INIT_MAX_RETRIES:-20}"
    retry_delay="${EDC_INIT_RETRY_DELAY:-3}"
    attempt=1

    while :; do
        code=$(curl -s -o /tmp/edc-init-response.txt -w "%{http_code}" \
            -X POST "$url" \
            -H "Content-Type: application/json" \
            -H "X-Api-Key: $API_KEY" \
            -d @"$payload" || true)

        if [ "$code" -ge 200 ] && [ "$code" -lt 300 ]; then
            return 0
        fi

        if [ "$code" = "409" ]; then
            echo "Already exists: $payload"
            return 0
        fi

        if [ "$code" -ge 500 ] && [ "$attempt" -lt "$max_retries" ]; then
            echo "Request got HTTP $code (attempt $attempt/$max_retries), retrying in ${retry_delay}s..."
            sleep "$retry_delay"
            attempt=$((attempt + 1))
            continue
        fi

        echo "Request failed ($code) for $url"
        echo "Payload: $payload"
        cat /tmp/edc-init-response.txt
        exit 1
    done
}

echo "Creating asset..."

post_or_ok "$EDC_URL$MANAGEMENT_PATH/v3/assets" /config/asset.json

echo "Creating policy..."

post_or_ok "$EDC_URL$MANAGEMENT_PATH/v3/policydefinitions" /config/policy.json

echo "Creating contract..."

post_or_ok "$EDC_URL$MANAGEMENT_PATH/v3/contractdefinitions" /config/contract.json

echo "Done."