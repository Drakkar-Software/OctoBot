#!/usr/bin/env bash
set -euo pipefail

DAYS_VALID=180
KEY_SIZE=4096
DIGEST="-sha384"

SERVER_CN="redis.local"
ALT_NAMES="DNS:redis,DNS:redis.local,DNS:localhost,IP:127.0.0.1"
APP_CLIENT_CN="redis-app-client-01"

BASE_DIR="./certs"
CLIENT_DIR="${BASE_DIR}/client"
mkdir -p "${BASE_DIR}" "${CLIENT_DIR}"

echo "Generating CA certificate..."
openssl genrsa -out "${BASE_DIR}/ca.key" ${KEY_SIZE} 2>/dev/null

openssl req -new -x509 -nodes ${DIGEST} \
    -key    "${BASE_DIR}/ca.key" \
    -days   $((DAYS_VALID + 365)) \
    -out    "${BASE_DIR}/ca.crt" \
    -subj   "/C=XX/ST=Local/O=Redis Local CA/CN=Redis Local Root CA" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    2>/dev/null

echo "Generating server certificate..."
openssl genrsa -out "${BASE_DIR}/redis.key" ${KEY_SIZE} 2>/dev/null

openssl req -new -nodes ${DIGEST} \
    -key    "${BASE_DIR}/redis.key" \
    -subj   "/C=XX/ST=Local/O=Redis/CN=${SERVER_CN}" \
    -out    "${BASE_DIR}/redis.csr" 2>/dev/null

cat > "${BASE_DIR}/server-extensions.cnf" <<EOF
basicConstraints        = critical, CA:FALSE
keyUsage                = critical, digitalSignature, keyEncipherment
extendedKeyUsage        = serverAuth
subjectAltName          = ${ALT_NAMES}
EOF

openssl x509 -req ${DIGEST} \
    -in         "${BASE_DIR}/redis.csr" \
    -CA         "${BASE_DIR}/ca.crt" \
    -CAkey      "${BASE_DIR}/ca.key" \
    -CAcreateserial \
    -out        "${BASE_DIR}/redis.crt" \
    -days       ${DAYS_VALID} \
    -extfile    "${BASE_DIR}/server-extensions.cnf" 2>/dev/null

rm -f "${BASE_DIR}/redis.csr" "${BASE_DIR}/server-extensions.cnf"
chmod 600 "${BASE_DIR}/redis.key" "${BASE_DIR}/ca.key"

echo "Generating application client certificate..."
openssl genrsa -out "${CLIENT_DIR}/client.key" ${KEY_SIZE} 2>/dev/null

openssl req -new -nodes ${DIGEST} \
    -key    "${CLIENT_DIR}/client.key" \
    -subj   "/C=XX/ST=Local/O=Redis Clients/CN=${APP_CLIENT_CN}" \
    -out    "${CLIENT_DIR}/client.csr" 2>/dev/null

cat > "${CLIENT_DIR}/client-extensions.cnf" <<EOF
basicConstraints        = CA:FALSE
keyUsage                = critical, digitalSignature, keyEncipherment
extendedKeyUsage        = clientAuth
subjectKeyIdentifier    = hash
authorityKeyIdentifier  = keyid
EOF

openssl x509 -req ${DIGEST} \
    -in         "${CLIENT_DIR}/client.csr" \
    -CA         "${BASE_DIR}/ca.crt" \
    -CAkey      "${BASE_DIR}/ca.key" \
    -CAcreateserial \
    -out        "${CLIENT_DIR}/client.crt" \
    -days       $((DAYS_VALID - 30)) \
    -extfile    "${CLIENT_DIR}/client-extensions.cnf" 2>/dev/null

rm -f "${CLIENT_DIR}/client.csr" "${CLIENT_DIR}/client-extensions.cnf"
chmod 600 "${CLIENT_DIR}/client.key"

echo "Certificates generated successfully inside ${BASE_DIR}"
