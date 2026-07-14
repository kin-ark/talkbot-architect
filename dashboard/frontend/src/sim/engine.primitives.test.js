import { describe, it, expect } from 'vitest';
import {
  MAX_STEPS, buildIndex, hasTarget, evalCondition, evalConditionGroup,
  pickConditionalBranch, applyAssign, mapChoices,
} from './engine';

describe('buildIndex', () => {
  it('indexes components and kb multi_round components + kbs', () => {
    const summary = {
      components: [{ uuid: 'c1', nodes: {} }],
      knowledge_bases: [{ knowledge_id: 7, title: 'KB', answers: [],
        multi_round: { components: [{ uuid: 'mr1', nodes: {} }] } }],
    };
    const { byUuid, kbById } = buildIndex(summary);
    expect(byUuid.get('c1')).toBeTruthy();
    expect(byUuid.get('mr1')).toBeTruthy();
    expect(kbById.get(7).title).toBe('KB');
  });
});

describe('hasTarget', () => {
  it('true for any set target field, false when all null', () => {
    expect(hasTarget({ target_uuid: 'x' })).toBe(true);
    expect(hasTarget({ terminal: 'hangup' })).toBe(true);
    expect(hasTarget({ target_uuid: null, target_component: null, target_kb: null, terminal: null })).toBe(false);
  });
});

describe('evalCondition', () => {
  const vs = { PAYMENT_STATUS: 'paid', AMOUNT: '150' };
  it('= and != on strings', () => {
    expect(evalCondition({ left_value: 'PAYMENT_STATUS', operator: '=', right_value: 'paid' }, vs)).toBe(true);
    expect(evalCondition({ left_value: 'PAYMENT_STATUS', operator: '!=', right_value: 'paid' }, vs)).toBe(false);
  });
  it('In / Not in comma lists', () => {
    expect(evalCondition({ left_value: 'PAYMENT_STATUS', operator: 'In', right_value: 'due, paid, overdue' }, vs)).toBe(true);
    expect(evalCondition({ left_value: 'PAYMENT_STATUS', operator: 'Not in', right_value: 'due,overdue' }, vs)).toBe(true);
  });
  it('numeric comparisons', () => {
    expect(evalCondition({ left_value: 'AMOUNT', operator: '>', right_value: '100' }, vs)).toBe(true);
    expect(evalCondition({ left_value: 'AMOUNT', operator: '<=', right_value: '100' }, vs)).toBe(false);
  });
  it('Null / Not null and unset vars', () => {
    expect(evalCondition({ left_value: 'MISSING', operator: 'Null', right_value: '' }, vs)).toBe(true);
    expect(evalCondition({ left_value: 'AMOUNT', operator: 'Not null', right_value: '' }, vs)).toBe(true);
    // any comparison on an unset var is false
    expect(evalCondition({ left_value: 'MISSING', operator: '=', right_value: 'x' }, vs)).toBe(false);
  });
  it('normalizes friendly operator tokens', () => {
    expect(evalCondition({ left_value: 'MISSING', operator: 'IsNull', right_value: '' }, vs)).toBe(true);
    expect(evalCondition({ left_value: 'PAYMENT_STATUS', operator: 'Contains', right_value: 'aid' }, vs)).toBe(true);
  });
});

describe('evalConditionGroup', () => {
  it('ANDs judgements; empty group is false', () => {
    const vs = { A: '1', B: '2' };
    expect(evalConditionGroup([{ left_value: 'A', operator: '=', right_value: '1' }, { left_value: 'B', operator: '=', right_value: '2' }], vs)).toBe(true);
    expect(evalConditionGroup([{ left_value: 'A', operator: '=', right_value: '1' }, { left_value: 'B', operator: '=', right_value: '9' }], vs)).toBe(false);
    expect(evalConditionGroup([], vs)).toBe(false);
  });
});

describe('pickConditionalBranch', () => {
  const node = {
    branches: [
      { label: 'Paid', kind: 'condition', target_uuid: 'nPaid' },
      { label: 'Unpaid', kind: 'condition', target_uuid: 'nUnpaid' },
      { label: 'Default', kind: 'default', target_uuid: 'nDef' },
    ],
    data: { branch: [
      { name: 'Paid', branch_judgement_condition: [{ left_value: 'S', operator: '=', right_value: 'paid' }] },
      { name: 'Unpaid', branch_judgement_condition: [{ left_value: 'S', operator: '=', right_value: 'unpaid' }] },
    ] },
  };
  it('routes to the matching branch', () => {
    expect(pickConditionalBranch(node, { S: 'paid' }).edge.target_uuid).toBe('nPaid');
  });
  it('falls back to Default when nothing matches', () => {
    expect(pickConditionalBranch(node, { S: 'other' }).edge.target_uuid).toBe('nDef');
  });
});

describe('applyAssign', () => {
  it('sets literal values and notes them', () => {
    const node = { data: { value_assignment: [
      { variable: { name: 'SALUTATION' }, assign: { func_code: 'OPT_VALUE_ASSIGNMENT', params: [{ name: 'value_to_assign', value: 'Bapak' }] } },
      { variable: { name: 'TODAY' }, assign: { func_code: 'DATE_GET_TODAY', params: [] } },
    ] } };
    const { varState, notes } = applyAssign(node, { X: '1' });
    expect(varState.SALUTATION).toBe('Bapak');
    expect(varState.TODAY).toBe('(computed)');
    expect(varState.X).toBe('1');
    expect(notes).toContain('set SALUTATION = Bapak');
  });
});

describe('mapChoices', () => {
  it('marks dead-end branches disabled', () => {
    const node = { branches: [
      { label: 'Positive', kind: 'intent', target_uuid: 'a' },
      { label: 'Dead', kind: 'intent', target_uuid: null, target_component: null, target_kb: null, terminal: null },
    ] };
    const cs = mapChoices(node);
    expect(cs[0]).toMatchObject({ label: 'Positive', branchIndex: 0, disabled: false });
    expect(cs[1]).toMatchObject({ label: 'Dead', disabled: true, reason: 'dead end' });
  });
});

it('MAX_STEPS is a sane cap', () => { expect(MAX_STEPS).toBe(200); });
