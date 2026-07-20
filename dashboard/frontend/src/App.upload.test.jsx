import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import * as api from './api';
import { useSession } from './state/useSession';
import App from './App';

beforeEach(() => {
  // SampleGallery mounts inside EmptyState and calls listSamples().then(...)
  api.listSamples.mockResolvedValue([]);
});

const baseHook = {
  summary: null, findings: [], transcript: [], proposal: null, canUndo: false, canRedo: false,
  sending: false, sessions: [], activeSessionId: null, usage: null,
  upload: vi.fn(), startBlank: vi.fn(), loadSample: vi.fn(), send: vi.fn(), apply: vi.fn(), reject: vi.fn(),
  undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
  newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(), startNew: vi.fn(),
};

describe('App upload-progress gating', () => {
  it('keeps the upload zone (progress bar) mounted while uploading, not the skeleton', () => {
    useSession.mockReturnValue({ ...baseHook, loading: true, uploadProgress: { phase: 'transferring', pct: 20 } });
    render(<App />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.queryByTestId('flow-skeleton')).not.toBeInTheDocument();
  });
  it('shows the skeleton for a non-upload load (no uploadProgress)', () => {
    useSession.mockReturnValue({ ...baseHook, loading: true, uploadProgress: null });
    render(<App />);
    expect(screen.getByTestId('flow-skeleton')).toBeInTheDocument();
  });
});
