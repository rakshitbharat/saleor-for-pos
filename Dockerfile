### Build and install packages
FROM python:3.12 AS build-python

RUN apt-get -y update \
  && apt-get install -y gettext \
  # Cleanup apt cache
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip pip install poetry==1.8.4
RUN poetry config virtualenvs.create false
COPY poetry.lock pyproject.toml /app/
RUN --mount=type=cache,mode=0755,target=/root/.cache/pypoetry poetry install --no-root

### Final image
FROM python:3.12-slim

RUN groupadd -r saleor && useradd -r -g saleor saleor

# Pillow dependencies
RUN apt-get update \
  && apt-get install -y \
  libffi8 \
  libgdk-pixbuf2.0-0 \
  liblcms2-2 \
  libopenjp2-7 \
  libssl3 \
  libtiff6 \
  libwebp7 \
  libpq5 \
  shared-mime-info \
  mime-support \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/media /app/static \
  && chown -R saleor:saleor /app/

COPY --from=build-python /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=build-python /usr/local/bin/ /usr/local/bin/
COPY . /app
WORKDIR /app

ARG STATIC_URL
ENV STATIC_URL=${STATIC_URL:-/static/}
RUN SECRET_KEY=dummy STATIC_URL=${STATIC_URL} python3 manage.py collectstatic --no-input

EXPOSE 8000
# Environment variables for development
ENV PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=saleor.settings

LABEL org.opencontainers.image.title="saleor/saleor" \
      org.opencontainers.image.description="A modular, high performance, headless e-commerce platform built with Python, GraphQL, Django, and ReactJS." \
      org.opencontainers.image.url="https://saleor.io/" \
      org.opencontainers.image.source="https://github.com/saleor/saleor" \
      org.opencontainers.image.authors="Saleor Commerce (https://saleor.io)" \
      org.opencontainers.image.licenses="BSD 3"

RUN pip install uvicorn[standard] watchfiles

# Install development tools with specific versions
RUN pip install \
    watchfiles==0.21.0 \
    uvicorn[standard]==0.27.1 \
    python-dotenv==1.0.0 \
    debugpy==1.8.0 \
    django-debug-toolbar==4.2.0

# Remove any existing .pyc files and __pycache__ directories
RUN find /app -type f -name "*.pyc" -delete && \
    find /app -type d -name "__pycache__" -delete

USER saleor
