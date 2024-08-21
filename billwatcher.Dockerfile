FROM python:3.12.5-alpine3.20 AS builder

WORKDIR /app

COPY . .

RUN apk add --no-cache curl \
    && apk add --no-cache postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && source $HOME/.cargo/env \
    && uv sync \
    && uvx --from build pyproject-build --installer uv

FROM python:3.12.5-alpine3.20 

ARG HTTP_PORT=80
ARG DEFAULT_DATABASE_URL

ENV DATABASE_URL=${DEFAULT_DATABASE_URL}

WORKDIR /app

EXPOSE 80

COPY --from=builder /app/dist/*whl .

RUN apk add --no-cache postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev \
    && apk add --no-cache curl \
    && pip install *.whl \
    && rm -rf /app/*.whl \
    && apk del --purge .build-deps

CMD ["python3", "-m", "sinar_billwatcher"]