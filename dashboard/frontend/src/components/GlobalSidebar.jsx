import React from 'react';
import { Map, Book, Settings } from 'lucide-react';

export default function GlobalSidebar() {
  return (
    <nav className="w-16 h-full bg-white border-r border-gray-200 flex flex-col items-center py-4 shadow-sm z-10" data-testid="global-sidebar">
      <div className="mb-8">
        <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-xl">
          W
        </div>
      </div>
      
      <div className="flex flex-col gap-6 flex-1">
        <button className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Map">
          <Map size={24} />
        </button>
        <button className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Library">
          <Book size={24} />
        </button>
      </div>

      <div className="mt-auto">
        <button className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors" title="Settings">
          <Settings size={24} />
        </button>
      </div>
    </nav>
  );
}
