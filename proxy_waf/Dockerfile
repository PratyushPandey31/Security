FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir flask requests

COPY . .

EXPOSE 8080

CMD ["python", "waf_proxy.py"]
