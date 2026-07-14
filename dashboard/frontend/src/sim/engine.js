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
  const right = cond?.right_value;
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
  const next = { ...(varState || {}) };
  const notes = [];
  for (const va of node?.data?.value_assignment || []) {
    const name = va?.variable?.name;
    if (!name) continue;
    if (va?.assign?.func_code === 'OPT_VALUE_ASSIGNMENT') {
      const params = va.assign.params || [];
      const p = params.find((x) => x.name === 'value_to_assign') || params[0];
      const value = p?.value ?? '';
      next[name] = value;
      notes.push(`set ${name} = ${value}`);
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
