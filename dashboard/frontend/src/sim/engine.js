// Flow Simulator engine — pure state machine over a summarize() payload.
// No React / fetch / DOM. Part 1: primitives (Task 2). Part 2: machine (Task 3).

export const MAX_STEPS = 200;

// Index every component reachable in the summary, including KB multi-round delegates.
export function buildIndex(summary) {
  const byUuid = new Map();
  const kbById = new Map();
  const addComps = (comps) => { for (const c of comps || []) byUuid.set(c.uuid, c); };
  addComps(summary?.components);
  for (const kb of summary?.knowledge_bases || []) {
    kbById.set(kb.knowledge_id, kb);
    if (kb.multi_round?.components) addComps(kb.multi_round.components);
  }
  return { byUuid, kbById };
}

export function entryNode(comp) {
  return comp?.entry_uuid || (comp?.root_uuids && comp.root_uuids[0]) || null;
}

// The active node object for a running state (resolves KB/nested components too).
export function currentNode(summary, state) {
  const { byUuid } = buildIndex(summary);
  return byUuid.get(state?.componentUuid)?.nodes?.[state?.nodeUuid] || null;
}

export function hasTarget(b) {
  return Boolean(b && (b.target_uuid || b.target_component || b.target_kb || b.terminal));
}

const _VAR_ID_RE = /^\{(.+)\}$/;
function varKey(left) {
  const m = _VAR_ID_RE.exec(String(left ?? ''));
  return m ? m[1] : String(left ?? '');
}

// Canonicalize friendly operator tokens to the deploy-valid set.
function normOp(op) {
  const map = { IsNull: 'Null', NotNull: 'Not null', NotIn: 'Not in', Contains: 'Contain' };
  return map[op] || op;
}

function asNum(x) { const n = Number(x); return Number.isNaN(n) ? null : n; }

export function evalCondition(cond, varState) {
  const vs = varState || {};
  const key = varKey(cond?.left_value);
  const has = Object.prototype.hasOwnProperty.call(vs, key);
  const left = has ? vs[key] : undefined;
  let right = cond?.right_value;
  const rvVar = cond?.value_var || cond?.right_value_var;
  if (cond?.type === 'variable' || rvVar) {
    const rname = varKey(rvVar || cond?.right_value);
    right = Object.prototype.hasOwnProperty.call(vs, rname) ? vs[rname] : undefined;
  }
  const op = normOp(cond?.operator);
  if (op === 'Null') return !has || left === '' || left == null;
  if (op === 'Not null') return has && left !== '' && left != null;
  if (!has) return false; // any comparison on an unset var is false
  switch (op) {
    case '=': return String(left) === String(right);
    case '!=': return String(left) !== String(right);
    case 'In': return String(right ?? '').split(',').map((s) => s.trim()).includes(String(left));
    case 'Not in': return !String(right ?? '').split(',').map((s) => s.trim()).includes(String(left));
    case 'Contain': return String(left).includes(String(right ?? ''));
    case '>': case '>=': case '<': case '<=': {
      const a = asNum(left); const b = asNum(right);
      if (a == null || b == null) return false;
      if (op === '>') return a > b;
      if (op === '>=') return a >= b;
      if (op === '<') return a < b;
      return a <= b;
    }
    default: return false;
  }
}

export function evalConditionGroup(judgements, varState) {
  const arr = judgements || [];
  if (!arr.length) return false;
  return arr.every((c) => evalCondition(c, varState));
}

export function pickConditionalBranch(node, varState) {
  const defs = node?.data?.branch || [];
  const branches = node?.branches || [];
  for (const def of defs) {
    const j = def.branch_judgement_condition || [];
    if (j.length && evalConditionGroup(j, varState)) {
      const edge = branches.find((b) => b.label === def.name);
      if (edge) return { edge, name: def.name };
    }
  }
  const def = branches.find((b) => b.kind === 'default') || branches.find((b) => b.label === 'Default');
  return { edge: def || null, name: def ? def.label : 'Default' };
}

