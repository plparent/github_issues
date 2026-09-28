FROM python:3.12-slim

WORKDIR /app/sync

ENV PYTHONPATH="/app"

COPY ./sync/requirements.txt /app/sync

RUN pip install -r requirements.txt

COPY ./sync /app/sync

COPY ./database/models.py /app/database/models.py

CMD ["python3", "-m", "worker"]
