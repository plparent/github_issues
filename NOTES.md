# Demo Notes

## 1. How to Run It Locally

Follow the instructions in the **README**.

## 2. Architecture

The full architecture is composed of 7 different docker containers:
1. Ollama instance for running LLMs locally.
2. Postgres Database that is fed the data pulled from the public repository.
3. Alembic for database migrations. It runs on every startup of the stack to update the database to the most recent migration. Uses SQLAlchemy as the ORM.
4. Worker that pulls from the public repository and stores the information to Postgres. On the first run, it will pull all the data in batches and timestamps when was the most recent pull done. Afterwards, it will only pull data that is more recent than the timestamp and update the timestamp accordingly. By default, it will check for new data on subsequent runs or every 10 minutes it is active.
5. LLM puller that will download a chosen LLM to Ollama. Allows for switching models between runs.
6. Server mainly responsible for interacting with the database and Ollama. Running on Fastapi and uvicorn with asynchronous endpoints (especially important to avoid blocking when calling Ollama).
7. Front-end written in Typescript with React to visually show the output of the back-end.

## 3. What I'd Do Next

If I had another day, I would focus on the following:

1.  **Add tests** Both unit tests and integrations tests.
    
2.  **Add an evaluation harness** This would allow me to compare different models.
    
3.  **Improve error handling** Most try catches are using generic exceptions.
    
4.  **Improve log handling** Send logs to telemetry tools to gather performance data.

## 4. AI Usage

AI was used primarily as a development assistant rather than as an autonomous implementation tool. I used it to generate individual functions that I would review and then copy/paste into the code. This allowed me to spend more time designing the architecture and containerizing it while reducing my token usage (I was using the free version of Claude). I effectively did an 80/20 split where the AI did the majority of the coding and I mostly reviewed and handled minor details.
