# Model Validation and Promotion

Production models must be trained, tracked, calibrated, explainable, and promoted through champion/challenger review.

## Required Promotion Evidence

| Evidence | Requirement |
| --- | --- |
| Registered artifact | Model artifact URI in MLflow-compatible registry or approved object storage |
| Training snapshot | Point-in-time feature/data snapshot ID |
| Out-of-sample score | Challenger improves over champion by the configured threshold |
| Calibration report | Calibration error is below policy threshold |
| Drift report | Latest data drift is below policy threshold |
| Explainability report | SHAP/LIME-style local attribution or interpretable surrogate report |
| Approval record | Human review before production promotion |

## Promotion Policy

- Minimum out-of-sample improvement: 5%.
- Maximum calibration error: 0.12.
- Maximum drift score: 0.20.
- Promotion is blocked when artifact, snapshot, calibration, drift, or explainability evidence is missing.

## Production Boundary

The repository contains deterministic baseline models and promotion gates. A production release still requires trained artifacts from approved data, registry connectivity, and reviewed validation reports.
