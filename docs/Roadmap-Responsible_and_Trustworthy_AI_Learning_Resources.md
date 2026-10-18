# Roadmap-Responsible_and_Trustworthy_AI_Learning_Resources

## Page 1

Responsible & Trustworthy AI — Learning
Resources

Learning Objectives

By the end of this module, all learners will be able to:
1.   Explain the core principles of responsible and trustworthy AI — fairness, transparency, accountability,
     robustness/safety, privacy and reliability — and locate them in real deployments governed by the NIST AI
     RMF and the EU AI Act. (Bloom's: Remember/Understand)

2.   Apply explainability techniques (feature importance, SHAP/LIME, partial-dependence plots,
     counterfactuals) to interpret a pre-trained model's predictions and state the strengths and limits of each.
     (Bloom's: Apply/Analyze)
3.   Distinguish correlation from causation using the ladder of causation (association -> intervention ->
     counterfactual), read a Directed Acyclic Graph (DAG), and identify where causal reasoning makes a system
     more trustworthy. (Bloom's: Understand/Analyze)

4.   Implement input and output guardrails — PII detection/redaction, prompt-injection detection, sensitive-topic
     classification, and schema plus groundedness validation — and explain why each layer exists. (Bloom's:
     Apply)
5.   Enforce least-privilege tool permissions and human-in-the-loop control in an agentic system, and
     estimate the blast radius of a runaway agent. (Bloom's: Apply/Evaluate)
6.   Instrument a trustworthy pipeline with tamper-evident audit logging, monitoring, incident review and
     red-teaming, and prove its behaviour with automated tests. (Bloom's: Apply/Evaluate)

By the end of the module, some learners will be able to (depth / stretch):

7.   Compare multiple explanation methods (e.g., SHAP vs. counterfactuals) and evaluate them with
     fidelity/stability metrics or a small human-subject study. (Bloom's: Analyze/Evaluate/Create)

8.   Build and query a simple causal model (DAG plus estimand, DoWhy-style) for intervention or counterfactual
     analysis on a dataset. (Bloom's: Apply/Create)

9.   Critique a live system against the NIST AI RMF and the EU AI Act, assemble an evidence pack, and defend
     a go/no-go deployment decision with named owners, tolerances and review dates. (Bloom's: Evaluate/Create)


Contents to cover

Topic 1 — Foundations of Responsible & Trustworthy AI
  Core principles of trustworthy AI
    –  Fairness (bias detection and mitigation)

    –  Transparency
    –  Accountability

    –  Robustness / safety
    –  Privacy (e.g., differential privacy)

    –  Reliability
  Trustworthiness vs. accuracy — why a highly accurate model can still be untrustworthy

  Risk management with the NIST AI RMF — GOVERN -> MAP -> MEASURE -> MANAGE




                                                               Page 1

## Page 2

  Regulatory frame — EU AI Act risk tiers and Annex III high-risk categories; GDPR Arts. 15, 22, 33 and 35

  The AI lifecycle — development, deployment and end-user serving

Topic 2 — Explainable AI (XAI)
  Interpretable vs. black-box models

  Post-hoc explanation methods — LIME, SHAP, partial-dependence plots, counterfactuals
  Intrinsic interpretability — decision trees, rule lists, monotonic and generalised additive models

  Global vs. local explanations — whole-model vs. single-decision
  What makes a good explanation — fidelity, stability, human understandability

  Audience-specific explanations — the affected person, the operator and the regulator
  Explanation misuse — attributions explain the model, not the world; a plausible explanation can increase
   over-trust


Topic 3 — Causal AI for Deeper Trust (optional)
  Correlation vs. causation
  The ladder of causation — association -> intervention -> counterfactual

  Structural Causal Models (SCMs) and DAGs
  Reading a graph — confounding, colliders and mediation

  Identification — the estimand vs. the estimate; ITT vs. TOT
  Causal failure modes — confounding as the default explanation for observational association

  Why it matters — causal explanations are more reliable and actionable

Topic 4 — Engineering Track: Prompt & Agentic AI Safety
  Preventing prompt injection

  Vulnerability identification in LLM applications
  Data privacy and governance — what to provide and what not to

  PII — what it is and how to handle it
  Handling sensitive information

  Input/output validation for AI and LLMs
  Bias detection

  Alignment (see Anthropic's alignment work)
  Handling safe-request refusal

  Hallucinations and how to detect them
  Alignment and autonomy control — human in / on / out of the loop

  Governance
  Data poisoning

  Incident management — who bears the cost when losses occur

Topic 5 — Integration, Auditing & Regulation
  Accountability as a mechanism — a named human-oversight role with authority to override





                                                               Page 2

## Page 3

  The evidence pack — model card, DPIA, technical documentation, fundamental-rights assessment,
   post-market monitoring and incident reports, right to explanation
  Post-market monitoring — every signal has a threshold, an owner and an action

  Incident response and the incident loop — severity, a clock, and feeding fixes back into the test suite
  Go / no-go and residual-risk acceptance — escalating risk tolerance to a human for signature

  Decommissioning triggers — decided before a crisis, not during one
  Red-teaming — adversarial testing of the system

Topic 6 — Testing & Best Practices
  Test strategy for AI systems — unit, property-based, integration and load testing
  Monitoring & observability — what to log, measure and alert on

  Deployment practices for trustworthy systems
  Architecture decision records (ADRs)

  The best-practice checklist — prompt engineering, data privacy & RAG, agentic safety, testing, monitoring,
   deployment, ADRs


Resources + Additional Materials

References & further reading
  NIST AI Risk Management Framework (AI RMF 1.0) — GOVERN / MAP / MEASURE / MANAGE.
  EU AI Act — Annex III high-risk categories, Chapter III obligations, Arts. 27, 72–73 and 86.

  GDPR — Arts. 15, 22, 33 and 35.
  Christoph Molnar — Interpretable Machine Learning.

  Causal Inference for the Brave and True (Matheus Facure) · DoWhy / EconML tutorials.
  OWASP Top 10 for LLM Applications — prompt injection, excessive agency, sensitive-information disclosure.

  Anthropic alignment material — RLHF, RLAIF, Constitutional AI, Responsible Scaling.
  Trustworthy AI (module reference book).

Additional materials
  Module plan — Responsible and Trustworthy AI.
  Best-practice checklist — the seven-area "never / always" checklist.

  Question banks — core questions (C1–C4), session questions, and the agentic and scenario question sets.
























                                                                Page 3

