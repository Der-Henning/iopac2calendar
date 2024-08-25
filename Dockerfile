ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PATH=/venv/bin:$PATH
WORKDIR /app

RUN apt-get update && apt-get upgrade -y

FROM base AS builder
RUN apt-get install -y gcc libffi-dev g++

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3

RUN pip install "poetry==$POETRY_VERSION" poetry-plugin-bundle
RUN --mount=type=bind,target=. poetry bundle venv /venv

FROM base AS final
COPY --from=builder /venv /venv
CMD ["python", "-m", "iopac2calendar"]
