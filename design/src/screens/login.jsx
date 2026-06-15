/* global React, KiwiMark, Icon */
const { useState } = React;

function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('admin@samsung.com');
  const [pw, setPw] = useState('demo-password');
  const [busy, setBusy] = useState(false);

  function submit(e) {
    e.preventDefault();
    setBusy(true);
    setTimeout(() => onLogin({ email }), 380);
  }

  return (
    <div className="kk-login">
      <div className="kk-login-bg" aria-hidden="true">
        <div className="kk-login-bg-mark">
          <KiwiMark size="3xl" />
        </div>
      </div>

      <form className="kk-login-card" onSubmit={submit}>
        <div className="kk-login-brand">
          <KiwiMark size="lg" />
          <div className="kk-login-brand-text">
            <div className="kk-wordmark">kiwi knows</div>
            <div className="kk-login-tag">사내 지식 동반자</div>
          </div>
        </div>

        <div className="kk-login-form">
          <label className="kk-field">
            <span className="kk-field-label">이메일</span>
            <input
              className="kk-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label className="kk-field">
            <span className="kk-field-row">
              <span className="kk-field-label">비밀번호</span>
              <span className="kk-field-hint">demo · 아무 값 가능</span>
            </span>
            <input
              className="kk-input"
              type="password"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" className="kk-btn kk-btn-primary kk-btn-full" disabled={busy}>
            {busy ? '로그인 중…' : '로그인'}
            {!busy && <Icon name="arrow-right" />}
          </button>
        </div>

        <div className="kk-login-meta">
          <span>v2.4 · 삼성생명 사내</span>
          <span className="kk-dot">·</span>
          <span>인가된 사용자만 접근 가능</span>
        </div>
      </form>
    </div>
  );
}

window.LoginScreen = LoginScreen;
