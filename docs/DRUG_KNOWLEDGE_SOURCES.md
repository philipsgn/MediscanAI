# DRUG KNOWLEDGE SOURCES & IDENTIFIER BRIDGE ARCHITECTURE CONTRACT

**Document Version:** 1.0  
**Status:** APPROVED & IMPLEMENTED  
**Date:** 2026-09-01  
**Applies to:** Backend Normalization Service, RxNorm Client, DDInter Service, Identifier Bridge, Clinical Evaluation Engine  

---

## 1. Executive Summary & Source Authority Hierarchy

MediScanAI enforces an authority-driven, multi-tier drug normalization and clinical evaluation pipeline. In accordance with clinical safety invariants (`UNKNOWN IS BETTER THAN WRONG`), no drug candidate is inferred or guessed for dangerous drug-drug interactions (DDI) without verified identity mapping.

```
                      [ OCR Candidate Tokens ]
                                 │
                                 ▼
                     [ 1. Local Verified DB ]
                       (Exact / Fuzzy Match)
                                 │
                      (Miss)     ▼
             [ 2. RxNorm / RxNav (Primary Authority) ]
               REST API (rxcui.json, approximateTerm)
                   /                         \
         (RESOLVED)                           (UNRESOLVED / REVIEW)
             │                                         │
             ▼                                         ▼
   [ Identifier Bridge ]                      [ 3. OpenFDA API ]
(RxCUI -> Canonical Ingredient)             (Supporting Evidence Only)
   (Direct / Synonyms)                    (Max Conf 0.6, is_verified=False)
             │                                         │
             ▼                                         ▼
 [ Safe for DDI = True ]                    [ Safe for DDI = False ]
             │                                (BLOCK DDI INFERENCE)
             ▼                                         │
[ 4. DDInter Local v2.0 ]                             │
 (On-premise frozenset lookup)                         │
 (Zero live network calls)                             │
             │                                         │
             └───────────────────┬─────────────────────┘
                                 ▼
              [ 4-Layer Clinical Evaluation Engine ]
```

---

## 2. Source Comparison & Decision Matrix

| Metric / Attribute | 🇺🇸 RxNorm / RxNav | 🏛️ OpenFDA Drug Label | 📚 DDInter (v2.0) | 🇻🇳 Local Drug DB |
| :--- | :--- | :--- | :--- | :--- |
| **Role in Architecture** | **PRIMARY Normalization Authority** | **SECONDARY Supporting Evidence** | **LOCAL DDI Knowledge Engine** | **TIER-1 Fast Cache** |
| **Type** | External Live REST API | External Live REST API | Local Static Versioned JSON | Local Static JSON |
| **Network Path** | Async HTTP (`timeout=4.0s`) | Async HTTP (`timeout=6.0s`) | **Zero Live Network Calls** | Local File / Memory |
| **License / Terms** | Open / Public Domain (NLM/NIH) | Open Public Domain (US FDA) | CC BY-NC-SA 4.0 | Proprietary Internal |
| **Identifier System** | RxCUI (Concept Unique ID) | SPL Set ID, NDC, UNII | DDInter ID (`DDInter100...`) | Drug ID (`DRUG_...`) |
| **Auto-Resolve Safe?** | **YES** (for exact concept matches) | **NO** (Strictly requires HITL) | **YES** (Curated pairwise DDI) | **YES** (Curated internal DB) |
| **Safety Invariant** | Ambiguous $\rightarrow$ Review | Max confidence $\le 0.6$ | Unbridged $\rightarrow$ Block DDI | Fuzzy $>85 \rightarrow$ High conf |

---

## 3. Core Architectural Modules

### 3.1. RxNorm / RxNav Client (`app/services/rxnorm_service.py`)
- **Base URL:** `https://rxnav.nlm.nih.gov/REST`
- **Resolution States:**
  - `RESOLVED`: Exact match with RxCUI, concept name, TTY (`IN`, `PIN`, `MIN`, `BN`, `SCD`).
  - `CANDIDATE_REQUIRES_REVIEW`: Approximate term returns ambiguous candidates without high confidence margin.
  - `UNRESOLVED`: Term not found in RxNorm terminology.
  - `SOURCE_UNAVAILABLE`: Network failure, timeout, or HTTP 5xx.

