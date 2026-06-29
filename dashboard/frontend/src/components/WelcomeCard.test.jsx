import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import WelcomeCard from './WelcomeCard';

beforeEach(() => localStorage.clear());

describe('WelcomeCard', () => {
  it('renders then hides on dismiss + persists', () => {
    const { rerender } = render(<WelcomeCard />);
    expect(screen.getByTestId('welcome-card')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('welcome-dismiss'));
    expect(screen.queryByTestId('welcome-card')).toBeNull();
    expect(localStorage.getItem('tb-welcome-dismissed')).toBe('1');
    rerender(<WelcomeCard />);   // stays hidden
    expect(screen.queryByTestId('welcome-card')).toBeNull();
  });

  it('is hidden when already dismissed', () => {
    localStorage.setItem('tb-welcome-dismissed', '1');
    render(<WelcomeCard />);
    expect(screen.queryByTestId('welcome-card')).toBeNull();
  });
});
