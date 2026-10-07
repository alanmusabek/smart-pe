"""Verify public routes with existing demo accounts, without changing student records."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
import httpx
from auth import create_access_token
from feature_extractor import get_connection


def demo_token(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT user_id, student_id, role FROM users WHERE email = %s AND is_active = TRUE', (email,))
            user_id, student_id, role = cur.fetchone()
    return create_access_token({'sub': user_id, 'student_id': student_id, 'role': role}), student_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    teacher, _ = demo_token('teacher2@smartpe.edu')
    student, sid = demo_token('student.demo@smartpe.edu')
    with httpx.Client(base_url=args.url, timeout=45) as client:
        for path in ['/health', '/app/', '/auth/config']:
            response = client.get(path)
            response.raise_for_status()
            print(f'Public {path}: {response.status_code}', flush=True)
        for path in ['/students', '/chat/status']:
            response = client.get(path)
            assert response.status_code in (401, 403), f'{path} is not protected'

        def check(item):
            token, path = item
            start = perf_counter()
            response = client.get(path, headers={'Authorization': 'Bearer ' + token})
            response.raise_for_status()
            print(f'{path}: {response.status_code} ({perf_counter() - start:.2f}s)', flush=True)
            return response.json()

        # Concurrent requests reproduce the dashboard's initial loading pattern.
        paths = [(teacher, p) for p in ['/auth/me', '/students', '/model/status', '/model/retrain/history', '/injury-types', '/exercises']]
        paths += [(student, p) for p in ['/auth/me', f'/students/{sid}', f'/students/{sid}/muscle-fatigue', f'/plans/{sid}/history?limit=50', '/chat/status']]
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(check, paths))
        history = check((student, f'/plans/{sid}/history'))
        assert history['plans'], 'Demo account needs a workout for explanation checks'
        exercises = check((student, f"/plans/{history['plans'][0]['plan_id']}/exercises"))
        assert exercises['exercises'], 'Demo workout needs an exercise'
        exercise_id = exercises['exercises'][0]['exercise_id']
        for token in [teacher, student]:
            result = check((token, f'/explain/exercise/{sid}/{exercise_id}'))
            assert result['shap_values'] and 0 <= result['score'] <= 1
            result = check((token, f'/explain/exercise/{sid}/{exercise_id}/ru'))
            assert result['explanation'].strip()
        print('All backend checks passed.', flush=True)


if __name__ == '__main__':
    main()
