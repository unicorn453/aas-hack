vault kv put secret/edc-transfer-proxy-token-signer-privatekey \
content="$(cat /vault/keys/transfer-private.pem)"

vault kv put secret/edc-transfer-proxy-token-verifier-publickey \
content="$(cat /vault/keys/transfer-public.pem)"