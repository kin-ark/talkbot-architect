import WelcomeCard from './WelcomeCard';
import UploadZone from './UploadZone';
import SampleGallery from './SampleGallery';

export default function EmptyState({ keySet, loading, onUpload, onStartBlank, onLoadSample, onOpenSettings }) {
  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <WelcomeCard />
        {!keySet && (
          <div data-testid="key-nudge" className="mb-4 rounded-lg border border-warning bg-warning-bg text-warning px-3 py-2 text-xs flex items-center gap-2">
            <span>No AI key set — the chat agent needs one.</span>
            <button type="button" onClick={onOpenSettings}
              className="ml-auto text-primary hover:underline">Open Settings</button>
          </div>
        )}
        <h2 className="text-2xl font-semibold mb-4 text-center text-text">Talkbot Architect</h2>
        <p className="text-center text-text-secondary mb-6 text-sm">Upload a WIZ dialogue JSON or ZIP to begin.</p>
        <UploadZone onUpload={onUpload} />
        <button onClick={onStartBlank}
          className="mt-4 w-full border border-border rounded-xl py-2 text-sm text-text-secondary hover:bg-surface-muted">
          Start from scratch — describe a new bot
        </button>
        {loading && <p className="text-center mt-4 text-text-tertiary">Analyzing…</p>}
        <SampleGallery onPick={onLoadSample} />
      </div>
    </div>
  );
}
