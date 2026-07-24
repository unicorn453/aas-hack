#!/bin/sh

set -e

EDC_URL=http://edc-controlplane:19193
MANAGEMENT_PATH=/api/management
API_KEY=${EDC_API_KEY:-password}

echo "Waiting for EDC..."

until status=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$EDC_URL$MANAGEMENT_PATH/v3/assets/request" \
        -H "Content-Type: application/json" \
        -H "X-Api-Key: $API_KEY" \
        -d '{}'); [ "$status" -lt 500 ] && [ "$status" -ne 000 ]; do
    sleep 2
done

echo "EDC is ready."

post_or_ok() {
    url="$1"
    payload="$2"

    code=$(curl -s -o /tmp/edc-init-response.txt -w "%{http_code}" \
        -X POST "$url" \
        -H "Content-Type: application/json" \
        -H "X-Api-Key: $API_KEY" \
        -d @"$payload")

    if [ "$code" -ge 200 ] && [ "$code" -lt 300 ]; then
        return 0
    fi

    if [ "$code" = "409" ]; then
        echo "Already exists: $payload"
        return 0
    fi

    echo "Request failed ($code) for $url"
    cat /tmp/edc-init-response.txt
    exit 1
}

echo "Creating asset..."

post_or_ok "$EDC_URL$MANAGEMENT_PATH/v3/assets" /config/asset.json

echo "Creating policy..."

post_or_ok "$EDC_URL$MANAGEMENT_PATH/v3/policydefinitions" /config/policy.json

echo "Creating contract..."

post_or_ok "$EDC_URL$MANAGEMENT_PATH/v3/contractdefinitions" /config/contract.json

echo "Done."