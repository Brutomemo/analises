FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretório para secrets
RUN mkdir -p ~/.streamlit

# Configurar Streamlit para Railway
RUN echo "\
[general]\n\
headless = true\n\
\n\
[server]\n\
port = 8000\n\
headless = true\n\
runOnSave = false\n\
\n\
[logger]\n\
level = info\n\
" > ~/.streamlit/config.toml

# Expor porta
EXPOSE 8000

# Comando para rodar
CMD ["streamlit", "run", "app.py", "--server.port=8000", "--server.address=0.0.0.0"]
