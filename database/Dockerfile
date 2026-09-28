FROM python:3.12-slim

WORKDIR /app/database

ENV PYTHONPATH="/app"

COPY ./database/requirements.txt /app/database

RUN pip install -r requirements.txt

COPY ./database /app/database

CMD ["alembic", "upgrade", "head"]
