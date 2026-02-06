import { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, Save } from 'lucide-react';

const API_URL = 'http://localhost:8001/api';

export default function Preferences() {
    const [prefs, setPrefs] = useState({
        PERSONA_GENAI_NEWS_ENABLED: true,
        PERSONA_PRODUCT_IDEAS_ENABLED: true,
        PERSONA_FINANCE_ENABLED: true,
        SOURCE_HN_ENABLED: true,
        SOURCE_REDDIT_ENABLED: true,
        SOURCE_RSS_ENABLED: true,
        DELIVERY_EMAIL_ENABLED: true,
        DELIVERY_TELEGRAM_ENABLED: true
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchPrefs();
    }, []);

    const fetchPrefs = async () => {
        try {
            const res = await axios.get(`${API_URL}/preferences`);
            // Parse response (strings to bools)
            const newPrefs = { ...prefs };
            Object.keys(newPrefs).forEach(key => {
                if (res.data[key] !== undefined) {
                    newPrefs[key] = res.data[key] === 'true';
                }
            });
            setPrefs(newPrefs);
        } catch (error) {
            console.error("Failed to fetch prefs", error);
        }
    };

    const handleToggle = (key) => {
        setPrefs(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const savePrefs = async () => {
        setLoading(true);
        try {
            const payload = Object.entries(prefs).map(([key, value]) => ({
                key,
                value: String(value)
            }));
            await axios.post(`${API_URL}/preferences`, payload);
            alert('Preferences saved!');
        } catch (error) {
            alert('Failed to save');
        }
        setLoading(false);
    };

    return (
        <div className="card">
            <div className="card-title">
                <Settings size={20} />
                Intelligence Preferences
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

                {/* PERSONAS */}
                <div>
                    <h4 style={{ marginBottom: '1rem', color: '#666', borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>
                        1. Select Topics (Personas)
                    </h4>

                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>GenAI Tech News</h3>
                            <p>Technical deep dives, libraries, and model releases.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.PERSONA_GENAI_NEWS_ENABLED}
                            onChange={() => handleToggle('PERSONA_GENAI_NEWS_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>

                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>Product Ideas & Opportunities</h3>
                            <p>Startup ideas, market gaps, and problem statements.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.PERSONA_PRODUCT_IDEAS_ENABLED}
                            onChange={() => handleToggle('PERSONA_PRODUCT_IDEAS_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>

                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>Financial Analysis</h3>
                            <p>Company stages, profits/losses, and key financial milestones.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.PERSONA_FINANCE_ENABLED}
                            onChange={() => handleToggle('PERSONA_FINANCE_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>
                </div>

                {/* SOURCES */}
                <div>
                    <h4 style={{ marginBottom: '1rem', color: '#666', borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>
                        2. Select Content Sources
                    </h4>
                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>HackerNews</h3>
                            <p>Top tech discussions and Show HN.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.SOURCE_HN_ENABLED}
                            onChange={() => handleToggle('SOURCE_HN_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>
                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>Reddit (AI & Tech)</h3>
                            <p>r/LocalLLaMA, r/MachineLearning, etc.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.SOURCE_REDDIT_ENABLED}
                            onChange={() => handleToggle('SOURCE_REDDIT_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>
                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>RSS Feeds</h3>
                            <p>Official blogs from OpenAI, Anthropic, Google DeepMind.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.SOURCE_RSS_ENABLED}
                            onChange={() => handleToggle('SOURCE_RSS_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>
                </div>

                {/* DELIVERY */}
                <div>
                    <h4 style={{ marginBottom: '1rem', color: '#666', borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>
                        3. Delivery Channels
                    </h4>
                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>Email Digest</h3>
                            <p>Send daily summary to configured email.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.DELIVERY_EMAIL_ENABLED}
                            onChange={() => handleToggle('DELIVERY_EMAIL_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>
                    <div className="setting-row">
                        <div className="setting-info">
                            <h3>Telegram Bot</h3>
                            <p>Send instant message via Telegram Bot.</p>
                        </div>
                        <input
                            type="checkbox"
                            checked={prefs.DELIVERY_TELEGRAM_ENABLED}
                            onChange={() => handleToggle('DELIVERY_TELEGRAM_ENABLED')}
                            style={{ width: '1.2rem', height: '1.2rem' }}
                        />
                    </div>
                </div>

                <button
                    onClick={savePrefs}
                    disabled={loading}
                    className="btn"
                >
                    <Save size={16} />
                    {loading ? 'Saving...' : 'Save Preferences'}
                </button>
            </div>
        </div>
    );
}
