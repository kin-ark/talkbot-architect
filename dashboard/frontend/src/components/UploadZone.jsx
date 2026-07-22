import { useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import ProgressBar from './ui/ProgressBar';

const ACCEPT = ['.json', '.zip'];
const isAccepted = (name) => ACCEPT.some((ext) => name.toLowerCase().endsWith(ext));

export default function UploadZone({ onUpload, progress = null, onReject = () => {} }) {
  const fileInputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const busy = Boolean(progress);

  const take = (file) => {
    if (!file) return;
    if (isAccepted(file.name)) onUpload(file);
    else onReject('Only .json or .zip files are supported.');
  };

  const handleChange = (e) => take(e.target.files[0]);
  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (busy) return;
    take(e.dataTransfer.files[0]);
  };
  const onDragOver = (e) => { e.preventDefault(); if (!busy) setDragging(true); };
  const onDragLeave = (e) => { e.preventDefault(); setDragging(false); };

  const label = progress?.phase === 'transferring'
    ? `Uploading ${progress.pct ?? 0}%`
    : progress?.phase === 'processing' ? 'Processing…' : null;

  return (
    <div
      data-testid="upload-zone"
      role="button"
      aria-label="Upload a WIZ export"
      tabIndex={busy ? -1 : 0}
      onClick={() => !busy && fileInputRef.current.click()}
      onKeyDown={(e) => { if (!busy && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); fileInputRef.current.click(); } }}
      onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
      className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors relative
        ${busy ? 'cursor-default border-border' : 'cursor-pointer hover:border-primary'}
        ${dragging ? 'border-primary bg-surface-muted' : 'border-border'}`}
    >
      <input ref={fileInputRef} type="file" className="hidden" onChange={handleChange}
        accept=".json,.zip" disabled={busy} />
      {busy ? (
        <div className="space-y-3">
          <ProgressBar value={progress.phase === 'transferring' ? (progress.pct ?? null) : null} />
          <p className="text-sm text-text-secondary">{label}</p>
        </div>
      ) : (
        <>
          <Upload className="mx-auto h-12 w-12 text-text-tertiary" />
          <p className="mt-2 text-sm text-text-secondary">Drag speech*.json or export .zip here, or click to select</p>
        </>
      )}
    </div>
  );
}
