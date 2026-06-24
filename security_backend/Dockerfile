FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir flask requests

COPY . .

EXPOSE 5000

# Create volume mount directory
RUN mkdir -p /app/data

CMD ["python", "backend.py"]
