ARG BUILD_FROM
FROM ${BUILD_FROM}

COPY rootfs /
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
