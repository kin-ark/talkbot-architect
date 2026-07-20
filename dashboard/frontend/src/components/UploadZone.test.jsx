import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import UploadZone from './UploadZone';

function drop(el, file) {
  fireEvent.drop(el, { dataTransfer: { files: [file] } });
}

describe('UploadZone drag-drop', () => {
  it('drop of a .json calls onUpload', () => {
    const onUpload = vi.fn();
    render(<UploadZone onUpload={onUpload} onReject={() => {}} />);
    drop(screen.getByTestId('upload-zone'), new File(['{}'], 'speech.json'));
    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(onUpload.mock.calls[0][0].name).toBe('speech.json');
  });
  it('drop of a .zip calls onUpload', () => {
    const onUpload = vi.fn();
    render(<UploadZone onUpload={onUpload} onReject={() => {}} />);
    drop(screen.getByTestId('upload-zone'), new File(['x'], 'export.zip'));
    expect(onUpload).toHaveBeenCalledTimes(1);
  });
  it('drop of a .txt rejects and does not upload', () => {
    const onUpload = vi.fn(); const onReject = vi.fn();
    render(<UploadZone onUpload={onUpload} onReject={onReject} />);
    drop(screen.getByTestId('upload-zone'), new File(['x'], 'notes.txt'));
    expect(onUpload).not.toHaveBeenCalled();
    expect(onReject).toHaveBeenCalledWith(expect.stringMatching(/\.json.*\.zip/i));
  });
});

describe('UploadZone progress', () => {
  it('transferring shows the pct label + bar and disables the input', () => {
    render(<UploadZone onUpload={() => {}} onReject={() => {}} progress={{ phase: 'transferring', pct: 37 }} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '37');
    expect(screen.getByText(/Uploading 37%/)).toBeInTheDocument();
  });
  it('processing shows the Processing label + indeterminate bar', () => {
    render(<UploadZone onUpload={() => {}} onReject={() => {}} progress={{ phase: 'processing' }} />);
    expect(screen.getByText(/Processing/)).toBeInTheDocument();
    expect(screen.getByTestId('progress-indeterminate')).toBeInTheDocument();
  });
});
