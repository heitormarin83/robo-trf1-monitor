FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY monitor_trf1_cloud.py .

# Comando padrão
CMD ["python", "monitor_trf1_cloud.py"]

