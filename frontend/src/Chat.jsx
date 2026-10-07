import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Sparkles, Send, RefreshCw, ArrowUpRight, ShieldCheck, HeartPulse } from 'lucide-react';
import { api, fetcher, queryClient, sendChat } from './api';
import { useLocale, Button, SectionHeading, Notice } from './components';

export default function Chat() {
  const { t, language } = useLocale();
  const [saved] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('smartpe-chat')) || {}; }
    catch { return {}; }
  });
  const [messages, setMessages] = useState(saved.messages || []);
  const [text, setText] = useState('');
  const [session, setSession] = useState(saved.session || null);
  const [error, setError] = useState('');
  const [replyStatus, setReplyStatus] = useState(null);
  const bottom = useRef();
  const initialized = useRef(false);
  const model = useQuery({ queryKey: ['/chat/status'], queryFn: fetcher('/chat/status'), refetchInterval: 60_000, retry: false });
  const status = replyStatus || model.data;
  const start = useMutation({ mutationFn: () => api('/chat/sessions', { method: 'POST' }), onSuccess: data => {
    setSession(data.session_id); setMessages([]); setError('');
  } });
  const send = useMutation({ mutationFn: prompt => sendChat(prompt, session, language), onSuccess: data => {
    setSession(data.session_id);
    setReplyStatus(data.model_status);
    setMessages(m => [...m, { role: 'assistant', text: data.message }]);
    if (['plan_generated', 'feedback_recorded'].includes(data.action)) {
      queryClient.invalidateQueries({ predicate: q => q.queryKey[0] !== 'me' });
    }
  }, onError: (err, prompt) => {
    setError(err.name === 'TimeoutError' ? t('The reply took too long. Please try again.', 'Ответ занял слишком много времени. Попробуйте ещё раз.') : err.message);
    setText(prompt);
  } });
  useEffect(() => {
    if (!initialized.current && !session) { initialized.current = true; start.mutate(); }
  }, []);
  useEffect(() => {
    if (session) sessionStorage.setItem('smartpe-chat', JSON.stringify({ session, messages: messages.slice(-80) }));
  }, [session, messages]);
  useEffect(() => { setReplyStatus(null); }, [model.data]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [messages, send.isPending]);
  function submit(prompt) {
    if (!prompt.trim() || send.isPending || !session || start.isPending) return;
    setError(''); setMessages(m => [...m, { role: 'user', text: prompt }]); setText(''); send.mutate(prompt);
  }
  const offline = {
    disabled: t('AI generation is turned off.', 'Генерация ИИ выключена.'),
    model_missing: t('The chat model is not installed.', 'Модель чат-бота не установлена.'),
    offline: t('The AI server is offline.', 'Сервер ИИ недоступен.'),
    authentication_failed: t('The AI connection needs a valid API key.', 'Для подключения ИИ нужен действующий API-ключ.'),
    timeout: t('The AI model did not reply in time.', 'Модель ИИ не ответила вовремя.'),
    sdk_missing: t('The AI client is not installed on the server.', 'На сервере не установлен клиент ИИ.'),
  };
  return <>
    <SectionHeading eyebrow={t('YOUR PERSONAL AI COACH', 'ВАШ ПЕРСОНАЛЬНЫЙ ИИ-ТРЕНЕР')} title={t('Let’s talk about you.', 'Поговорим о вас.')} text={t('A little guidance for your next step.', 'Поддержка на пути к следующей цели.')} action={<Button variant="secondary" icon={RefreshCw} busy={start.isPending} disabled={send.isPending} onClick={() => start.mutate()}>{t('New conversation', 'Новый разговор')}</Button>}/>
    {status && !status.ready && status.reason !== 'not_checked' && <Notice>{offline[status.reason] || t('AI generation is temporarily unavailable.', 'Генерация ИИ временно недоступна.')} {t('You can still check your workouts, progress and recovery.', 'Вы можете проверить тренировки, прогресс и восстановление.')}</Notice>}
    <div className="chat-layout"><section className="chat-panel">
      <div className="chat-heading"><span className="stat-icon mint"><Sparkles size={22}/></span><div><strong>Smart PE {t('Coach', 'Тренер')}</strong><small><span className="live-dot"/>{start.isPending ? t('Loading your profile…', 'Загрузка профиля…') : !session ? t('Conversation not ready', 'Разговор ещё не готов') : status?.ready ? t('AI connected', 'ИИ подключён') : t('Workout assistant', 'Помощник по тренировкам')}</small></div></div>
      <div className="chat-messages" role="log" aria-live="polite">
        {!messages.length && <div className="chat-welcome"><span className="empty-icon"><Sparkles size={32}/></span><h2>{t('What’s on your mind?', 'Что вас интересует?')}</h2><p>{t('Your profile is loaded at the start of this conversation. Ask me about your workouts, progress or recovery.', 'Ваш профиль загружается в начале разговора. Спросите о тренировках, прогрессе или восстановлении.')}</p><div className="prompt-grid">{[t('Show my progress', 'Покажи мой прогресс'), t('Check my muscle recovery', 'Проверь восстановление мышц'), t('Explain my latest plan', 'Объясни мой последний план'), t('Hello! What can you do?', 'Привет! Что ты умеешь?')].map(p => <button key={p} disabled={!session || start.isPending || send.isPending} onClick={() => submit(p)}>{p}<ArrowUpRight size={16}/></button>)}</div></div>}
        {messages.map((m, i) => <div key={i} className={`chat-message ${m.role}`}><span className="message-avatar">{m.role === 'assistant' ? <Sparkles size={17}/> : t('You', 'Вы')}</span><div>{m.text}</div></div>)}
        {send.isPending && <div className="thinking"><span/><span/><span/>{t('Preparing a reply…', 'Готовлю ответ…')}</div>}<div ref={bottom}/>
      </div>
      {(error || start.isError) && <Notice>{error || start.error.message}</Notice>}
      {start.isError && <Button variant="secondary" onClick={() => start.mutate()}>{t('Retry connection', 'Повторить подключение')}</Button>}
      <form className="chat-composer" onSubmit={e => { e.preventDefault(); submit(text); }}><textarea aria-label={t('Message your coach', 'Сообщение тренеру')} placeholder={t('Ask your coach anything about your training…', 'Спросите тренера о ваших тренировках…')} rows="2" maxLength="4000" value={text} onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(text); } }}/><button className="send-button" aria-label={t('Send message', 'Отправить сообщение')} disabled={!text.trim() || send.isPending || !session || start.isPending}><Send size={20}/></button></form>
    </section><aside className="chat-tips"><span className="eyebrow">{t('MADE PERSONAL', 'ПЕРСОНАЛЬНЫЙ ПОДХОД')}</span><h3>{t('Your context. A better conversation.', 'Ваш контекст. Полезный разговор.')}</h3><p>{t('Your health profile, recent plan, recovery and progress help your coach respond with context.', 'Профиль здоровья, последний план, восстановление и прогресс помогают тренеру отвечать с учётом ваших данных.')}</p><div className="tip"><ShieldCheck size={20}/>{t('Only your own student data', 'Только ваши данные')}</div><div className="tip"><RefreshCw size={20}/>{t('Refreshes after changes', 'Обновляется при изменениях')}</div><div className="tip"><HeartPulse size={20}/>{t('Talk to your teacher about pain or injury', 'При боли или травме обратитесь к преподавателю')}</div></aside></div>
  </>;
}
