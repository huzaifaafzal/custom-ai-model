# custom-ai-model

A local test setup for experimenting with self-hosted LLMs. Spins up Open WebUI in Docker against a host-installed Ollama, plus a small Python agent that runs natural-language questions against an Excel file.

Used as the test environment for the IEEE SVCC 2026 paper *"From Shadow AI to Secure AI: Enabling Secure Enterprise Generative AI On-Premises."*

## Contents

- `docker-compose.yml` — Open WebUI container, talks to Ollama on the host
- `Modelfile` — defines a custom Ollama model (`excel-qa`) for answering tabular questions
- `excel-agent.py` — Python script that loads an .xlsx file and answers questions about it via the local model
- `synthetic_pii_dataset.xlsx` — sample dataset used in our examples

## Setup

**1. Install Ollama** on your host machine: https://ollama.com

**2. Pull the base model:**
```
ollama pull llama3.1
```

**3. Build the custom model:**
```
ollama create excel-qa -f Modelfile
```

**4. Start Open WebUI:**
```
docker compose build --no-cache
docker compose up -d
```
Open WebUI will be available at http://localhost:3000.

**5. Run the agent against the dataset:**
```
pip install pandas openpyxl requests
python excel-agent.py --file synthetic_pii_dataset.xlsx
```

Type questions at the prompt; type `exit` to quit.

## Notes

- Ollama runs on the host (not in a container) so it can use the host GPU.
- The Open WebUI container reaches Ollama at `host.docker.internal:11434`.
- This is a research test environment, not a production deployment.

## Contact

Syed Huzaifa Bin Afzal — huzaifaafzall0@gmail.com
