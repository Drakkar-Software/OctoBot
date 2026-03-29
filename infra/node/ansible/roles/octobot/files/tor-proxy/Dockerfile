FROM alpine:3.21@sha256:c3f8e73fdb79deaebaa2037150150191b9dcbfba68b4a46d70103204c53f4709

RUN apk add --no-cache tor netcat-openbsd && \
    echo "SocksPort 0.0.0.0:9050" > /etc/tor/torrc

EXPOSE 9050

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD nc -z 127.0.0.1 9050

VOLUME ["/var/lib/tor"]

USER tor

CMD ["tor"]
