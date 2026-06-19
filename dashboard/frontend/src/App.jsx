import { useState } from 'react';
import axios from 'axios';
import UploadZone from './components/UploadZone';
import SummaryCards from './components/SummaryCards';
import FindingList from './components/FindingList';
import ChatSidebar from './components/ChatSidebar';
import StructureTree from './components/StructureTree';
import { RefreshCw, FileText } from 'lucide-react';

function App() {
  const [data, setData] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleUpload = async (uploadedFile) => {
    setLoading(true);
    setError(null);
    setFile(uploadedFile);
    
    const formData = new FormData();
    formData.append('file', uploadedFile);
    
    try {
      const res = await axios.post('http://localhost:8000/analyze', formData);
      setData(res.data);
      
      try {
        const summaryRes = await axios.post('http://localhost:8000/summarize', formData);
        setSummaryData(summaryRes.data);
      } catch (sumErr) {
        console.error('Summary fetch failed:', sumErr);
      }
    } catch (err) {
      console.error('Upload and analysis failed:', err);
      setError('Analysis failed. Make sure the backend server is running on port 8000 and the JSON schema is valid.');
      setFile(null);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setData(null);
    setSummaryData(null);
    setFile(null);
    setError(null);
  };

  return (
    <div className="flex h-screen bg-slate-100 font-sans text-gray-900 overflow-hidden">
      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="bg-white border-b border-gray-200 px-8 py-5 shadow-sm flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-800 flex items-center gap-2">
              Talkbot Architect Dashboard
            </h1>
            <p className="text-sm text-gray-500 font-medium">
              Validate dialog graph structures, variables, and intent integrity.
            </p>
          </div>
          {file && !loading && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-semibold text-gray-600 bg-white hover:bg-gray-50 transition-all active:scale-95 shadow-sm"
            >
              <RefreshCw size={13} />
              Analyze Another File
            </button>
          )}
        </header>

        <main className="flex-1 p-8 max-w-5xl mx-auto w-full">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg shadow-sm">
              <p className="text-sm text-red-700 font-semibold">{error}</p>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center py-32 space-y-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 rounded-full border-4 border-indigo-200" />
                <div className="absolute inset-0 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-gray-700">Auditing Dialog Structure...</p>
                <p className="text-xs text-gray-400 mt-1">Running graph-integrity checks and schema validation</p>
              </div>
            </div>
          )}

          {!file && !loading && (
            <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8 max-w-2xl mx-auto mt-12 transition-all hover:shadow-2xl">
              <div className="flex items-center justify-center mb-6">
                <div className="h-12 w-12 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                  <FileText size={24} />
                </div>
              </div>
              <h2 className="text-lg font-bold text-gray-800 text-center mb-2">Upload Talkbot Export</h2>
              <p className="text-sm text-gray-500 text-center mb-6 max-w-md mx-auto">
                Select a talkbot dialogue export JSON (`speech*.json`) to analyze canvas nodes, variables, and links.
              </p>
              <UploadZone onUpload={handleUpload} />
            </div>
          )}

          {data && !loading && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-slate-100 text-slate-600">
                    <FileText size={20} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700">{file?.name}</h3>
                    <p className="text-xs text-gray-400 font-medium">Checked successfully</p>
                  </div>
                </div>
              </div>

              <SummaryCards 
                errors={data.summary?.errors || 0} 
                warnings={data.summary?.warnings || 0} 
              />
              
              <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
                <FindingList findings={data.findings} />
              </div>
              
              <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
                <StructureTree summary={summaryData} />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* AI Assistant Sidebar */}
      <ChatSidebar analysisContext={data} />
    </div>
  );
}

export default App;
