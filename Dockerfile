FROM python:3.10-slim
WORKDIR /app
# Copiem requiremens, instalam dependentele
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Expunem portul FastAPI
EXPOSE 8000
# Comanda de start
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]