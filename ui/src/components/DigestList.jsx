import { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, Play, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const API_URL = 'http://localhost:8001/api';

export default function DigestList() {
    const [digests, setDigests] = useState([]);
    const [selectedDigest, setSelectedDigest] = useState(null);
    const [content, setContent] = useState('');
    const [running, setRunning] = useState(false);
    const [summaryMode, setSummaryMode] = useState(true);

    useEffect(() => {
        fetchDigests();
        // Auto-refresh every 10 seconds to check for new digests
        const interval = setInterval(fetchDigests, 10000);
        return () => clearInterval(interval);
    }, []);

    const fetchDigests = async () => {
        try {
            const res = await axios.get(`${API_URL}/digests`);
            // Only update if list changed to avoid unnecessary re-renders (simple length check for now)
            setDigests(prev => {
                const newFiles = res.data.digests;
                if (JSON.stringify(prev) !== JSON.stringify(newFiles)) {
                    return newFiles;
                }
                return prev;
            });
        } catch (error) {
            console.error("Failed to fetch digests");
        }
    };

    const viewDigest = async (filename) => {
        setSelectedDigest(filename);
        try {
            const res = await axios.get(`${API_URL}/digests/${filename}`);
            setContent(res.data.content);
        } catch (error) {
            setContent("**Error loading digest content**");
        }
    };

    const runPipeline = async () => {
        setRunning(true);
        try {
            await axios.post(`${API_URL}/run`, { force: true, summary_mode: summaryMode });
            alert('Pipeline started! It runs in the background. Check back in a few minutes.');
        } catch (error) {
            alert('Failed to start pipeline');
        }
        setRunning(false);
    };

    return (
        <div className="digest-layout">
            {/* Sidebar List */}
            <div className="sidebar">
                <div className="sidebar-header">
                    <h2 className="card-title" style={{ margin: 0, fontSize: '1.1rem' }}>
                        <FileText size={20} /> Digests
                    </h2>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={summaryMode}
                                onChange={(e) => setSummaryMode(e.target.checked)}
                            />
                            Summary
                        </label>
                        <button
                            onClick={runPipeline}
                            disabled={running}
                            className="btn btn-primary"
                            title="Run Pipeline Now"
                            style={{ borderRadius: '50%', padding: '0.6rem' }}
                        >
                            {running ? <Loader2 className="animate-spin" size={20} /> : <Play size={20} />}
                        </button>
                    </div>
                </div>

                <div>
                    {digests.map((file) => (
                        <div
                            key={file}
                            onClick={() => viewDigest(file)}
                            className={`digest-item ${selectedDigest === file ? 'active' : ''}`}
                        >
                            <p style={{ margin: 0, fontWeight: 500 }}>{file}</p>
                            <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b' }}>Markdown</p>
                        </div>
                    ))}
                    {digests.length === 0 && <p style={{ color: '#94a3b8', textAlign: 'center' }}>No digests found.</p>}
                </div>
            </div>

            {/* Main Content Area */}
            <div className="content-area">
                {selectedDigest ? (
                    <div>
                        <div className="markdown-content">
                            <ReactMarkdown>{content}</ReactMarkdown>
                        </div>
                    </div>
                ) : (
                    <div className="empty-state">
                        <FileText size={64} style={{ opacity: 0.2, marginBottom: '1rem' }} />
                        <p>Select a digest to view its content</p>
                    </div>
                )}
            </div>
        </div>
    );
}
