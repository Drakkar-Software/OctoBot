---
title: Security
description: OctoBot Node security — OS hardening, SSH lockdown, TLS configuration, container isolation, and nginx protections.
sidebar_position: 4
---

# Security

OctoBot Node applies security at multiple layers: the operating system, SSH access, Docker containers, and the nginx reverse proxy. Most protections are opt-in via the `enable_hardening` and `enable_nginx` flags, but container-level isolation is always active.

## OS hardening

When `enable_hardening` is true, the `devsec.hardening.os_hardening` role applies kernel-level protections: restrictive sysctl parameters, removal of SUID/SGID bits from unnecessary binaries, password policy enforcement, and core dump prevention. These settings follow the DevSec Hardening Framework, a widely-adopted baseline for Linux server security.

## SSH hardening

The same flag also enables `devsec.hardening.ssh_hardening`, which locks down the SSH daemon. Root login is disabled, password authentication is turned off in favor of public-key only, and forwarding features (TCP, agent, X11) are all disabled. Authentication attempts are limited to three retries.

These settings are controlled by variables that can be overridden in group vars, though the defaults represent a secure baseline:

```yaml
ssh_permit_root_login: "no"
ssh_server_password_login: false
ssh_max_auth_retries: 3
ssh_allow_tcp_forwarding: "no"
ssh_x11_forwarding: false
```

## Container isolation

All containers in the stack run with `no-new-privileges` set and all Linux capabilities dropped. This prevents privilege escalation within containers regardless of whether hardening is enabled.

Nginx is the only exception — it requires `CHOWN`, `SETUID`, `SETGID`, and `NET_BIND_SERVICE` capabilities to bind to ports 80 and 443 and manage its worker processes. These are the minimum capabilities needed for nginx to function.

The Tor proxy runs as a dedicated non-root `tor` user inside its container, further limiting the impact of any compromise.

## Firewall

The `geerlingguy.firewall` role manages iptables rules. The default policy opens only SSH (22), HTTP (80), and HTTPS (443), with all other inbound traffic dropped. Dropped packets are logged at a rate-limited 15 per minute for monitoring.

ICMP ping and NTP (UDP 123) are allowed for health checking and time synchronization. Established connections are always permitted.

In replica mode, port 5432 must be reachable from consumer nodes to the master. Add explicit rules in group vars:

```yaml
firewall_additional_rules:
  - "iptables -A INPUT -p tcp --dport 5432 -s 203.0.113.11 -j ACCEPT"
  - "iptables -A INPUT -p tcp --dport 5432 -s 203.0.113.12 -j ACCEPT"
```

## TLS

When nginx is enabled, the playbook generates a self-signed TLS certificate for each host using OpenSSL. The certificate is valid for ten years and uses the host's inventory name as the common name.

The nginx configuration enforces TLS 1.2 and 1.3 only, with server cipher preference enabled. For production deployments behind a CDN or load balancer, replace the self-signed certificate with one from your certificate authority.

## Nginx protections

The nginx template applies several security measures beyond TLS:

**Security headers** are set on all responses: `X-Frame-Options` (SAMEORIGIN), `X-Content-Type-Options` (nosniff), `X-XSS-Protection`, `Strict-Transport-Security` (two-year max-age with subdomains), `Referrer-Policy` (strict-origin-when-cross-origin), and a restrictive `Content-Security-Policy`. The `server_tokens` directive is off to suppress version disclosure.

**Rate limiting** uses a global zone of 50 requests per second per client IP. API routes allow a burst of 20 requests; web UI routes allow a burst of 50. Excess requests are rejected immediately (`nodelay`).

**HTTP to HTTPS redirect** is enforced — all requests on port 80 are 301-redirected to HTTPS, except the `/health` endpoint which returns 200 directly for load balancer probes.

**Path restriction** — when `expose_web_ui` is false, the root location returns 403, limiting the node to API-only access through nginx.

## Docker networking

Services communicate over isolated Docker networks. The `frontend` network connects all public-facing services. In replica mode, a separate `backend` network links OctoBot to PostgreSQL, keeping database traffic off the frontend. When Tor is enabled, a dedicated `tor_net` network isolates the proxy so only the OctoBot container can reach it.
