import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function uploadSession(file) {
  const fd = new FormData();
  fd.append('file', file);
  const { data } = await axios.post(`${BASE}/session`, fd);
  return data;
}
export async function sendChat(message) {
  const { data } = await axios.post(`${BASE}/chat`, { message });
  return data;
}
export async function applyPending() { return (await axios.post(`${BASE}/apply`)).data; }
export async function undo() { return (await axios.post(`${BASE}/undo`)).data; }
export async function redo() { return (await axios.post(`${BASE}/redo`)).data; }
export async function getSummary() { return (await axios.get(`${BASE}/summary`)).data; }
export async function getFindings() { return (await axios.get(`${BASE}/findings`)).data; }
export function exportUrl() { return `${BASE}/export`; }
export async function getConfig() { return (await axios.get(`${BASE}/config`)).data; }
export async function updateConfig(body) { return (await axios.put(`${BASE}/config`, body)).data; }
export async function clearConfig() { return (await axios.post(`${BASE}/config/clear`)).data; }
