import { test } from 'node:test';
import assert from 'node:assert/strict';
import { api, sendChat } from './api.js';

globalThis.sessionStorage = { getItem: () => null };

test('expired chat resumes once with a new session before retrying the message', async () => {
  const calls = [];
  const replies = [{ status: 410, detail: 'Expired' }, { status: 200, session_id: 'fresh' }, { status: 200, message: 'Reply', session_id: 'fresh' }];
  globalThis.fetch = async (url, options) => {
    calls.push([url, options.body ? JSON.parse(options.body) : null]);
    const reply = replies.shift();
    return { ok: reply.status === 200, status: reply.status, json: async () => reply };
  };
  const result = await sendChat('Question', 'expired', 'ru');
  assert.equal(result.message, 'Reply');
  assert.equal(calls.length, 3);
  assert.equal(calls[1][0], '/chat/sessions');
  assert.deepEqual(calls[2][1], { text: 'Question', session_id: 'fresh', language: 'ru' });
});

test('server failures are not automatically retried because actions may have succeeded', async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return { ok: false, status: 500, json: async () => ({ detail: 'Failed' }) };
  };
  await assert.rejects(sendChat('Create a plan', 'active', 'en'), /Failed/);
  assert.equal(calls, 1);
});

test('proxy failures explain the connection problem in both interface languages', async () => {
  globalThis.fetch = async () => ({ ok: false, status: 502, json: async () => { throw new Error('HTML proxy page'); } });
  for (const [language, expected] of [['en', /Cannot reach the server/], ['ru', /Нет связи с сервером/]]) {
    globalThis.localStorage = { getItem: () => language };
    await assert.rejects(api('/students'), error => error.status === 502 && expected.test(error.message));
  }
});
