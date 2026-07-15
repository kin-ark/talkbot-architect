// Pure prep helpers for the Flow Simulator. No React / fetch / DOM.

const _VAR_ID_RE = /\{([^}]+)\}/g;

// Conditional-referenced variable names that no assign node produces.
export function neededVars(summary) {
  const referenced = new Set();
  const assigned = new Set();
  for (const c of summary?.components || []) {
    for (const n of Object.values(c.nodes || {})) {
      if (n.node_type === 'conditional') {
        for (const def of n.data?.branch || []) {
          for (const cond of def.branch_judgement_condition || []) {
            const lv = String(cond.left_value ?? '');
            let m; let matched = false;
            _VAR_ID_RE.lastIndex = 0;
            while ((m = _VAR_ID_RE.exec(lv)) !== null) { referenced.add(m[1]); matched = true; }
            if (!matched && lv) referenced.add(lv);
          }
        }
      } else if (n.node_type === 'variable_assignment') {
        for (const va of n.data?.value_assignment || []) {
          if (va?.variable?.name) assigned.add(va.variable.name);
        }
      }
    }
  }
  return [...referenced].filter((v) => !assigned.has(v)).sort();
}

// Every variable the flow READS but the simulator cannot produce (so the setup
// form can prompt for it): conditional refs + talk-text {VAR} (referenced_vars)
// + computed-function assigns, minus literal (OPT_VALUE_ASSIGNMENT) assigns.
export function promptableVars(summary) {
  const referenced = new Set();
  const computed = new Set();
  const literal = new Set();
  for (const c of summary?.components || []) {
    for (const n of Object.values(c.nodes || {})) {
      if (n.node_type === 'conditional') {
        for (const def of n.data?.branch || []) {
          for (const cond of def.branch_judgement_condition || []) {
            const lv = String(cond.left_value ?? '');
            let m; let matched = false;
            _VAR_ID_RE.lastIndex = 0;
            while ((m = _VAR_ID_RE.exec(lv)) !== null) { referenced.add(m[1]); matched = true; }
            if (!matched && lv) referenced.add(lv);
          }
        }
      } else if (n.node_type === 'variable_assignment') {
        for (const va of n.data?.value_assignment || []) {
          const name = va?.variable?.name;
          if (!name) continue;
          if (va?.assign?.func_code === 'OPT_VALUE_ASSIGNMENT') literal.add(name);
          else computed.add(name);
        }
      }
      for (const v of n.referenced_vars || []) referenced.add(v);
    }
  }
  return [...new Set([...referenced, ...computed])].filter((v) => !literal.has(v)).sort();
}

// The SpeechIntent ids that fire a talk node's named branch.
export function intentsForBranch(node, branchLabel) {
  const aci = node?.data?.all_client_intent || [];
  const entry = aci.find((e) => e.name === branchLabel);
  return (entry?.intents || []).map((i) => i.intentId);
}

// Best default starting component: main-flow (parent_uuid "0"/null) first, then lowest sort_index.
export function defaultStartComponent(summary) {
  const comps = [...(summary?.components || [])];
  if (!comps.length) return null;
  comps.sort((a, b) => {
    const pa = (a.parent_uuid === '0' || a.parent_uuid == null) ? 0 : 1;
    const pb = (b.parent_uuid === '0' || b.parent_uuid == null) ? 0 : 1;
    if (pa !== pb) return pa - pb;
    return (a.sort_index ?? 0) - (b.sort_index ?? 0);
  });
  return comps[0].uuid;
}