export function applyAssign(node, varState) {
  const vs = varState || {};
  const next = { ...vs };
  const notes = [];
  for (const va of node?.data?.value_assignment || []) {
    const name = va?.variable?.name;
    if (!name) continue;
    if (va?.assign?.func_code === 'OPT_VALUE_ASSIGNMENT') {
      const params = va.assign.params || [];
      const p = params.find((x) => x.name === 'value_to_assign') || params[0];
      if (p?.type === 'variable') {
        const rname = String(p.value ?? '');
        const value = Object.prototype.hasOwnProperty.call(vs, rname) ? vs[rname] : '';
        next[name] = value;
        notes.push(`set ${name} = ${value} (from ${rname})`);
      } else {
        const value = p?.value ?? '';
        next[name] = value;
        notes.push(`set ${name} = ${value}`);
      }
    } else {
      next[name] = '(computed)';
      notes.push(`set ${name} = (computed)`);
    }
  }
  return { varState: next, notes };
}

export function mapChoices(node) {
  return (node?.branches || []).map((b, i) => ({
    label: b.label, kind: b.kind, branchIndex: i,
    disabled: !hasTarget(b), reason: hasTarget(b) ? null : 'dead end',
  }));
}

// ---------------------------------------------------------------------------
// Part 2: the state machine (Task 3)
// ---------------------------------------------------------------------------

function botRow(label, text) { return { role: 'bot', label, text: text || '' }; }
function sysRow(text) { return { role: 'system', text }; }
function youRow(label) { return { role: 'you', label }; }

function end(state, reason, note) {
  const transcript = note ? [...state.transcript, sysRow(note)] : state.transcript;
  return { ...state, status: 'ended', endReason: reason, choices: [], transcript };
}

export function start(summary, componentUuid, varState) {
  const { byUuid } = buildIndex(summary);
  const base = {
    componentUuid, nodeUuid: null, varState: { ...(varState || {}) },
    callStack: [], transcript: [], status: 'running', choices: [], endReason: null, steps: 0,
  };
  const comp = byUuid.get(componentUuid);
  if (!comp) return end(base, 'external', 'Component not found — cannot simulate.');
  const entry = entryNode(comp);
  if (!entry) return end(base, 'no_entry', 'No entry node — cannot simulate this component.');
  return _run({ ...base, nodeUuid: entry }, summary);
}

export function choose(state, summary, branchIndex) {
  if (state.status !== 'awaiting_choice') return state;
  const { byUuid } = buildIndex(summary);
  const node = byUuid.get(state.componentUuid)?.nodes?.[state.nodeUuid];
  const edge = node?.branches?.[branchIndex];
  if (!edge) return state;
  let s = { ...state, status: 'running', choices: [], steps: 0, transcript: [...state.transcript, youRow(edge.label)] };
  s = _followEdge(s, summary, edge);
  return _run(s, summary);
}

function _followEdge(state, summary, edge) {
  const { byUuid } = buildIndex(summary);
  if (edge.terminal === 'hangup') return end(state, 'hangup');
  if (edge.terminal === 'transfer') return end(state, 'transfer');
  if (edge.target_uuid) return { ...state, nodeUuid: edge.target_uuid };
  if (edge.target_component) {
    const c = byUuid.get(edge.target_component);
    if (!c) return end(state, 'external', 'Leaves this export (library/external) — ends here.');
    const entry = entryNode(c);
    if (!entry) return end(state, 'no_entry', 'Target component has no entry — ends here.');
    return { ...state, componentUuid: edge.target_component, nodeUuid: entry };
  }
  if (edge.target_kb) return _enterKb(state, summary, edge.target_kb);
  return end(state, 'dead_end', 'Dead end (no target wired) — ends here.');
}

function _enterKb(state, summary, kbId) {
  const { kbById } = buildIndex(summary);
  const kb = kbById.get(kbId);
  if (!kb) return end(state, 'external', 'KB not in this export (library) — ends here.');
  const answer = (kb.answers || [])[0];
  const t = [...state.transcript, botRow(`KB: ${kb.title}`, answer ? answer.text : '(no answer)')];
  const mr = kb.multi_round?.components;
  if (mr && mr.length) {
    const c = mr[0];
    const entry = entryNode(c);
    if (entry) return { ...state, transcript: [...t, sysRow(`entered multi-round: ${c.name}`)], componentUuid: c.uuid, nodeUuid: entry };
  }
  return end({ ...state, transcript: t }, 'ended');
}

