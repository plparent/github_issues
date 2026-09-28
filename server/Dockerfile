FROM python:3.12-slim

WORKDIR /app/server

ENV PYTHONPATH="/app"

COPY ./server/requirements.txt /app/server

RUN pip install -r requirements.txt

COPY ./server /app/server

COPY ./database/models.py /app/database/models.py

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--reload"]
