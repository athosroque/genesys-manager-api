FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# .dockerignore impede .env, JSONs com PII, .db e scripts de consulta na imagem
COPY . .
# uid 1000 = dono de users.json/auth_tokens.json montados do host
RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin app
USER app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--proxy-headers"]
