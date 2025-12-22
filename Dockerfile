FROM python:3.12.9

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install-deps
RUN playwright install

COPY . .

EXPOSE 8080

CMD ["uvicorn", "api.api_server:app", "--host", "0.0.0.0", "--port", "8080"]