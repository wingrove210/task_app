FROM python:3.12-slim

WORKDIR /code

COPY common/ ./common/
COPY task/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY task/ ./

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
