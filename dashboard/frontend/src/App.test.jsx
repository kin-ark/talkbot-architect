import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
vi.mock('./api');
import App from './App';

describe('App', () => {
  it('shows the upload zone before any session', () => {
    render(<App />);
    expect(screen.getByTestId('upload-zone')).toBeInTheDocument();
  });
});
