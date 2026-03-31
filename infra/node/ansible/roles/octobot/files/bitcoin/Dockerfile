FROM alpine:3.21@sha256:c3f8e73fdb79deaebaa2037150150191b9dcbfba68b4a46d70103204c53f4709

ARG BITCOIN_VERSION=28.1
ARG BITCOIN_HASH=7fe294b02b25e09c4f2516c8cc3fa57a6407945c86e01a9e3744d4760a6839a1

RUN apk add --no-cache wget ca-certificates && \
    adduser -D -h /home/bitcoin bitcoin && \
    wget -qO /tmp/bitcoin.tar.gz \
      "https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}/bitcoin-${BITCOIN_VERSION}-x86_64-linux-gnu.tar.gz" && \
    echo "${BITCOIN_HASH}  /tmp/bitcoin.tar.gz" | sha256sum -c && \
    tar xzf /tmp/bitcoin.tar.gz -C /tmp && \
    cp /tmp/bitcoin-${BITCOIN_VERSION}/bin/bitcoind /usr/local/bin/ && \
    cp /tmp/bitcoin-${BITCOIN_VERSION}/bin/bitcoin-cli /usr/local/bin/ && \
    rm -rf /tmp/bitcoin* && \
    apk del wget

VOLUME ["/home/bitcoin/.bitcoin"]
EXPOSE 8332 8333

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD bitcoin-cli -rpcconnect=127.0.0.1 getblockchaininfo || exit 1

USER bitcoin

ENTRYPOINT ["bitcoind"]
