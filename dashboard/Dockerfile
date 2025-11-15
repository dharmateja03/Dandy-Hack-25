FROM python:3.11-slim

WORKDIR /app

COPY index.html .

# Serve with Python's built-in HTTP server
CMD ["python", "-m", "http.server", "3000"]
