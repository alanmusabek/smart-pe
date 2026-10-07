import numpy as np
import plan_assembler


def test_rank_exercises_uses_one_prediction_for_all_candidates(monkeypatch):
    calls = []
    def features(student_id, exercise_ids, connection):
        calls.append(exercise_ids)
        return {eid: {name: 0 for name in plan_assembler.FEATURE_COLS} for eid in exercise_ids}
    monkeypatch.setattr(plan_assembler, 'extract_features_batch', features)
    class Model:
        def predict_proba(self, matrix):
            assert list(matrix.columns) == plan_assembler.FEATURE_COLS
            assert len(matrix) == 3
            return np.array([[.8, .2], [.1, .9], [.5, .5]])
    ranked = plan_assembler.rank_exercises(29, [{'exercise_id': i} for i in [1, 2, 3]], Model(), object())
    assert calls == [[1, 2, 3]]
    assert [r['exercise_id'] for r in ranked] == [2, 3, 1]


def test_empty_candidates_do_not_read_or_predict():
    assert plan_assembler.rank_exercises(29, [], None, None) == []
