# Streetkind AI - Voice-to-Form Assistant

A voice-powered assistant that lets Streetkind volunteers speak naturally about incidents and SafeBase activity, then automatically fills in the required forms using AI-structured output.

## Problem

Volunteers on the street spend significant time manually filling multi-step forms (Incident Reports with 15+ fields, Client assessments with 50+ fields, SafeBase headcounts with 19 fields). This is slow, error-prone, and takes focus away from helping people.

## Solution

A voice-first interface where volunteers:
1. Tap a button and describe what happened naturally
2. Speech is transcribed in real-time
3. An AI model extracts structured data matching the exact form schemas
4. The volunteer reviews pre-filled fields and submits

## Target Forms

| Form | Complexity | Fields | AI Difficulty |
|------|-----------|--------|---------------|
| **SafeBase Form** | Low | ~19 (numeric counts by gender/age + assistance types) | Easy - mostly counting |
| **Incident Form** | Medium | ~15 (location, times, checkboxes, free text) | Medium - mixed field types |
| **Client Form** | High | ~50+ (nested risk assessment, multi-category booleans) | Hard - complex nested structure with clinical terminology |

## Architecture

```
  React Frontend (port 3000)             FastAPI Backend (port 5000)
  ========================              ===========================

  1. Voice Input                        GET /api/config
     (Web Speech API)                     -> sites, form types, field options
         |                                   (all from config/ files)
    transcript
         |
  2. "Extract" button  ──POST──>        POST /api/extract
                                          -> Claude tool_use (structured output)
         <──JSON──                        <- validated JSON
         |
  3. Form Preview
     (review & edit)
         |
  4. "Submit" button   ──POST──>        POST /api/submit
                                          -> Pydantic validation
                                          -> Firebase RTDB write
```

## Model Selection Guide

### Recommendation: Tiered approach

| Form | Recommended Model | Rationale |
|------|------------------|-----------|
| SafeBase Form | **Claude Haiku** or **Phi-3 / Llama 3.1 8B** | Simple numeric extraction. Small models handle this reliably. |
| Incident Form | **Claude Haiku** or **Claude Sonnet** | Mixed types (checkboxes, locations, free text). Haiku is fast and cheap enough. |
| Client Form | **Claude Sonnet** | Complex nested schema with clinical risk assessment. Needs strong structured output + domain understanding. |

### Cost estimate (Claude API)

| Model | Per form (est.) | Monthly (50 forms/night, 20 nights) |
|-------|----------------|--------------------------------------|
| Haiku | ~$0.001 | ~$1.00 |
| Sonnet | ~$0.01 | ~$10.00 |

Haiku or Sonnet is the sweet spot for this use case.

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI (Python) | Async, native Pydantic, auto API docs at `/docs` |
| Frontend | React 18.2 + Semantic UI React 2.1.4 | Matches existing SKSSIR / streetkind-dashboard ecosystem |
| Speech-to-text | Web Speech API (browser) + OpenAI Whisper (fallback) | Browser API is free; Whisper for offline/accuracy |
| AI extraction | Anthropic Claude API (tool_use structured output) | Guaranteed valid JSON matching form schemas |
| Database | Firebase RTDB (existing) | Writes directly to existing SKSSIR database |
| Config | JSON files in `config/` | Non-technical users can edit sites, prompts, field options |

## Getting Started

