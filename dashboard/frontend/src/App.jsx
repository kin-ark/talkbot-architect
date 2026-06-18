import React, { useState } from 'react';
import UploadZone from './components/UploadZone';

function App() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleUpload = async (uploadedFile) => {
    setFile(uploadedFile);
    setError(null);
    setAnalysis(null);
    
    // Analysis logic will go here in next task
    console.log("File selected:", uploadedFile.name);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12 text-center">
          <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">
            Talkbot Architect
          </h1>
          <p className="mt-4 text-lg text-gray-600">
            Analyze and optimize your voice dialogue configurations
          </p>
        </header>

        <main>
          {!file && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Upload Configuration</h2>
              <UploadZone onUpload={handleUpload} />
            </div>
          )}

          {file && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Analyzing: {file.name}</h2>
                <button 
                  onClick={() => setFile(null)}
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  Upload different file
                </button>
              </div>
              
              {loading && <p className="text-gray-600">Processing...</p>}
              {error && <p className="text-red-600">{error}</p>}
              {analysis && (
                <div className="prose">
                  {/* Analysis results component will go here */}
                  <pre>{JSON.stringify(analysis, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
