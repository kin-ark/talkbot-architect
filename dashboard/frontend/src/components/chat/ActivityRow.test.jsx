import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ActivityRow from './ActivityRow';

const done = (over = {}) => ({ name: 'validate', arguments: {}, status: 'done', summary: '0 findings', result: { findings: [] }, ...over });

describe('ActivityRow', () => {
  it('is collapsed by default and expands on click', () => {
    render(<ActivityRow entry={done({ arguments: { a: 1 }, result: { ok: true } })} />);
    expect(screen.queryByTestId('activity-detail')).toBeNull();
    fireEvent.click(screen.getByTestId('activity-row'));
    const detail = screen.getByTestId('activity-detail');
    expect(detail.textContent).toMatch(/Input/);
    expect(detail.textContent).toMatch(/"a": 1/);
    expect(detail.textContent).toMatch(/Output/);
    expect(detail.textContent).toMatch(/"ok": true/);
  });

  it('omits the Input section when arguments are empty', () => {
    render(<ActivityRow entry={done({ arguments: {}, result: 'hi' })} />);
    fireEvent.click(screen.getByTestId('activity-row'));
    const detail = screen.getByTestId('activity-detail');
    expect(detail.textContent).not.toMatch(/Input/);
    expect(detail.textContent).toMatch(/Output/);
    expect(detail.textContent).toMatch(/hi/);          // string result rendered verbatim
  });

  it('shows the narrated label', () => {
    render(<ActivityRow entry={done()} />);
    expect(screen.getByTestId('activity-row').textContent).toMatch(/Checking the dialogue/);
  });

  it('uses a spinner while running and a check when done (no crash)', () => {
    const { container, rerender } = render(<ActivityRow entry={done({ status: 'running', summary: undefined, result: undefined })} />);
    expect(container.querySelector('.animate-spin')).not.toBeNull();
    rerender(<ActivityRow entry={done()} />);
    expect(container.querySelector('.animate-spin')).toBeNull();
  });

  it('flags an errorish result and still expands', () => {
    render(<ActivityRow entry={done({ result: { ok: false, error: 'nope' } })} />);
    fireEvent.click(screen.getByTestId('activity-row'));
    expect(screen.getByTestId('activity-detail').textContent).toMatch(/nope/);
  });

  it('shows per-step elapsed when ts/endTs are present', () => {
    render(<ActivityRow entry={{ _kind: 'tool', name: 'build', status: 'done', ts: 10, endTs: 13.4 }} />);
    expect(screen.getByText(/3\.4s/)).toBeInTheDocument();
  });
});
