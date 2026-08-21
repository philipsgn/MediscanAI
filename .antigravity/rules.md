# ANTIGRAVITY ENGINE INSTRUCTIONS - MEDISCAN AI

You are acting as the Lead AI Developer for Mediscan AI. 

### 1. DIRECTIVE & CONTEXT
- Always strictly follow the pipeline and data models defined in `ARCHITECTURE.md`.
- Always check `STAGES.md` to identify the current task context and definition of done.
- Always obey the persona rules and boundaries defined in `AGENTS.md`.

### 2. EXECUTION BOUNDARIES
- **Backend First:** Core logic for Vision AI, Normalization, and Cross-Evaluation MUST reside in `backend/app/services/`.
- **Strict Data Schemas:** Never alter API request/response properties without checking `backend/app/schemas.py` and `frontend/src/types/medication.ts`.
- **Human-in-the-Loop:** For packaging scan stream, ALWAYS prompt/require user input for dosage via frontend forms.
- **No API Key Leaks:** Always fetch keys via environment variables configured in `backend/app/config.py`.

### 3. SELF-CORRECTION & TESTING
- Before marking a task complete in `STAGES.md`, run code linting/type checks and ensure no syntax or compile errors exist.