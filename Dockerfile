FROM python:3.11-slim as base


ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PATH=/venv/bin:$PATH
WORKDIR /app

RUN apt-get update

FROM base as builder

RUN apt-get install -y gcc libffi-dev g++

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.6.1

RUN pip install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

COPY . .
RUN . /venv/bin/activate && poetry install --without dev
RUN . /venv/bin/activate && poetry build

FROM base as final

COPY --from=builder /venv /venv
RUN --mount=type=bind,from=builder,source=/app/dist,target=. pip install *.whl

CMD ["python", "-m", "iopac2calendar"]
