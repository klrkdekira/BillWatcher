FROM python:3.12.5-bookworm

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /bin/uvx

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    apt-get update \
    && apt-get install -y curl libpq-dev \
    && apt-get install -y --no-install-recommends build-essential gcc libc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && uv sync --frozen --no-dev 

ENV STREAMLIT_UI_HIDE_TOP_BAR=1
ENV STREAMLIT_SERVER_PORT=8000
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["uv", "run", "streamlit", "run", "cli/app.py"]
