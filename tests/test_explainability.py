from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import DMatrix
from explainability import FEATURE_COLS, load_explainer


def test_native_explanations_match_the_deployed_models_predictions():
    artifact = Path(__file__).resolve().parents[1] / 'fitness_ranker.pkl'
    model, explainer = load_explainer(str(artifact))
    frame = pd.DataFrame([
        {feature: value for feature in FEATURE_COLS} for value in (0.0, 1.0, 3.0)
    ])
    values = explainer.shap_values(frame)
    assert values.shape == (3, len(FEATURE_COLS))
    assert np.isfinite(values).all()
    native = model.get_booster().predict(
        DMatrix(frame), pred_contribs=True, iteration_range=explainer.iteration_range)
    # Bias is excluded from features but included when reconstructing the score.
    reconstructed = 1 / (1 + np.exp(-(values.sum(axis=1) + native[:, -1])))
    np.testing.assert_allclose(reconstructed, model.predict_proba(frame)[:, 1], atol=1e-6)
