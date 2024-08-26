ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PATH=/venv/bin:$PATH

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3

RUN apt-get update && apt-get install -y gcc libffi-dev g++
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
RUN pip install "poetry==$POETRY_VERSION" poetry-plugin-bundle
RUN --mount=type=bind,target=. poetry bundle venv /venv

FROM base AS final

ENV PORT=8080 \
    SLEEP_TIME=600 \
    ICS_FILE=/app/iopac.ics \
    ICS_PATH=/iopac.ics \
    CONFIG_FILE=/app/config.yaml \
    TIMEOUT=30

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "curl", "-f", "http://localhost:8080/health" ]

COPY --from=builder /venv /venv
CMD ["python", "-m", "iopac2calendar"]
