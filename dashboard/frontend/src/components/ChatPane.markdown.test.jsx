import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ChatPane from './ChatPane';

describe('ChatPane markdown', () => {
  it('renders agent markdown list as <li> elements', () => {
    const transcript = [{ role: 'agent', text: '- alpha\n- beta' }];
    const { container } = render(<ChatPane transcript={transcript} proposal={null} sending={false}
      onSend={() => {}} onApply={() => {}} onReject={() => {}} onCancel={() => {}} />);
    expect(container.querySelectorAll('li').length).toBe(2);
    expect(screen.getByText('alpha')).toBeInTheDocument();
  });

  it('keeps user text plain (no markdown parsing artifacts)', () => {
    const transcript = [{ role: 'user', text: '**not bold**' }];
    const { container } = render(<ChatPane transcript={transcript} proposal={null} sending={false}
      onSend={() => {}} onApply={() => {}} onReject={() => {}} onCancel={() => {}} />);
    expect(container.querySelectorAll('strong').length).toBe(0);
    expect(screen.getByText('**not bold**')).toBeInTheDocument();
  });
});
