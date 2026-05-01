# FROM python:3.11-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libpq-dev \
#     libcairo2 \
#     pango1.0-tools \
#     libpango-1.0-0 \
#     libpangoft2-1.0-0 \
#     shared-mime-info \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt /app/

# RUN pip install --upgrade pip
# RUN pip install -r requirements.txt

# COPY . /app/

# CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]




FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    curl \
    postgresql-client \
    gettext \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]