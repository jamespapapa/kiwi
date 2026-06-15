/* global React, Icon */
const { useState } = React;

function AdminScreen() {
  const [form, setForm] = useState({
    localEndpoint: 'http://localhost:8088',
    embedding: 'hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf',
    rerank: 'hf:ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/qwen3-reranker-0.6b-q8_0.gguf',
    remoteBase: '',
    remoteModel: 'Qwen3.5-397B',
    timeout: '240',
  });
  const [checking, setChecking] = useState(false);
  const [saved, setSaved] = useState(false);
  const [healthState, setHealthState] = useState('idle'); // idle | checking | ok

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function checkHealth() {
    setChecking(true);
    setHealthState('checking');
    setTimeout(() => {
      setChecking(false);
      setHealthState('ok');
    }, 800);
  }

  function save() {
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  }

  return (
    <div className="kk-admin">
      <div className="kk-admin-head">
        <div>
          <div className="kk-eyebrow">시스템</div>
          <h1 className="kk-page-title-kr">런타임 설정</h1>
          <p className="kk-page-sub">로컬 모델, 원격 LLM, 색인 파이프라인 연결 상태를 관리합니다.</p>
        </div>
        <div className="kk-admin-head-right">
          <div className="kk-status-strip-right">
            <StatusItem label="API" state="ok" />
            <StatusItem label="로컬 모델" state="muted" />
            <StatusItem label="원격 LLM" state="muted" />
            <StatusItem label="Codex CLI" state="ok" />
          </div>
        </div>
      </div>

      <div className="kk-admin-grid">
        <section className="kk-card">
          <header className="kk-card-head">
            <div>
              <div className="kk-eyebrow">런타임</div>
              <h2 className="kk-card-title-kr">모델과 엔드포인트</h2>
            </div>
            <button
              className="kk-btn kk-btn-ghost kk-btn-sm"
              onClick={() => setForm({
                localEndpoint: 'http://localhost:8088',
                embedding: 'hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf',
                rerank: 'hf:ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/qwen3-reranker-0.6b-q8_0.gguf',
                remoteBase: '',
                remoteModel: 'Qwen3.5-397B',
                timeout: '240',
              })}
            >
              기본값 복원
            </button>
          </header>

          <div className="kk-form-section">
            <div className="kk-form-section-head">
              <span className="kk-form-section-title">로컬 추론</span>
              <span className="kk-mono kk-muted">llama.cpp · GGUF</span>
            </div>

            <Field label="엔드포인트" hint="내부 런타임 URL">
              <input className="kk-input kk-mono" value={form.localEndpoint} onChange={set('localEndpoint')} />
            </Field>
            <Field label="임베딩 모델" hint="768-dim">
              <input className="kk-input kk-mono" value={form.embedding} onChange={set('embedding')} />
            </Field>
            <Field label="리랭크 모델" hint="교차 인코더">
              <input className="kk-input kk-mono" value={form.rerank} onChange={set('rerank')} />
            </Field>
          </div>

          <div className="kk-form-section">
            <div className="kk-form-section-head">
              <span className="kk-form-section-title">원격 LLM</span>
              <span className="kk-mono kk-muted">LOCAL_MODE=true · Codex CLI</span>
            </div>

            <Field label="기본 URL">
              <input className="kk-input kk-mono" value={form.remoteBase} onChange={set('remoteBase')} placeholder="https://..." />
            </Field>

            <div className="kk-form-row kk-form-row-2">
              <Field label="모델">
                <input className="kk-input kk-mono" value={form.remoteModel} onChange={set('remoteModel')} />
              </Field>
              <Field label="타임아웃" hint="초">
                <input className="kk-input kk-mono" value={form.timeout} onChange={set('timeout')} />
              </Field>
            </div>

            <Field label="API 키" hint="설정됨 · 비워두면 유지">
              <div className="kk-input-wrap">
                <input className="kk-input kk-mono" type="password" placeholder="••••••••••••••••••••••••" />
                <span className="kk-input-suffix">
                  <span className="kk-status-pill is-ok">
                    <span className="kk-status-dot" />
                    설정됨
                  </span>
                </span>
              </div>
            </Field>
          </div>

          <footer className="kk-card-foot">
            <span className="kk-muted">
              {saved
                ? <span style={{color:'var(--kk-accent-deep)', fontWeight:500}}>✓ 시크릿 저장소에 반영됨</span>
                : '변경사항은 시크릿 저장소에 즉시 반영됩니다.'}
            </span>
            <div className="kk-card-foot-actions">
              <button className="kk-btn kk-btn-ghost kk-btn-sm" onClick={checkHealth} disabled={checking}>
                {checking ? '확인 중…' : '헬스체크 실행'}
              </button>
              <button className="kk-btn kk-btn-primary kk-btn-sm" onClick={save}>설정 저장</button>
            </div>
          </footer>
        </section>

        <aside className="kk-admin-side">
          <section className="kk-card">
            <header className="kk-card-head">
              <div>
                <div className="kk-eyebrow">헬스체크</div>
                <h2 className="kk-card-title-kr">검증 결과</h2>
              </div>
              <span className="kk-mono kk-muted">
                {healthState === 'idle' ? '아직 확인 전' : healthState === 'checking' ? '확인 중…' : '방금'}
              </span>
            </header>
            <div className="kk-health">
              <HealthRow
                title="로컬 런타임"
                endpoint="http://localhost:8088"
                detail="/health 응답 확인"
                state={healthState === 'ok' ? 'ok' : 'idle'}
                latency={healthState === 'ok' ? '84 ms' : '—'}
              />
              <HealthRow
                title="원격 LLM"
                endpoint="—"
                detail="/v1/models 200 OK 확인"
                state={healthState === 'ok' ? 'ok' : 'idle'}
                latency={healthState === 'ok' ? '312 ms' : '—'}
              />
            </div>
          </section>

          <section className="kk-card">
            <header className="kk-card-head">
              <div>
                <div className="kk-eyebrow">설정</div>
                <h2 className="kk-card-title-kr">색인 차원</h2>
              </div>
            </header>
            <div className="kk-health">
              <div className="kk-health-row">
                <div className="kk-health-state" style={{color: 'var(--kk-muted)'}}>
                  <Icon name="database" size={18} />
                </div>
                <div>
                  <div className="kk-health-title">임베딩 차원</div>
                  <div className="kk-health-detail">768-dim 벡터</div>
                </div>
                <div className="kk-health-latency kk-mono" style={{color:'var(--kk-ink)', fontSize: 14}}>768</div>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="kk-field">
      <span className="kk-field-row">
        <span className="kk-field-label-kr">{label}</span>
        {hint && <span className="kk-field-hint">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

function StatusItem({ label, state }) {
  return (
    <div className={`kk-status-strip-item is-${state}`}>
      <span className="kk-status-dot" />
      <span>{label}</span>
    </div>
  );
}

function HealthRow({ title, endpoint, detail, state, latency }) {
  return (
    <div className={`kk-health-row is-${state}`}>
      <div className="kk-health-state"><span className="kk-status-dot" /></div>
      <div>
        <div className="kk-health-title">{title}</div>
        <div className="kk-health-endpoint kk-mono">{endpoint}</div>
        <div className="kk-health-detail">{detail}</div>
      </div>
      <div className="kk-health-latency kk-mono">{latency}</div>
    </div>
  );
}

window.AdminScreen = AdminScreen;
