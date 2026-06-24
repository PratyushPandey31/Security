FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir flask requests

COPY . .

EXPOSE 9000

CMD ["python", "decoy.py"]
