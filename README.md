# BTFitness
My fun fitness AI app


### DEXA Body Composition Review
Ask: *"Show my DEXA results"* or *"What's my body comp?"*
→ `dexa-scan` skill reads from `data/bodyspec_dexa_history.json` and produces a structured report.

### 1. Initial Bodyspec DEXA sync (first time only)
```bash
python scripts/Bodyspec_DEXA_Sync.py
```
This fetches your full scan history and saves it to `data/bodyspec_dexa_history.json`.
Run again after each new scan to append the latest result.

### 2. Use the agent
In the Antigravity chat, try:
- `"Show me my latest DEXA scan results"`
- `"How's my body composition trending?"`

## Bodyspec DEXA Integration
...

### How it works
- DEXA scans happen every 3–6 months, so the sync script is run **manually** after each appointment.
- All scan history is stored persistently in `data/bodyspec_dexa_history.json` — never overwritten, only appended.
- The daily Master Sync Orchestrator reads from this local file (no API call) and includes it in the coach context.
- The `dexa-scan` skill reads from this file to generate body composition reports.

### API Details
- **Base URL:** `https://app.bodyspec.com`
- **Auth:** `Bearer <BODYSPEC_ACCESS_TOKEN>` (personal access token from portal)
- **Key endpoints per result:**
  - `GET /api/v1/users/me/results/` — list all results
  - `GET /api/v1/users/me/results/{id}/dexa/scan-info` — scan metadata
  - `GET /api/v1/users/me/results/{id}/dexa/composition` — lean/fat by region
  - `GET /api/v1/users/me/results/{id}/dexa/bone-density` — BMD + T-scores
  - `GET /api/v1/users/me/results/{id}/dexa/visceral-fat` — VAT
  - `GET /api/v1/users/me/results/{id}/dexa/percentiles` — age/sex percentiles

## Directory Structure
```
.
├── .agent/
│   ├── rules.md                          # Workspace-level agent instructions
│   └── skills/
│       ├── dexa-scan/                    # Bodyspec DEXA body composition analyst
│       │   └── SKILL.md
├── API_Documentation/
│   └── Bodyspec_api-1.json               # Bodyspec OpenAPI spec v0.11.0
├── scripts/
│   ├── Bodyspec_DEXA_Sync.py             # Bodyspec DEXA scan history (persistent)
├── data/
│   └── bodyspec_dexa_history.json        # Persistent DEXA scan history (committed)
└── .env                                  # API keys (gitignored)
...

---


- **Full spec:** `API_Documentation/Bodyspec_api-1.json`
