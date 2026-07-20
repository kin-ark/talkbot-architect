import UploadZone from './UploadZone';
import SampleGallery from './SampleGallery';
import { toast } from '../toast/toastStore';

export default function EmptyState({ keySet, loading, uploadProgress, onUpload, onStartBlank, onLoadSample, onOpenSettings }) {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="max-w-xl mx-auto">
          <h2 className="text-3xl font-semibold text-center text-text">Talkbot Architect</h2>
          <p className="mt-2 text-center text-text-secondary text-sm">
            Upload a WIZ export, try a sample, or describe a bot in chat — the assistant builds and validates it for you.
          </p>
          {!keySet && (
            <div data-testid="key-nudge" className="mt-4 rounded-lg border border-warning bg-warning-bg text-warning px-3 py-2 text-xs flex items-center gap-2">
              <span>No AI key set — the chat agent needs one.</span>
              <button type="button" onClick={onOpenSettings}
                className="ml-auto text-primary hover:underline">Open Settings</button>
            </div>
          )}
          <div className="mt-6">
            <UploadZone onUpload={onUpload} progress={uploadProgress}
              onReject={(m) => toast.error(m)} />
          </div>
          <button onClick={onStartBlank}
            className="mt-4 w-full border border-border rounded-xl py-2 text-sm text-text-secondary hover:bg-surface-muted">
            Start from scratch — describe a new bot
          </button>
          {loading && <p className="text-center mt-4 text-text-tertiary">Analyzing…</p>}
        </div>
        <SampleGallery onPick={onLoadSample} />
      </div>
    </div>
  );
}
