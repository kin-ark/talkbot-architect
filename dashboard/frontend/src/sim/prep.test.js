import { describe, it, expect } from 'vitest';
import { neededVars, intentsForBranch, defaultStartComponent } from './prep';

const cond = (uuid, judgements) => ({
  uuid, label: uuid, node_type: 'conditional', text: '', branches: [], data: { branch: judgements },
});
const assign = (uuid, names) => ({
  uuid, label: uuid, node_type: 'variable_assignment', text: '', branches: [],
  data: { value_assignment: names.map((n) => ({ variable: { name: n }, assign: { func_code: 'OPT_VALUE_ASSIGNMENT', params: [{ name: 'value_to_assign', value: 'x' }] } })) },
});
const comp = (uuid, nodes, extra = {}) => ({
  uuid, name: uuid, sort_index: 0, entry_uuid: nodes[0]?.uuid || null,
  root_uuids: nodes[0] ? [nodes[0].uuid] : [], parent_uuid: '0',
  nodes: Object.fromEntries(nodes.map((n) => [n.uuid, n])), ...extra,
});

describe('neededVars', () => {
  it('returns conditional-referenced vars minus assign-produced, sorted', () => {
    const summary = { components: [comp('c1', [
      cond('k1', [{ name: 'Paid', branch_judgement_condition: [{ left_value: 'PAYMENT_STATUS', operator: '=', right_value: 'paid' }] }]),
      cond('k2', [{ name: 'Big', branch_judgement_condition: [{ left_value: 'AMOUNT', operator: '>', right_value: '100' }] }]),
      assign('a1', ['AMOUNT']),
    ])] };
    expect(neededVars(summary)).toEqual(['PAYMENT_STATUS']); // AMOUNT is assigned → excluded
  });

  it('unwraps {varId} braces in left_value', () => {
    const summary = { components: [comp('c1', [
      cond('k1', [{ name: 'X', branch_judgement_condition: [{ left_value: '{9001}', operator: 'Null', right_value: '' }] }]),
    ])] };
    expect(neededVars(summary)).toEqual(['9001']);
  });

  it('empty / missing summary → []', () => {
    expect(neededVars(null)).toEqual([]);
    expect(neededVars({ components: [] })).toEqual([]);
  });
});

describe('intentsForBranch', () => {
  it('maps a branch label to its intentIds', () => {
    const node = { data: { all_client_intent: [
      { name: 'Positive', id: 'p1', intents: [{ intentId: '111' }, { intentId: '222' }] },
      { name: 'Negative', id: 'p2', intents: [{ intentId: '333' }] },
    ] } };
    expect(intentsForBranch(node, 'Positive')).toEqual(['111', '222']);
    expect(intentsForBranch(node, 'Nope')).toEqual([]);
  });
});

describe('defaultStartComponent', () => {
  it('prefers parent_uuid "0" then lowest sort_index', () => {
    const summary = { components: [
      { uuid: 'child', parent_uuid: 'p', sort_index: 0, nodes: {} },
      { uuid: 'main', parent_uuid: '0', sort_index: 2, nodes: {} },
      { uuid: 'main0', parent_uuid: '0', sort_index: 1, nodes: {} },
    ] };
    expect(defaultStartComponent(summary)).toBe('main0');
  });
  it('null when no components', () => {
    expect(defaultStartComponent({ components: [] })).toBeNull();
  });
});
