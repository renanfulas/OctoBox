FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code

# Copia apenas requirements primeiro para aproveitar cache
COPY ../../requirements.txt /code/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt || true

# Copia todo o código
COPY . /code
