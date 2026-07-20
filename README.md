# USAGE

This is a simple example of how to run the server and client in a docker container.

```bash
docker compose up
```

## Open the UI: https://ip-address/

## Open the Keycloak admin dashboard: https://ip-address/auth

To stop and remove the container run:

```bash
docker compose down
```

Create a `certs/` directory and `server.crt` + `server.key` with the following commands:

```bash
mkdir -p ./certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
  -keyout ./certs/server.key \
  -out ./certs/server.crt \
  -subj "/CN=192.168.56.76" \
  -addext "subjectAltName=IP:192.168.56.76"
```
