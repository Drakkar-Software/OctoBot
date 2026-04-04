FROM debian:bookworm-slim

ARG BITCOIN_VERSION=28.1
ARG BITCOIN_HASH=07f77afd326639145b9ba9562912b2ad2ccec47b8a305bd075b4f4cb127b7ed7

RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates && \
    useradd -m -d /home/bitcoin bitcoin && \
    mkdir -p /home/bitcoin/.bitcoin && \
    chown bitcoin:bitcoin /home/bitcoin/.bitcoin && \
    wget -qO /tmp/bitcoin.tar.gz \
      "https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}/bitcoin-${BITCOIN_VERSION}-x86_64-linux-gnu.tar.gz" && \
    echo "${BITCOIN_HASH}  /tmp/bitcoin.tar.gz" | sha256sum -c && \
    tar xzf /tmp/bitcoin.tar.gz -C /tmp && \
    cp /tmp/bitcoin-${BITCOIN_VERSION}/bin/bitcoind /usr/local/bin/ && \
    cp /tmp/bitcoin-${BITCOIN_VERSION}/bin/bitcoin-cli /usr/local/bin/ && \
    rm -rf /tmp/bitcoin* && \
    apt-get purge -y wget && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

VOLUME ["/home/bitcoin/.bitcoin"]
EXPOSE 8332 8333

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD bitcoin-cli -rpcconnect=127.0.0.1 getblockchaininfo || exit 1

USER bitcoin

ENTRYPOINT ["bitcoind"]
