import React, { useEffect, useState } from 'react';
import GlobalSidebar from './components/GlobalSidebar';
import DialogueGraphCanvas from './components/DialogueGraphCanvas';
import NodePropertiesPanel from './components/NodePropertiesPanel';
import axios from 'axios';

const mockFallbackData = {
  mainFlow: [
    {
      name: "Fallback Component",
      children: [
        {
          name: "Start Node",
          uuid: "start-1",
          node_type: "Talk",
          allowedKBs: [],
          children: [
            {
              name: "Welcome Node",
              uuid: "welcome-1",
              node_type: "Talk",
              allowedKBs: ["KB-1"],
              children: []
            }
          ]
        }
      ]
    }
  ],
  knowledgeBases: [
    { id: "KB-1", title: "Test Knowledge Base" }
  ]
};

export default function App() {
  const [data, setData] = useState({ mainFlow: [], knowledgeBases: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    axios.get(`${apiUrl}/summarize`)
      .then(res => {
        setData(res.data.summary || res.data || { mainFlow: [] });
        setLoading(false);
      })
      .catch(err => {
        console.warn('Backend not available, using fallback data', err.message);
        setData(mockFallbackData);
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans" data-testid="app-container">
      <GlobalSidebar />
      <main className="flex-1 flex overflow-hidden relative">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">Loading...</div>
        ) : (
          <>
            <div className="flex-1 flex overflow-hidden relative">
              <DialogueGraphCanvas 
                mainFlow={data.mainFlow} 
                onNodeClick={setSelectedNode} 
              />
            </div>
            <NodePropertiesPanel 
              selectedNode={selectedNode} 
              knowledgeBases={data.knowledgeBases} 
            />
          </>
        )}
      </main>
    </div>
  );
}
