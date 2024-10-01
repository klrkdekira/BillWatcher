FROM python:3.12.5-bookworm

ENV UV_PYTHON_PREFERENCE=only-system
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /bin/uvx

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y curl libpq-dev \
    && apt-get install -y --no-install-recommends build-essential gcc libc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* 

ENV STREAMLIT_UI_HIDE_TOP_BAR=1
ENV STREAMLIT_SERVER_PORT=8000
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev 

CMD ["uv", "run", "streamlit", "run", "scripts/app.py"]
