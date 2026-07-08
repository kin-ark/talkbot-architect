import { Tag } from 'lucide-react';
import { tagColor } from './ui/tagColor';

export default function TagsPanel({ tags }) {
  const rows = tags || [];
  if (!rows.length) return <div data-testid="tags-panel" className="p-4 text-xs text-text-tertiary">No tags.</div>;
  return (
    <div data-testid="tags-panel" className="p-4 overflow-y-auto h-full space-y-3">
      {rows.map((c) => (
        <div key={c.category_id || c.category} data-testid="tag-category-row" className="border-b border-divider pb-2">
          <div className="flex items-center gap-1.5 text-sm text-text">
            <Tag size={13} className="text-text-tertiary" />
            <span className="font-medium">{c.category}</span>
            <span className="ml-auto text-xs text-text-tertiary">{c.node_count} node{c.node_count === 1 ? '' : 's'}</span>
          </div>
          <div className="mt-1 flex flex-wrap gap-1">
            {(c.values || []).map((v, i) => (
              <span key={i} className={`rounded px-1.5 py-0.5 text-xs ${tagColor(c.category)}`}>{v}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
