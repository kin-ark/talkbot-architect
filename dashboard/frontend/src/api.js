import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function uploadSession(file) {
  const fd = new FormData();
  fd.append('file', file);
  const { data } = await axios.post(`${BASE}/session`, fd);
  return data;
}
export async function cancelChat() { return (await axios.post(`${BASE}/chat/cancel`)).data; }
export async function applyPending() { return (await axios.post(`${BASE}/apply`)).data; }
export async function undo() { return (await axios.post(`${BASE}/undo`)).data; }
export async function redo() { return (await axios.post(`${BASE}/redo`)).data; }
export async function getSummary() { return (await axios.get(`${BASE}/summary`)).data; }
export async function getFindings() { return (await axios.get(`${BASE}/findings`)).data; }
export function exportUrl() { return `${BASE}/export`; }
export async function getConfig() { return (await axios.get(`${BASE}/config`)).data; }
export async function updateConfig(body) { return (await axios.put(`${BASE}/config`, body)).data; }
export async function clearConfig() { return (await axios.post(`${BASE}/config/clear`)).data; }
export async function startBlank() { return (await axios.post(`${BASE}/session/blank`)).data; }
export async function getSession() { return (await axios.get(`${BASE}/session`)).data; }
export async function clearSession() { return (await axios.post(`${BASE}/session/clear`)).data; }

export async function streamChat(message, { onEvent, signal } = {}) {
  let resp;
  try {
    resp = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
      signal,
    });
  } catch (e) {
    if (e?.name === 'AbortError') return;
    throw e;
  }
  if (!resp.ok || !resp.body) throw new Error(`stream failed: ${resp.status}`);
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf('\n\n')) !== -1) {
        const frame = buf.slice(0, nl);
        buf = buf.slice(nl + 2);
        const line = frame.split('\n').find((l) => l.startsWith('data: '));
        if (line) onEvent?.(JSON.parse(line.slice(6)));
      }
    }
  } catch (e) {
    if (e?.name !== 'AbortError') throw e;
  }
}
