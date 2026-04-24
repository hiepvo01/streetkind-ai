# StreetKind AI - Features & Capabilities

## Overview

StreetKind AI is a voice-powered form assistant that helps StreetKind volunteers fill incident reports and SafeBase forms by speaking naturally. The app uses Claude AI to extract structured data from voice transcripts and maps it to the exact form fields used in the existing SKSSIR system.

## Core Features

### Voice-to-Form AI Extraction
- Tap the microphone button and describe what happened
- Web Speech API transcribes speech in real-time (Australian English)
- Claude AI (via tool_use structured output) extracts form data matching SKSSIR schemas
- Supports multi-client extraction: one voice description generates incident + multiple client records

### Incident Report Form
- Matches the SKSSIR incident form layout exactly
- Fields: Team Leader Name, Base Site, Location/Address
- Incident Referred By: 11 checkboxes (SK Ambassador, CCTV, Self, Friend, General Public, Venue Security, Transport Staff, Police, Fire & Rescue, Rangers, Ambulance) + Other text
- Other Services Referred: 6 checkboxes + Others text
- Embedded Client forms (one per person helped)
- Incident Description and Outcome textareas
- Add/Remove Client buttons

### Client Form (5-Tab Wizard)
Each client within an incident has a 5-tab form matching SKSSIR exactly:

**Tab 1 - Client Information:**
- Gender (Male/Female/Non-Binary), Age Group (<18/18-25/26-39/40+), Alone (Yes/No)
- Intoxication Signs, Drug Use Signs
- Offensive Conduct, Self Harm Signs, Suicidal Signs
- Sexual Assault, Physical Assault, Domestic Violence
- Contact: First Name, Suburb

**Tab 2 - Basic Support:**
- Reconnection, Directions, Transport Information, Escort, Safe Space

**Tab 3 - Health Support:**
- Basic Aid, Additional Aid, Emergency Services Called

**Tab 4 - Risk Minimisation:**
- Physical Assault Risk (4 levels), Sexual Assault Risk (4 levels)
- Theft Risk: Client Consciousness, Valuables Visibility, Lost Property
- Injury Risk

**Tab 5 - Services Referred:**
- 10 service referrals (Alcohol & Drug Info, Beyond Blue, Child Protection, DV Line, Hospital, Lifeline, Link2Home, Salvos Street Level, Streetbeat Bus, Trafficking & Slavery AFP)
- Service Information, Other Support

### SafeBase Form
- People headcount by Gender (Male/Female/Non-Binary) x Age Group (<18/18-25/26-39/40+)
- Assistance Rendered: Directions, Bus Info, Train Info, Taxi Info, Device Charge, Family Reconnect
- Number counters with +/- buttons

### Dashboard
- 11 live impact statistics from Firebase:
  People Assisted | Drugs/Intoxicated | Alone | Sexual Assault Risk | De-escalated Violence | Welfare Checks | Reconnections | Escorted | First Aid | Volunteer Hours | Volunteer Shifts
- Colored stat cards matching the SKSSIR/streetkind-dashboard design

### Firebase Authentication
- Email/password login matching the SKSSIR login page design
- User profile loaded from Firebase RTDB (name, role, site)
- Role-based access: Administrator, Team Leader, Team Member
- Real user UID used for all form submissions (createdBy field)
- Logout functionality

### Firebase Database Integration
- Reads from and writes to the existing SKSSIR Firebase Realtime Database
- Incident submission flow matches SKSSIR exactly:
  1. Write incident to `incidentForms/{incidentId}`
  2. Write each client to `clients/{clientId}` with `incidentId` reference
  3. Update `incidentForms/{incidentId}/clientList` with all client IDs
  4. Set incident status to `completed`
- SafeBase submission writes to `safeSpaceForms/{formId}`
- Dashboard reads from `dashboardInfoStats`

## Design & UX

### Responsive Layout
- **Desktop (1920x1080)**: Full-width forms, multi-column layouts
- **iPad (768x1024)**: 2-column layouts, stackable grids
- **Mobile (375x812)**: Single column, vertically stacked, horizontally scrollable tabs

### Design System
- Matches SKSSIR and streetkind-dashboard styling
- Semantic UI React 2.1.4 components
- Blue primary color (#259ee5), green submit, red cancel
- StreetKind logo in menu bar
- Dark inverted push sidebar navigation
- Consistent with SKSSIR: huge menu, blue segments, raised cards

## Configuration (No-Code Editable)

All configuration lives in `config/` as plain JSON and text files:

| File | What it controls |
|------|-----------------|
| `config/sites.json` | Operating sites (add/remove/rename) |
| `config/form_types.json` | Form labels, icons, Firebase paths |
| `config/app.json` | App name, AI model, speech language, defaults |
| `config/prompts/incident.txt` | How AI interprets incident descriptions |
| `config/prompts/safebase.txt` | How AI interprets SafeBase descriptions |
| `config/fields/shared.json` | Gender and age options (all forms) |
| `config/fields/incident.json` | Incident-specific options |
| `config/fields/safebase.json` | SafeBase-specific options |
| `config/fields/client.json` | Client-specific options (50+ fields) |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python), Uvicorn |
| Frontend | React 18.2, Semantic UI React 2.1.4 |
| AI | Claude via Microsoft Foundry (tool_use structured output) |
| Auth | Firebase Authentication (email/password) |
| Database | Firebase Realtime Database |
| Speech | Web Speech API (browser-native) |
| Testing | Playwright + pytest (20 E2E tests) |

## Test Coverage

20 E2E tests covering:
- **Login** (5): valid/invalid credentials, logout, admin login, login page display
- **Incident Form** (2): API submission + Firebase verification + cleanup, UI rendering
- **SafeBase Form** (2): API submission + Firebase verification + cleanup, UI switching
- **Dashboard** (2): all 11 stat labels, non-zero values from live database
- **Responsive** (9): 3 viewports (1920/768/375) x 3 checks (login, app, sidebar)

All tests auto-clean test data from Firebase after each run.

## Demo Accounts

| Email | Password | Role |
|-------|----------|------|
| admin@streetkind.demo | streetkind123 | Administrator |
| leader@streetkind.demo | streetkind123 | Team Leader |
| volunteer@streetkind.demo | streetkind123 | Team Member |

## Known Limitations

- **Auth migration pending**: Only 3 demo users can login. The 66 original SKSSIR users exist in the database but their Firebase Auth credentials were not migrated from the old `sk-foundation` project. Migration requires `firebase auth:export/import` CLI access to the old project.
- **No offline mode**: Requires internet for Claude API and Firebase
- **Web Speech API**: Only works in Chrome and Edge browsers
- **Client form Phase 2**: AI extracts client data but some complex fields (consciousness level, lost property) may need manual review
