# vpa-engine: Volume Price Analysis (Anna Coulling)
# Slim production image with all VPA rules and CLI.
#
# Build:
#   make build
#
# Run (single command):
#   docker run --env-file .env -v $(pwd)/data:/app/data vpa-engine scan
#   docker run --env-file .env -v $(pwd)/data:/app/data vpa-engine backtest
#
# Run (live paper trading):
#   docker run -d --env-file .env -v $(pwd)/data:/app/data \
#     --name vpa-spy vpa-engine paper --live
#
# Per-symbol override (mount a config):
#   docker run --env-file .env \
#     -v $(pwd)/data:/app/data \
#     -v $(pwd)/config-QQQ.yaml:/app/config.yaml:ro \
#     vpa-engine paper --live

FROM python:3.12-slim

ARG VERSION=dev
ARG GIT_SHA=unknown

LABEL maintainer="vpa-engine"
LABEL description="Volume Price Analysis engine — deterministic, explainable signals"
LABEL org.opencontainers.image.version=$VERSION
LABEL org.opencontainers.image.revision=$GIT_SHA

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src/ src/

RUN pip install --no-cache-dir ".[data]" \
    && rm -rf /root/.cache/pip

COPY config.example.yaml config.yaml
COPY docs/config/ docs/config/

RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

VOLUME ["/app/data"]

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD ["vpa", "health"]

ENTRYPOINT ["vpa"]
CMD ["--help"]
