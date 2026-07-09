# app/../Dockerfile — builds and runs the GraphiTech Academy backend on Render.
FROM python:3.11-slim

# System libraries WeasyPrint needs for PDF generation (Pango, Cairo, GDK-Pixbuf).
# Plain `pip install weasyprint` is not enough — this is why we use Docker
# instead of Render's native Python buildpack.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

# Render sets $PORT at runtime; default 8000 for local docker run.
ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
