/* global React, KiwiMark, Icon */

function Topbar({ active, onNav, onLogout }) {
  const items = [
    { key: 'chat', label: '채팅' },
    { key: 'sources', label: '문서 관리' },
    { key: 'admin', label: '관리자' },
  ];
  return (
    <header className="kk-topbar">
      <button className="kk-topbar-brand" onClick={() => onNav('chat')}>
        <KiwiMark size="md" />
        <span className="kk-wordmark kk-wordmark-sm">kiwi knows</span>
      </button>

      <nav className="kk-nav">
        {items.map((it) => (
          <button
            key={it.key}
            className={`kk-nav-item ${active === it.key ? 'is-active' : ''}`}
            onClick={() => onNav(it.key)}
          >
            {it.label}
          </button>
        ))}
      </nav>

      <div className="kk-topbar-actions">
        <button className="kk-icon-btn" aria-label="새로고침" title="새로고침">
          <Icon name="refresh" />
        </button>
        <div className="kk-topbar-divider" />
        <button className="kk-user" onClick={onLogout} title="로그아웃">
          <span className="kk-avatar">A</span>
          <span className="kk-user-meta">
            <span className="kk-user-name">admin@samsung.com</span>
            <span className="kk-user-role">관리자</span>
          </span>
        </button>
      </div>
    </header>
  );
}

window.Topbar = Topbar;
