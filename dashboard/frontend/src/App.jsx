import React from 'react';
import GlobalSidebar from './components/GlobalSidebar';

export default function App() {
  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans" data-testid="app-container">
      <GlobalSidebar />
      <main className="flex-1 flex overflow-hidden">
        {/* Canvas and Panel will go here */}
      </main>
    </div>
  );
}
