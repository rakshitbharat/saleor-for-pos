### Build and install packages
FROM python:3.12 AS build-python

RUN apt-get -y update \
  && apt-get install -y gettext \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
RUN pip install poetry==1.8.4
RUN poetry config virtualenvs.create false

# Copy the entire project first
COPY . .

# Install project and dependencies
RUN poetry install

### Final image
FROM python:3.12-slim

RUN groupadd -r saleor && useradd -r -g saleor saleor

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
COPY --from=build-python /app/ /app/
WORKDIR /app

# Install poetry and project
RUN pip install poetry==1.8.4 \
    && poetry config virtualenvs.create false \
    && poetry install

# Install development dependencies
RUN poetry add --group dev \
    django-debug-toolbar@4.2.0 \
    watchfiles@0.21.0 \
    "uvicorn[standard]@>=0.32.0,<0.33.0"

ARG STATIC_URL
ENV STATIC_URL=${STATIC_URL:-/static/} \
    PYTHONPATH=/app \
    SECRET_KEY="development-secret-key-123"

# Collect static files
USER root
RUN cd /app && SECRET_KEY="development-secret-key-123" python3 manage.py collectstatic --no-input
USER saleor

EXPOSE 8000
ENV PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=saleor.settings
