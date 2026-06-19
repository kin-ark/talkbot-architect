import { render, screen } from '@testing-library/react';
import App from './App';

describe('App Layout', () => {
  it('renders without crashing and displays the global sidebar', () => {
    render(<App />);
    expect(screen.getByTestId('app-container')).toBeInTheDocument();
    expect(screen.getByTestId('global-sidebar')).toBeInTheDocument();
  });
});
