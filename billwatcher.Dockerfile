FROM python:3.12.5-alpine3.20 AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /bin/uvx

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    apk add --no-cache curl postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev \
    && uv sync --frozen --no-dev \
    && uvx --from build pyproject-build --installer uv
#     && uv sync --frozen --no-dev 

# ENV STREAMLIT_UI_HIDE_TOP_BAR=1
# ENV STREAMLIT_SERVER_PORT=8000
# ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# CMD ["uv", "run", "streamlit", "run", "cli/app.py"]

FROM python:3.12.5-alpine3.20 

ARG HTTP_PORT=80
ARG DEFAULT_DATABASE_URL

ENV DATABASE_URL=${DEFAULT_DATABASE_URL}

WORKDIR /app

EXPOSE 80

COPY --from=builder /app/dist/*whl .

RUN apk add --no-cache postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev \
    && pip install *.whl \
    && rm -rfv /app/*.whl \
    && apk del --purge .build-deps

CMD ["python3", "-m", "sinar_billwatcher"]