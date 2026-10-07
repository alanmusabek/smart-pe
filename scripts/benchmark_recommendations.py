"""Read-only timing and SQL-count check for recommendation ranking."""
import json
import sys
import tempfile
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.model_cache import load_model
from feature_extractor import get_connection, extract_features
from plan_assembler import load_all_exercises, filter_exercises, rank_exercises


class CountedConnection:
    def __init__(self, connection):
        self.connection = connection
        self.queries = 0

    def cursor(self):
        parent = self
        class Cursor:
            def __init__(self):
                self.cursor = parent.connection.cursor()
            def execute(self, *args, **kwargs):
                parent.queries += 1
                return self.cursor.execute(*args, **kwargs)
            def __getattr__(self, name):
                return getattr(self.cursor, name)
        return Cursor()


if __name__ == '__main__':
    student_id = int(sys.argv[1]) if len(sys.argv) > 1 else 29
    connection = get_connection()
    try:
        counted = CountedConnection(connection)
        start = perf_counter()
        model = load_model()
        candidates = filter_exercises(student_id, load_all_exercises(counted), counted)
        ranked = rank_exercises(student_id, candidates, model, counted)
        print(json.dumps({'exercises': len(ranked), 'queries': counted.queries,
                          'seconds': round(perf_counter() - start, 4)}))
        counted.queries = 0
        start = perf_counter()
        model = load_model()
        candidates = filter_exercises(student_id, load_all_exercises(counted), counted)
        rank_exercises(student_id, candidates, model, counted)
        print(json.dumps({'warm_queries': counted.queries, 'warm_seconds': round(perf_counter() - start, 4)}))
        baseline = Path(tempfile.gettempdir()) / 'smart-pe-feature-baseline.json'
        if baseline.exists():
            old = json.loads(baseline.read_text(encoding='utf-8'))
            mismatches = []
            for key, expected in old.items():
                sid, eid = map(int, key.split(':'))
                actual = extract_features(sid, eid, connection)
                mismatches.extend(f'{key}:{field}' for field in expected if actual[field] != expected[field])
            print(json.dumps({'baseline_vectors': len(old), 'mismatched_features': mismatches}))
    finally:
        connection.close()