### 3.2. Identifier Bridge (`app/services/identifier_bridge.py`)
- **Mapping Types:**
  - `DIRECT_CANONICAL`: Exact match to curated active ingredient dictionary.
  - `SYNONYM_BRIDGE_VERIFIED`: Verified medical synonym bridging (e.g. `acetylsalicylic acid` $\rightarrow$ `aspirin`, `acetaminophen` $\rightarrow$ `paracetamol`).
  - `UNSUPPORTED_NO_MATCH`: Unverified entity $\rightarrow$ `is_safe_for_ddi = False`.
- **Invariants:**
  - **INV-01 (Authority Gate):** DDI engine only consumes canonical entities from verified sources.
  - **INV-02 (Unknown > Wrong):** Unresolved or candidate-only items cannot trigger automatic DDI inferences.
  - **INV-03 (Provenance):** All alerts record source, dataset version, and identifier.

### 3.3. DDInter Local Engine (`app/services/ddinter_service.py` + `ddinter_interactions.json`)
- **Dataset Version:** 2.0 (CC BY-NC-SA 4.0).
- **Storage:** Local static JSON in `app/data/ddinter_interactions.json`.
- **Lookup Complexity:** $O(1)$ commutative pairwise lookup via `frozenset([drug_a, drug_b])`.
- **No Runtime Dependencies:** Zero external network calls or dynamic downloading in production request path.

### 3.4. 4-Layer Clinical Engine Integration (`app/services/evaluation_service.py`)
- **Layer 1:** Duplicate active ingredient and total daily overdose check.
- **Layer 2 (Drug-Drug):** Combines core emergency rules with DDInter local pairwise dataset with full provenance (`DDInter100...`).
- **Layer 3:** Drug-condition conflict and contraindication check.
- **Layer 4:** Population-based dosage appropriateness check.

---

## 4. Verification & Testing Standards

- All 12 specialized test cases implemented in `backend/tests/test_drug_knowledge_bridge.py`.
- All 14 governance & coverage test cases implemented in `backend/tests/test_clinical_governance_coverage.py`.
- 100% test pass rate across 202 backend unit/integration tests (`pytest backend/tests`).
- 100% test pass rate across 16 AI pipeline tests (`pytest ai/tests`).
- Clean frontend production compilation (`npm run build`).

---

## 5. Stage 12: Clinical Knowledge Dataset Governance & Invariants

### 5.1. Core Safety Invariants
1. **INV-12-01 (UNKNOWN IS NOT SAFE):** `UNRESOLVED`, `AMBIGUOUS`, `SOURCE_UNAVAILABLE`, `NOT_COVERED` states never produce a blanket "No interaction" safety claim.
2. **INV-12-02 (DATASET ABSENCE IS NOT CLINICAL NEGATIVE):** DDInter is a curated positive interaction dataset; absence of record is scoped as `NO_RECORD_IN_DATASET` within dataset boundaries and never proclaimed as unconditional negative proof of absolute safety.
3. **INV-12-03 (NORMALIZATION != COVERAGE):** Resolving a drug via RxNorm/Local DB establishes identity, not DDI coverage. A drug is only `COVERED` if its canonical entity exists in the active DDI dataset universe (`ddinter_service.is_drug_in_universe()`).
4. **INV-12-04 (UNVERIFIED SOURCE CANNOT PROMOTE CLINICAL CONFIDENCE):** OpenFDA unverified candidates remain `is_verified=False` and are blocked from automatic DDI inference.

### 5.2. Governance & Manifest
- **Manifest Path:** `backend/app/data/manifest.json` (tracking SHA256 checksum, active version 2.0).
- **Integrity Validator:** `backend/app/governance/dataset_validator.py` (enforcing schema, uniqueness of IDs, self-pair rejection, symmetric pair deduplication, valid severity).
- **Rollback Policy:** Rollback targets must physically exist on disk and pass full validation before selection (`rollback_available: false`).

