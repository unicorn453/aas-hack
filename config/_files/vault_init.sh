export VAULT_ADDR=http://127.0.0.1:8200

echo "Waiting for Vault to be ready..."
until vault status > /dev/null 2>&1; do
    sleep 1
done
echo "Vault is ready."

vault kv put secret/edc-transfer-proxy-token-signer-privatekey \
content="$(cat /vault/keys/transfer-private.pem)"

vault kv put secret/edc-transfer-proxy-token-verifier-publickey \
content="$(cat /vault/keys/transfer-public.pem)"

# OAuth client secrets referenced by *.secret.alias properties in EDC configs.
vault kv put secret/edc-control-plane-secret \
content="edc-control-plane-secret"

vault kv put secret/edc-dataplane-secret \
content="edc-dataplane-secret"