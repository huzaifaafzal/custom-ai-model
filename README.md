# custom-ai-model

Test setup for the GovernAI architecture — a sanctioned on-premises generative-AI environment for enterprise use. Spins up Open WebUI in Docker against a host-installed Ollama, plus a small Python agent that runs natural-language questions against an Excel file.

This repository accompanies the IEEE SVCC 2026 paper:

> **Are You Aware of Shadow AI? GovernAI for Addressing Emerging Risks**
> Syed Huzaifa Bin Afzal, Justin Bowman, Yu-Tien Renee Chian, Ayush Singh, and Wenjun Fan
> University of Washington, Tacoma — IEEE Silicon Valley Cybersecurity Conference (SVCC) 2026.

## Contents

- `docker-compose.yml` — Open WebUI container, talks to Ollama running on the host
- `Modelfile` — defines a custom Ollama model (`excel-qa`) for tabular question answering
- `excel-agent.py` — Python script that loads an .xlsx file and answers questions via the local model
- `synthetic_pii_dataset.xlsx` — synthetic dataset used for our example workflows

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

- Ollama runs on the host (not in a container) so it can use the host GPU directly.
- The Open WebUI container reaches Ollama at `host.docker.internal:11434`.
- This is a research test environment, not a production deployment.

## Citation

```bibtex
@inproceedings{afzal2026governai,
  title     = {Are You Aware of Shadow AI? GovernAI for Addressing Emerging Risks},
  author    = {Afzal, Syed Huzaifa Bin and Bowman, Justin and Chian, Yu-Tien Renee and Singh, Ayush and Fan, Wenjun},
  booktitle = {IEEE Silicon Valley Cybersecurity Conference (SVCC)},
  year      = {2026}
}
```

## Contact

Syed Huzaifa Bin Afzal — huzaifaafzall0@gmail.com
