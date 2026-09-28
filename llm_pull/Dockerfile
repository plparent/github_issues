FROM python:3.12-slim

WORKDIR /app/pull

ENV PYTHONPATH="/app"

COPY ./llm_pull/requirements.txt /app/pull

RUN pip install -r requirements.txt

COPY ./llm_pull/llm_pull.py /app/pull 

CMD ["python3", "-m", "llm_pull"]
