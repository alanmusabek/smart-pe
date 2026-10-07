"""Read-only checks against a running server using an existing demo student's token."""
import argparse
import json
from time import perf_counter
import httpx
from auth import create_access_token
from feature_extractor import get_connection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--require-llm', action='store_true', help='Fail if general chat returns a fallback instead of model output')
    args = parser.parse_args()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT user_id, student_id, role FROM users WHERE email = %s AND is_active = TRUE', ('student.demo@smartpe.edu',))
            user_id, student_id, role = cur.fetchone()
    token = create_access_token({'sub': user_id, 'student_id': student_id, 'role': role})
    with httpx.Client(base_url=args.url, headers={'Authorization': 'Bearer ' + token}, timeout=45) as client:
        status = client.get('/chat/status'); status.raise_for_status()
        print('Model status:', json.dumps(status.json()))
        started = client.post('/chat/sessions'); started.raise_for_status()
        session = started.json()['session_id']
        for language, text in [('en', 'Please write a short encouraging message about staying consistent.'), ('ru', 'Напиши короткое поддерживающее сообщение о регулярных занятиях.'), ('en', 'Show my progress')]:
            start = perf_counter()
            result = client.post('/chat/', json={'text': text, 'language': language, 'session_id': session})
            result.raise_for_status()
            data = result.json()
            assert data['message'].strip()
            assert data['intent'] != 'generate_workout', 'Read-only message unexpectedly generated a plan'
            if args.require_llm and data['intent'] == 'general_chat':
                assert data['llm_used'], f"Model did not generate a reply: {data.get('model_status')}"
            print(json.dumps({'language': language, 'seconds': round(perf_counter() - start, 2), 'intent': data['intent'], 'llm_used': data['llm_used'], 'message_length': len(data['message']), 'preview': data['message'][:120]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
