# Demo Github Issues

A small demonstration project showcasing a fullstack application that pulls issues from a public github repository and summarizes the activity levels of issues using a local LLM.

## Requirements

Before running the project, make sure of the following:

-   **Docker and Docker Compose installed**
-   **A Github token with read permissions for the target repository**
-   **Nvidia GPU and the NVIDIA Container Toolkit** if you want to run the LLM on GPU otherwise it works fine on CPU (https://github.com/NVIDIA/nvidia-container-toolkit)


## Installation

Clone the repository:

```bash
git clone https://github.com/plparent/github_issues.git
cd github_issues
```

## Configuration

You can change configurations in the .env file. Notably the default ports are: 
```env
POSTGRES_PORT=5432
BACKEND_PORT=8000
FRONTEND_PORT=5173
```
The default repository issues are extracted from https://github.com/nats-io/nats.go.
You can uncomment the section in compose.yaml to enable Nvidia GPU.

## Running the Demo

Start the application with:

```bash
export GITHUB_TOKEN=<github_token>
docker compose up
```
The first time you run the program, it will build everything and pull all issues from the default repository which can take between 15 and 20 minutes.

The demo should then be available at:

```text
http://localhost:5173
```

## License

This project is licensed under the **GLP-3.0** license. See [`LICENSE`](https://github.com/plparent/github_issues?tab=GPL-3.0-1-ov-file) for details.
