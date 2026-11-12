"""Model explainability module."""

from nosql_rag.explainability.shap_explainer import (
    ShapExplanationResult,
    explain_instance_with_shap,
    explain_model_with_shap,
)

__all__ = ["ShapExplanationResult", "explain_instance_with_shap", "explain_model_with_shap"]