### Prerequisites
- Conda (Anaconda or Miniconda)
- Node.js 18+
- An Anthropic API key (get one at https://console.anthropic.com)
- Firebase service account key (from existing SKSSIR project) - optional for demo

### Installation

```bash
cd streetkind-ai

# Backend
conda env create -f environment.yml
conda activate streetkind-ai
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Frontend
cd frontend
npm install
cd ..
```

### Running (development)

Two terminals:

```bash
# Terminal 1: FastAPI backend (port 5000)
python run.py

# Terminal 2: React frontend (port 3000, proxies /api to 5000)
cd frontend
npm start
```

Open `http://localhost:3000` in Chrome or Edge (required for Web Speech API).

FastAPI auto-generated docs available at `http://localhost:5000/docs`.

### Alternative: pip only (no conda)

```bash
pip install -r requirements.txt
```

## Project Structure

```
streetkind-ai/
  app/                              # FastAPI backend
    __init__.py                     # App factory
    config.py                       # Config loader (reads from config/)
    routes.py                       # API endpoints
    schemas/
      incident_schema.py            # Incident form Pydantic model
      safebase_schema.py            # SafeBase form Pydantic model
      client_schema.py              # Client form Pydantic model (Phase 2)
    services/
      ai_extractor.py               # Claude tool_use structured output
      firebase_client.py            # Firebase RTDB write operations
      transcription.py              # Whisper fallback for offline
  config/                           # Editable by non-technical users
    app.json                        # App name, defaults, AI model settings
    sites.json                      # Operating sites
    form_types.json                 # Form type definitions
    prompts/
      incident.txt                  # AI prompt template for incidents
      safebase.txt                  # AI prompt template for SafeBase
    fields/
      shared.json                   # Options shared across forms (gender, age)
      incident.json                 # Incident-specific field options
      safebase.json                 # SafeBase-specific field options
      client.json                   # Client-specific field options (Phase 2)
  frontend/                         # React 18.2 + Semantic UI React
    package.json
    public/index.html
    src/
      App.js                        # Root component, loads config from API
      App.css                       # Styles matching SKSSIR design
      components/
        MenuBar/                    # Top nav with logo (matches SKSSIR)
        NavSidebar/                 # Push sidebar (matches SKSSIR)
        FormSelector/               # Form type + site selection
        VoiceInput/                 # Mic button + transcript + extract
        FormPreview/                # Review JSON + submit
      services/
        api.js                      # API client (fetchConfig, extract, submit)
      assets/
        street-kind-logo-black.svg  # Shared logo from SKSSIR
  tests/
    test_extraction.py              # AI extraction tests
  .env.example                      # Environment variable template
  environment.yml                   # Conda environment
  requirements.txt                  # pip fallback
  run.py                            # Entry point (uvicorn)
```

## Configuration

All configurable values live in `config/` as plain JSON and text files. No code changes needed to:

| File | What you can change |
|------|-------------------|
| `config/sites.json` | Add/remove/rename operating sites |
| `config/form_types.json` | Form labels, icons, Firebase paths |
| `config/app.json` | App name, default site, AI model, speech language |
| `config/prompts/incident.txt` | How the AI interprets incident descriptions |
| `config/prompts/safebase.txt` | How the AI interprets SafeBase descriptions |
| `config/fields/shared.json` | Gender and age group options (used by all forms) |
| `config/fields/incident.json` | Incident-specific options (encountered by, services) |
| `config/fields/safebase.json` | SafeBase-specific options (assistance types) |
| `config/fields/client.json` | Client-specific options (risk, support, referrals) |

## Prior Art

The `../StreetKind/` directory contains an earlier prototype built with Flask + OpenAI GPT-3.5 + Google Speech Recognition + Excel storage. Key improvements in this project:

- **FastAPI** instead of Flask (async, Pydantic-native, auto docs)
- **Claude tool_use** for guaranteed structured output (vs GPT freeform text parsing)
- **React + Semantic UI React** matching the SKSSIR/dashboard ecosystem
- **Externalised config** so non-technical users can edit sites, prompts, and field options
- **Firebase RTDB** integration (vs local Excel files)
- **Full SKSSIR schema** support (50+ fields vs 7)

## Roadmap

- [x] Project setup and schema definitions
- [x] Claude structured output via tool_use
- [x] Two-step extract/submit architecture
- [x] React frontend matching SKSSIR design system
- [x] Externalised config (sites, prompts, field options)
- [x] FastAPI backend with auto-generated docs
- [ ] Dynamic form renderer for review/edit (beyond raw JSON)
- [ ] Firebase integration testing with real SKSSIR database
- [ ] Client form extraction (complex, 5-step)
- [ ] Offline mode with local Whisper + small model
- [ ] React Native / Expo mobile app
