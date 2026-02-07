# OctoBot-Node - Redis Setup

## Quick Start

```bash
# 1. Generate certificates
./generate-redis-tls.sh --with-client

# 2. Create a strong redis password
echo -n 'REDIS_PASSWORD=YOUR_REDIS_STRONG_PASSWORD' > .env

# 3. Start
docker compose up -d
```

Then update the `.env` file in your OctoBot-Node directory with the following:
```
SCHEDULER_REDIS_URL="rediss://default:YOUR_REDIS_STRONG_PASSWORD@YOUR_REDIS_HOST:YOUR_REDIS_PORT/0"
```
*Default redis port is 6379*

## Security

This configuration:
- Plain TCP completely disabled
- TLS 1.2 + TLS 1.3 only
- Strong **forward-secrecy** + **AEAD** ciphers only (GCM & ChaCha20-Poly1305)
- Mutual TLS (mTLS) support – client certificate required
- Certificates mounted read-only
- AOF + periodic RDB persistence
