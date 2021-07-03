ARG OCTOBOT_IMAGE
FROM $OCTOBOT_IMAGE

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

ENV CYTHON_IGNORE=true

COPY dev_requirements.txt .
COPY tests tests
RUN pip freeze && pip install --prefer-binary -r dev_requirements.txt

ENTRYPOINT ["./tests/docker-entrypoint.sh"]
