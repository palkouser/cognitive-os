FROM python:3.12-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b

COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --requirement /tmp/requirements.lock \
    && rm /tmp/requirements.lock \
    && groupadd --gid 10001 cogos \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin cogos \
    && mkdir /workspace \
    && chown 10001:10001 /workspace

USER 10001:10001
WORKDIR /workspace
CMD ["python", "--version"]
