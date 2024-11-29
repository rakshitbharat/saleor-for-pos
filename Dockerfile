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

# Copy only pyproject.toml and poetry.lock first
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-root

# Now copy the rest of the code
COPY . .

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

ARG STATIC_URL
ENV STATIC_URL=${STATIC_URL:-/static/} \
    PYTHONPATH=/app

# Install runtime dependencies
RUN pip install uvicorn[standard]==0.27.1

# Collect static files
USER root
RUN PYTHONPATH=/app SECRET_KEY=dummy STATIC_URL=${STATIC_URL} python3 manage.py collectstatic --no-input
USER saleor

EXPOSE 8000
ENV PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=saleor.settings
