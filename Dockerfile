FROM python:3.12.8

# .pyc vai direto pro cache e aumenta eficiencia
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependencias (--no-install-recommends pra ficar mais leve)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copia código pro container
COPY . /app/

# Baixa dependencias
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Healthcheck
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "curl", "-f", "http://0.0.0.0:8501/_stcore/health" ]

# Roda o streamlit 
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]