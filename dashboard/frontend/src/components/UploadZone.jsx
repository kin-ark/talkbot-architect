import { useRef } from 'react';
import { Upload } from 'lucide-react';

export default function UploadZone({ onUpload }) {
  const fileInputRef = useRef(null);

  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) onUpload(file);
  };

  return (
    <div
      data-testid="upload-zone"
      className="border-2 border-dashed border-border rounded-lg p-12 text-center hover:border-primary transition-colors cursor-pointer relative"
      onClick={() => fileInputRef.current.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleChange}
        accept=".json,.zip"
      />
      <Upload className="mx-auto h-12 w-12 text-text-tertiary" />
      <p className="mt-2 text-sm text-text-secondary">Drag speech*.json or export .zip here, or click to select</p>
    </div>
  );
}
