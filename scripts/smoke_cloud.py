"""Check the hosted demo using real logins; never print credentials or tokens."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://smart-pe-demo.onrender.com')
    parser.add_argument('--credentials', default='.runtime/render-demo-secrets.json')
    parser.add_argument('--require-llm', action='store_true')
    parser.add_argument('--workout-writes', action='store_true', help='Create and delete only new workouts in the fictional demo')
    args = parser.parse_args()
    passwords = json.loads(Path(args.credentials).read_text(encoding='utf-8'))
    with httpx.Client(base_url=args.url.rstrip('/'), timeout=90, follow_redirects=True) as client:
        for path in ['/health', '/app/', '/auth/config']:
            response = client.get(path)
            response.raise_for_status()
            print(f'Public {path}: {response.status_code}', flush=True)
        for path in ['/students', '/chat/status']:
            assert client.get(path).status_code in (401, 403), 'Authenticated route became public'
        accounts = {}
        for role, email in [('teacher', 'teacher2@smartpe.edu'), ('student', 'student.demo@smartpe.edu')]:
            response = client.post('/auth/login', json={'email': email, 'password': passwords[f'DEMO_{role.upper()}_PASSWORD']})
            response.raise_for_status()
            account = response.json()
            assert account['role'] == role
            accounts[role] = account
            print(f'{role.capitalize()} login: passed', flush=True)
        sid = accounts['student']['student_id']

        def request(role, path, method='GET', payload=None):
            started = perf_counter()
            response = client.request(method, path, headers={'Authorization': 'Bearer ' + accounts[role]['access_token']}, json=payload)
            response.raise_for_status()
            print(f'{role} {method} {path}: {response.status_code} ({perf_counter()-started:.2f}s)', flush=True)
            return response.json()

        paths = [('teacher', path) for path in ['/auth/me', '/students', '/model/status', '/model/retrain/history', '/injury-types', '/exercises']]
        paths += [('student', path) for path in ['/auth/me', f'/students/{sid}', f'/students/{sid}/muscle-fatigue', f'/plans/{sid}/history?limit=50']]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda pair: request(*pair), paths))
        history = request('student', f'/plans/{sid}/history')['plans']
        assert history
        exercises = request('student', f"/plans/{history[0]['plan_id']}/exercises")['exercises']
        assert exercises
        eid = exercises[0]['exercise_id']
        for role in ['teacher', 'student']:
            explanation = request(role, f'/explain/exercise/{sid}/{eid}')
            assert explanation['shap_values'] and 0 <= explanation['score'] <= 1
            explanation = request(role, f'/explain/exercise/{sid}/{eid}/ru')
            assert explanation['explanation'].strip()
        preview = request('student', '/plans/generate', 'POST', {'student_id': sid, 'save_to_db': False})
        assert len(preview['plan']) == 3
        assert all([len(day[slot]) for slot in ['warmup','main','cooldown']] == [2,3,2] for day in preview['plan'])
        if args.workout_writes:
            students = request('teacher', '/students')
            assert students and all(row['name'].startswith('Demo Student ') for row in students), 'Write checks require the fictional demo dataset'
            before = {row['plan_id'] for row in request('student', f'/plans/{sid}/history?limit=50')['plans']}
            created = set()
            try:
                request('student', '/plans/generate', 'POST', {'student_id': sid, 'save_to_db': True})
                after = {row['plan_id'] for row in request('student', f'/plans/{sid}/history?limit=50')['plans']}
                created = after - before
                assert len(created) == 3
                for plan_id in sorted(created):
                    assigned = request('teacher', f'/plans/{plan_id}/exercises')['exercises']
                    assert len(assigned) == 7
                    forbidden = client.delete(f'/plans/{plan_id}', headers={'Authorization': 'Bearer ' + accounts['student']['access_token']})
                    assert forbidden.status_code == 403
            finally:
                for plan_id in sorted(created):
                    request('teacher', f'/plans/{plan_id}', 'DELETE')
            remaining = {row['plan_id'] for row in request('student', f'/plans/{sid}/history?limit=50')['plans']}
            assert remaining == before, 'Original demonstration workouts must remain'
            print('Workout saving, teacher deletion and student access checks passed.', flush=True)
        status = request('student', '/chat/status')
        print('Chat provider:', json.dumps(status), flush=True)
        session = request('student', '/chat/sessions', 'POST')['session_id']
        for language, text in [('en', 'Please write a short encouraging message about staying consistent.'), ('ru', 'Напиши короткое поддерживающее сообщение о регулярных занятиях.'), ('en', 'Show my progress')]:
            data = request('student', '/chat/', 'POST', {'text': text, 'language': language, 'session_id': session})
            assert data['message'].strip() and data['intent'] != 'generate_workout'
            if args.require_llm and data['intent'] == 'general_chat':
                assert data['llm_used'], 'Generative chat was unavailable; inspect /chat/status'
            print(json.dumps({'language': language, 'intent': data['intent'], 'llm_used': data['llm_used'], 'message_length': len(data['message'])}), flush=True)
        print('Hosted demo checks passed.', flush=True)


if __name__ == '__main__':
    main()
