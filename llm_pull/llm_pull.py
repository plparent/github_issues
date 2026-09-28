import json
import logging
import os
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite4.2:3b")
OLLAMA_PULL_TIMEOUT = float(os.environ.get("OLLAMA_PULL_TIMEOUT", "1800"))

logger = logging.getLogger("llm_pull")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    """
    Block until OLLAMA_MODEL is pulled and ready on the Ollama server.

    Streams Ollama's pull progress (manifest, each layer, verification) and
    logs each status change, since a first-time pull of a multi-GB model can
    take a while with no other feedback otherwise.
    """
    logger.info("Requesting Ollama to pull model '%s' from %s", OLLAMA_MODEL, OLLAMA_URL)
    try:
        with requests.post(
            f"{OLLAMA_URL}/api/pull",
            json={"model": OLLAMA_MODEL, "stream": True},
            stream=True,
            timeout=OLLAMA_PULL_TIMEOUT,
        ) as response:
            response.raise_for_status()
            last_status = None
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("error"):
                    raise RuntimeError(event["error"])
                status = event.get("status")
                if status and status != last_status:
                    logger.info("Ollama pull '%s': %s", OLLAMA_MODEL, status)
                    last_status = status
    except requests.RequestException:
        logger.exception(
            "Failed to reach Ollama at %s to pull model '%s'", OLLAMA_URL, OLLAMA_MODEL
        )
        raise
    except RuntimeError:
        logger.exception("Ollama reported an error while pulling model '%s'", OLLAMA_MODEL)
        raise
    logger.info("Ollama model '%s' is ready", OLLAMA_MODEL)


if __name__ == "__main__":
    main()
