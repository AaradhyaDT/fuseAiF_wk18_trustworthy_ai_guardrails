# Agent Rules & Workflow Guidelines — fuseAiF_wk18_trustworthy_ai_guardrails

Welcome, Agent. This repository (`fuseAiF_wk18_trustworthy_ai_guardrails`) serves as the official implementation of **Trustworthy AI: Implementing Input and Output Guardrails** for Fuse AI Fellowship 2026 (Week 18).

---

## 1. Git Workflow & Ecosystem Automation (CRITICAL — STRICT ENFORCEMENT)

To avoid breaking branch tracking and prevent wasteful multi-step Git commands, **NEVER run individual `git add`, `git commit`, `git push`, or `git pull` commands directly.**

**ALWAYS execute `.\sync.bat` (or `.\sync.ps1`) for repository synchronization and version control.**

### Core Commands
- **Routine Sync**:
  ```powershell
  .\sync.bat
  ```
- **Custom Commit Message**:
  ```powershell
  .\sync.bat -m "feat(guardrails): add output groundedness verifier"
  ```
- **Preview Only**:
  ```powershell
  .\sync.bat -WhatIf
  ```
- **Safe Pull Only**:
  ```powershell
  .\sync.bat -PullOnly
  ```

---

## 2. Verification Gates & Reality Layer

Before finalizing changes or running `.\sync.bat`:
1. **Linting & Hygiene Gate**:
   ```powershell
   ruff check .
   ```
2. **Pytest Verification Gate**:
   ```powershell
   pytest tests/ -v
   ```
3. **Deterministic Evaluation Suite**:
   ```powershell
   python eval/run_eval.py --dataset eval/golden_benchmark.jsonl
   ```

---

## 3. Architecture & Invariants

- **Zero-PII Leakage**: Detect and redact email, telephone, SSN, and sensitive tokens prior to downstream model inference.
- **Fail-Closed on Severe Violations**: Reject prompt injections and high-risk sensitive topics before making expensive API calls.
- **Pydantic Schema Validation**: All model outputs must validate against structured schema with automatic 1-pass corrective retry and fallback circuit breaker.
- **Groundedness Verification**: Ground truth NLI / entailment verification against source context documents.
