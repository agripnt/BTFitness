---
name: dexa-scan
description: >
  Use when Brent asks about DEXA scan results, body composition, body fat percentage,
  lean mass, muscle mass, bone density, or visceral fat levels.
  Triggers on: "show my DEXA results", "what's my body comp", "how's my body fat",
  "lean mass", "visceral fat", "bone density", "show my scan", "body composition update".
  Do NOT use for workout generation or readiness checks — only for DEXA data retrieval and analysis.
---

# DEXA Scan Body Composition Analyst

## Purpose
Retrieve and analyze Bodyspec DEXA scan data to provide a structured body composition
report with trend comparison vs the prior scan, and flag any significant changes.

## Data Sources
**Primary (persistent):** `data/bodyspec_dexa_history.json`
- This file is your complete scan history — it never gets overwritten, only appended
- It is loaded into `coach_context` on every daily sync automatically

**To sync after a new scan:**
```bash
python3 scripts/Bodyspec_DEXA_Sync.py
```
**First-time setup (one-time OAuth):**
```bash
python3 scripts/Bodyspec_DEXA_Sync.py --setup
```

## Output Format
Generate a structured body composition report:

```
📊 DEXA SCAN REPORT — [Scan Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏋️  BODY COMPOSITION
   Total Body Fat:      X.X%    (↑/↓ X.X% vs prior)
   Fat Mass:            XXX lbs (↑/↓ X lbs vs prior)
   Lean Mass:           XXX lbs (↑/↓ X lbs vs prior)

🦴 BONE DENSITY
   Total Bone Mass:     X.X lbs (T-score: X.X)

⚡ VISCERAL FAT
   Visceral Fat:        X lbs   [LOW/MODERATE/HIGH]
   (Normal <1.0 lbs / <2.0 lbs concern zone)

📍 REGIONAL BREAKDOWN
   Arms:    X.X% fat | X.X lbs lean
   Legs:    X.X% fat | X.X lbs lean
   Trunk:   X.X% fat | X.X lbs lean

📈 TREND vs PRIOR SCAN ([Prior Scan Date])
   [Lean mass trend narrative]
   [Fat trend narrative]
   [Any flags or coaching notes]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Interpretation Rules
- **Weight in lbs** always. Convert from kg if needed (`× 2.20462`).
- **Lean mass loss** (>1 lb between scans): Flag as ⚠️ and check if training volume dropped.
- **Visceral fat increase**: Flag as ⚠️ and note cortisol/sleep correlation.
- **Bone density**: T-score above -1.0 is normal for Brent's age group. No alarm unless < -1.0.
- **Context awareness**: Factor in Brent's protocols (started 2/9/26) — expect
  gradual improvements in lean mass and visceral fat reduction over 3-6 months on protocol.

When interpreting scans, note distance from protocol start date and whether trends align
with expected protocol outcomes.

## Scan History Summary
When asked about trends (multiple scans), list all scans chronologically:
```
Date          | Body Fat % | Lean Mass | Visceral Fat
2025-XX-XX    |   XX.X%    |  XXX lbs  |   X.X lbs
2026-XX-XX    |   XX.X%    |  XXX lbs  |   X.X lbs
```
