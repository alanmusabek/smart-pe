"""Read-only session benchmark; excludes optional provider generation time."""
import json
import sys
from pathlib import Path
from time import perf_counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routers import chatbot
from scripts.benchmark_recommendations import CountedConnection


if __name__ == '__main__':
    student_id = int(sys.argv[1]) if len(sys.argv) > 1 else 29
    original = chatbot.get_connection
    connections = []
    class Connection(CountedConnection):
        def close(self):
            self.connection.close()
    def counted():
        conn = Connection(original())
        connections.append(conn)
        return conn
    chatbot.get_connection = counted
    chatbot.llm_client = None
    user = {'user_id': -1, 'student_id': student_id, 'role': 'student'}
    start = perf_counter()
    session = chatbot.start_session(user)
    first_queries = sum(c.queries for c in connections)
    print(json.dumps({'initial_queries': first_queries, 'initial_seconds': round(perf_counter() - start, 4)}))
    for prompt in ['hello', 'Show my progress', 'Check my muscle recovery']:
        before = sum(c.queries for c in connections)
        start = perf_counter()
        chatbot.chat(chatbot.ChatMessage(text=prompt, session_id=session['session_id']), user)
        print(json.dumps({'message': prompt, 'queries': sum(c.queries for c in connections) - before,
                          'seconds': round(perf_counter() - start, 4)}))
