FROM python:3.12-slim

WORKDIR /app

# Copia solo requirements primero (cache de capas de Docker).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala Chromium + todas sus dependencias del sistema en un solo paso.
# --with-deps resuelve las librerias de Linux que Chromium necesita.
RUN playwright install --with-deps chromium

# Copia el resto del codigo.
COPY . .

# Render inyecta la variable PORT. Default 10000 para pruebas locales.
ENV PORT=10000
EXPOSE 10000

# Produccion: uvicorn directo, sin --reload, sin --loop (Linux usa el loop correcto).
# run.py y core/event_loop.py son SOLO para Windows dev local.
# shell form con sh -c para que $PORT se expanda correctamente.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
