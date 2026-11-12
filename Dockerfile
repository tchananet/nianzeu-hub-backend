FROM ghcr.io/astral-sh/uv:0.11.6 AS uv
FROM python:3.13-slim-bookworm AS runtime
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 PYTHONPATH=/opt/app PATH="/opt/app/.venv/bin:$PATH"
WORKDIR /opt/app
COPY pyproject.toml uv.lock ./
# Binary wheels include PyAV codecs; fail instead of compiling native sources.
RUN uv sync --locked --no-dev --no-install-project --no-build \
    && useradd --uid 10001 --no-create-home app
COPY app ./app
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--no-proxy-headers", "--no-access-log"]

FROM runtime AS test
USER root
RUN uv sync --locked --no-install-project --no-build
COPY tests ./tests
USER 10001:10001
CMD ["pytest", "-p", "no:cacheprovider"]
