/* global React, ReactDOM, LoginScreen, ChatScreen, SourcesScreen, AdminScreen, Topbar */
const { useState, useEffect } = React;

function App() {
  const [auth, setAuth] = useState(() => {
    try { return JSON.parse(localStorage.getItem('kk.auth') || 'null'); }
    catch { return null; }
  });
  const [view, setView] = useState(() => localStorage.getItem('kk.view') || 'chat');

  useEffect(() => { localStorage.setItem('kk.view', view); }, [view]);
  useEffect(() => {
    if (auth) localStorage.setItem('kk.auth', JSON.stringify(auth));
    else localStorage.removeItem('kk.auth');
  }, [auth]);

  if (!auth) {
    return <LoginScreen onLogin={(u) => setAuth(u)} />;
  }

  return (
    <div className="kk-shell">
      <Topbar
        active={view}
        onNav={setView}
        onLogout={() => setAuth(null)}
      />
      {view === 'chat' && <ChatScreen />}
      {view === 'sources' && <SourcesScreen />}
      {view === 'admin' && <AdminScreen />}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