function _enterNested(state, summary, node) {
  const { byUuid } = buildIndex(summary);
  const childUuid = node.data?.subComponentUuid;
  const child = childUuid ? byUuid.get(childUuid) : null;
  if (!child) return end(state, 'external', 'Nested child not in this export (library) — ends here.');
  const entry = entryNode(child);
  if (!entry) return end(state, 'no_entry', 'Nested child has no entry — ends here.');
  const exitMap = {};
  for (const b of node.branches || []) exitMap[b.label] = b.target_uuid || null;
  const callStack = [...state.callStack, { parentComponentUuid: state.componentUuid, exitMap }];
  return { ...state, callStack, componentUuid: childUuid, nodeUuid: entry,
    transcript: [...state.transcript, sysRow(`entered nested: ${child.name}`)] };
}

function _exitNested(state, node) {
  const stack = state.callStack;
  if (!stack.length) return end(state, 'ended', 'Reached a return port with no caller — ends here.');
  const ctx = stack[stack.length - 1];
  const name = node.data?.name || (node.branches || [])[0]?.label;
  const target = ctx.exitMap[name];
  const callStack = stack.slice(0, -1);
  if (!target) return end({ ...state, callStack }, 'external', 'Return port not wired in parent — ends here.');
  return { ...state, callStack, componentUuid: ctx.parentComponentUuid, nodeUuid: target };
}

function _run(state, summary) {
  const { byUuid } = buildIndex(summary);
  let s = state;
  while (true) {
    if (s.status !== 'running') return s;
    if (s.steps >= MAX_STEPS) return end(s, 'loop_guard', 'Loop guard hit — stopping.');
    s = { ...s, steps: s.steps + 1 };
    const node = byUuid.get(s.componentUuid)?.nodes?.[s.nodeUuid];
    if (!node) return end(s, 'external', 'Leaves this export (missing node) — ends here.');
    switch (node.node_type) {
      case 'talk': {
        if ((node.branches || []).length === 0)
          return end(s, 'dead_end', 'Talk node has no outgoing branch — ends here.');
        let s2 = s;
        const va = node.data?.value_assignment;
        if (va && va.length) {
          const { varState, notes } = applyAssign(node, s.varState);
          s2 = { ...s, varState, transcript: [...s.transcript, ...notes.map(sysRow)] };
        }
        return { ...s2, status: 'awaiting_choice', choices: mapChoices(node),
          transcript: [...s2.transcript, botRow(node.label, node.text)] };
      }
      case 'talk_continue': {
        const s2 = { ...s, transcript: [...s.transcript, botRow(node.label, node.text)] };
        const ret = (node.branches || []).find((b) => b.target_component);
        if (ret) { s = _followEdge(s2, summary, ret); break; }
        return end(s2, 'talk_continue', 'Waiting for the caller (talk-continue) — ends here.');
      }
      case 'conditional': {
        const { edge, name } = pickConditionalBranch(node, s.varState);
        const s2 = { ...s, transcript: [...s.transcript, sysRow(`condition → ${name}`)] };
        if (!edge) return end(s2, 'dead_end', 'Conditional has no matching or default branch — ends here.');
        s = _followEdge(s2, summary, edge); break;
      }
      case 'variable_assignment': {
        const { varState, notes } = applyAssign(node, s.varState);
        const s2 = { ...s, varState, transcript: [...s.transcript, ...notes.map(sysRow)] };
        const nxt = (node.branches || []).find((b) => hasTarget(b));
        if (!nxt) return end(s2, 'dead_end', 'Assign node has no onward branch — ends here.');
        s = _followEdge(s2, summary, nxt); break;
      }
      case 'goto_component':
      case 'goto_mr': {
        const edge = (node.branches || [])[0];
        if (!edge) return end(s, 'dead_end', 'Jump has no target — ends here.');
        const s2 = { ...s, transcript: [...s.transcript, sysRow(`jumped to component: ${edge.label || node.label}`)] };
        s = _followEdge(s2, summary, edge); break;
      }
      case 'nested_component':
        s = _enterNested(s, summary, node); break;
      case 'exit_port':
        s = _exitNested(s, node); break;
      case 'goto_kb': {
        const edge = (node.branches || [])[0];
        if (!edge || !edge.target_kb) return end(s, 'dead_end', 'goto_kb has no KB target — ends here.');
        s = _enterKb(s, summary, edge.target_kb); break;
      }
      case 'exit':
        return end({ ...s, transcript: [...s.transcript, botRow(node.label, node.text)] }, 'hangup');
      case 'transfer':
        return end({ ...s, transcript: [...s.transcript, botRow(node.label, node.text)] }, 'transfer');
      default:
        return end(s, 'external', `Unsupported node type (${node.node_type}) — ends here.`);
    }
  }
}
