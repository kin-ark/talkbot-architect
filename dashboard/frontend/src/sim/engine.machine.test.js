import { describe, it, expect } from 'vitest';
import { start, choose } from './engine';

// --- tiny summary builders ---
const talk = (uuid, text, branches) => ({ uuid, label: uuid, node_type: 'talk', text, branches, data: {} });
const exit = (uuid) => ({ uuid, label: uuid, node_type: 'exit', text: 'Goodbye', branches: [{ label: 'exit', kind: 'exit', terminal: 'hangup' }], data: {} });
const br = (label, target_uuid, extra = {}) => ({ label, kind: 'intent', target_uuid: target_uuid || null, target_component: null, target_kb: null, terminal: null, ...extra });
const comp = (uuid, nodes, extra = {}) => ({
  uuid, name: uuid, sort_index: 0, entry_uuid: nodes[0].uuid, root_uuids: [nodes[0].uuid],
  parent_uuid: '0', nodes: Object.fromEntries(nodes.map((n) => [n.uuid, n])), ...extra,
});

describe('start', () => {
  it('speaks the entry node and awaits a choice', () => {
    const summary = { components: [comp('c1', [
      talk('t1', 'Hello', [br('Positive', 't2'), br('Unclassified', 't2')]),
      exit('t2'),
    ])] };
    const s = start(summary, 'c1', {});
    expect(s.status).toBe('awaiting_choice');
    expect(s.transcript.at(-1)).toEqual({ role: 'bot', label: 't1', text: 'Hello' });
    expect(s.choices.map((c) => c.label)).toEqual(['Positive', 'Unclassified']);
  });
  it('no-entry component ends gracefully', () => {
    const summary = { components: [{ uuid: 'c1', name: 'c1', nodes: {}, entry_uuid: null, root_uuids: [] }] };
    const s = start(summary, 'c1', {});
    expect(s.status).toBe('ended');
    expect(s.endReason).toBe('no_entry');
  });
});

describe('choose', () => {
  it('advances to the chosen branch target, then to exit', () => {
    const summary = { components: [comp('c1', [
      talk('t1', 'Hi', [br('Positive', 't2')]),
      exit('t2'),
    ])] };
    let s = start(summary, 'c1', {});
    s = choose(s, summary, 0);
    expect(s.status).toBe('ended');
    expect(s.endReason).toBe('hangup');
    expect(s.transcript.some((r) => r.role === 'you' && r.label === 'Positive')).toBe(true);
  });
});

describe('conditional auto-eval', () => {
  const cnode = (uuid, branches, defs) => ({ uuid, label: uuid, node_type: 'conditional', text: '', branches, data: { branch: defs } });
  const build = () => ({ components: [comp('c1', [
    talk('t1', 'Ask', [br('Positive', 'k1')]),
    cnode('k1',
      [{ label: 'Paid', kind: 'condition', target_uuid: 'paidExit' }, { label: 'Default', kind: 'default', target_uuid: 'defExit' }],
      [{ name: 'Paid', branch_judgement_condition: [{ left_value: 'S', operator: '=', right_value: 'paid' }] }]),
    exit('paidExit'), exit('defExit'),
  ])] });
  it('routes on a set var', () => {
    let s = start(build(), 'c1', { S: 'paid' });
    s = choose(s, build(), 0);
    expect(s.transcript.some((r) => r.role === 'system' && r.text === 'condition → Paid')).toBe(true);
  });
  it('falls to Default on an unset var', () => {
    let s = start(build(), 'c1', {});
    s = choose(s, build(), 0);
    expect(s.transcript.some((r) => r.role === 'system' && r.text === 'condition → Default')).toBe(true);
  });
});

describe('assign', () => {
  it('updates var state and notes it, then continues', () => {
    const anode = { uuid: 'a1', label: 'a1', node_type: 'variable_assignment', text: '',
      branches: [{ label: 'Default', kind: 'next', target_uuid: 'e1' }],
      data: { value_assignment: [{ variable: { name: 'SAL' }, assign: { func_code: 'OPT_VALUE_ASSIGNMENT', params: [{ name: 'value_to_assign', value: 'Bapak' }] } }] } };
    const summary = { components: [comp('c1', [
      talk('t1', 'Hi', [br('Positive', 'a1')]), anode, exit('e1'),
    ])] };
    let s = start(summary, 'c1', {});
    s = choose(s, summary, 0);
    expect(s.varState.SAL).toBe('Bapak');
    expect(s.transcript.some((r) => r.text === 'set SAL = Bapak')).toBe(true);
    expect(s.endReason).toBe('hangup');
  });
});

describe('goto_kb', () => {
  it('speaks the first KB answer and ends', () => {
    const kbnode = { uuid: 'g1', label: 'g1', node_type: 'goto_kb', text: '',
      branches: [{ label: 'kb', kind: 'exit', target_kb: 7 }], data: {} };
    const summary = {
      components: [comp('c1', [talk('t1', 'Hi', [br('Positive', 'g1')]), kbnode])],
      knowledge_bases: [{ knowledge_id: 7, title: 'Payment', answers: [{ text: 'Pay here', after: 'wait' }], multi_round: null }],
    };
    let s = start(summary, 'c1', {});
    s = choose(s, summary, 0);
    expect(s.transcript.some((r) => r.role === 'bot' && r.text === 'Pay here')).toBe(true);
    expect(s.status).toBe('ended');
  });
  it('descends into a multi-round delegate', () => {
    const kbnode = { uuid: 'g1', label: 'g1', node_type: 'goto_kb', text: '',
      branches: [{ label: 'kb', kind: 'exit', target_kb: 8 }], data: {} };
    const mrComp = comp('mr1', [talk('m1', 'MR turn', [br('Positive', 'm2')]), exit('m2')]);
    const summary = {
      components: [comp('c1', [talk('t1', 'Hi', [br('Positive', 'g1')]), kbnode])],
      knowledge_bases: [{ knowledge_id: 8, title: 'MRKB', answers: [{ text: 'Let me help', after: 'wait' }], multi_round: { components: [mrComp] } }],
    };
    let s = start(summary, 'c1', {});
    s = choose(s, summary, 0);
    expect(s.transcript.some((r) => r.role === 'bot' && r.text === 'MR turn')).toBe(true);
    expect(s.status).toBe('awaiting_choice');
  });
  it('absent KB ends external', () => {
    const kbnode = { uuid: 'g1', label: 'g1', node_type: 'goto_kb', text: '', branches: [{ label: 'kb', kind: 'exit', target_kb: 99 }], data: {} };
    const summary = { components: [comp('c1', [talk('t1', 'Hi', [br('Positive', 'g1')]), kbnode])], knowledge_bases: [] };
    let s = start(summary, 'c1', {});
    s = choose(s, summary, 0);
    expect(s.endReason).toBe('external');
  });
});

describe('graceful stops', () => {
  it('missing target node ends external', () => {
    const summary = { components: [comp('c1', [talk('t1', 'Hi', [br('Positive', 'ghost')])])] };
    let s = start(summary, 'c1', {});
    s = choose(s, summary, 0);
    expect(s.endReason).toBe('external');
  });
  it('loop guard stops a cycle', () => {
    const summary = { components: [comp('c1', [
      { uuid: 'a', label: 'a', node_type: 'variable_assignment', text: '', branches: [{ label: 'n', kind: 'next', target_uuid: 'a' }], data: { value_assignment: [] } },
    ])] };
    const s = start(summary, 'c1', {});
    expect(s.endReason).toBe('loop_guard');
  });
});
