import { useState } from 'react'
import Preferences from './components/Preferences'
import DigestList from './components/DigestList'
import { LayoutDashboard } from 'lucide-react'

function App() {
  return (
    <div className="container">
      <header>
        <div className="header-content">
          <div style={{ background: '#2563eb', padding: '0.75rem', borderRadius: '0.75rem', display: 'flex' }}>
            <LayoutDashboard style={{ color: 'white', width: '2rem', height: '2rem' }} />
          </div>
          <div>
            <h1>AI Intelligence Platform</h1>
            <p className="subtitle">Local Privacy-First Intelligence Digest</p>
          </div>
        </div>
      </header>

      <section>
        <Preferences />
      </section>

      <section>
        <DigestList />
      </section>
    </div>
  )
}

export default App
