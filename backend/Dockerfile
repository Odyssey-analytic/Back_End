FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python" , "./manage.py", "makemigrations"]
CMD ["python" , "./manage.py", "migrate"]
CMD ["uvicorn", "backend.asgi:application", "--host", "0.0.0.0" , "--port" , "8000" ]


# test of .yml