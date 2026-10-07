import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } } });
const env = import.meta.env || {};
const base = env.DEV ? '/api' : (env.VITE_API_URL || '');
function connectionMessage(status) {
  const ru = globalThis.localStorage?.getItem('smartpe-language') === 'ru';
  return ru
    ? `Нет связи с сервером (${status}). Попробуйте ещё раз. Если ошибка повторяется, откройте актуальную ссылку приложения.`
    : `Cannot reach the server (${status}). Try again. If this continues, open the current app link.`;
}
export async function api(path, { method = 'GET', body, signal } = {}) {
  const token = sessionStorage.getItem('smartpe-token');
  const timeout = AbortSignal.timeout(path.startsWith('/chat') ? 45_000 : 120_000);
  const response = await fetch(base + path, {
    method, signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/login')) window.dispatchEvent(new Event('smartpe-expired'));
    const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join('; ') : data.detail;
    const unavailable = [502, 503, 504].includes(response.status);
    const error = new Error(detail || (unavailable ? connectionMessage(response.status) : `Request failed (${response.status})`));
    error.status = response.status;
    throw error;
  }
  return data;
}

export const fetcher = path => ({ signal }) => api(path, { signal });

// A 410 is raised before any action, so replacing that session and retrying is safe.
export async function sendChat(text, sessionId, language) {
  let active = sessionId;
  const send = () => api('/chat/', { method: 'POST', body: { text, session_id: active, language } });
  try {
    return await send();
  } catch (err) {
    if (err.status !== 410) throw err;
    const started = await api('/chat/sessions', { method: 'POST' });
    active = started.session_id;
    return send();
  }
}
