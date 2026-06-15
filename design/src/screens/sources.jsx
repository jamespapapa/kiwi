/* global React, Icon */
const { useState, useMemo } = React;

const INITIAL_DOCS = [
  {
    id: 'd1',
    title: '무배당 종신보험 약관 v3.2',
    topic: '일반',
    topics: ['product', 'policy'],
    url: 'samsunglife.kr/policies/term-3.2.pdf',
    updated: '2일 전',
    chunks: 8,
    content: `# 무배당 종신보험 약관

## 제1조 (목적)
이 약관은 회사가 정한 보험상품의 보장내용
및 가입자의 권리·의무를 정함을 목적으로 한다.

## 제14조 (보험금을 지급하지 않는 사유)
회사는 다음 중 어느 하나에 해당하는 경우에는
보험금을 지급하지 아니합니다.

1. 피보험자가 고의로 자신을 해친 경우.
   다만, 다음의 경우에는 보장합니다.
   - 계약의 보장개시일부터 \`2년\`이 경과한 후
     자살한 경우 (사망보험금에 한함)
   - 심신상실 등으로 자유로운 의사결정을 할
     수 없는 상태에서 발생한 경우`,
  },
  { id: 'd2', title: '보험금 지급 기준 — 종신/CI', topic: '일반', topics: ['claims'], url: 'samsunglife.kr/claims/term-ci.md', updated: '3일 전', chunks: 12,
    content: `# 보험금 지급 기준 — 종신/CI

## 일반 사망보험금
보장개시일 이후 발생한 사망에 대해 지급한다.

## 재해사망보험금
재해분류표상의 재해를 직접적인 원인으로 사망한 경우.` },
  { id: 'd3', title: '청약서 OCR 파이프라인 설계', topic: '엔지니어링', topics: ['engineering'], url: 'kk-engineering/ocr-pipeline.md', updated: '5일 전', chunks: 6,
    content: `# 청약서 OCR 파이프라인

## 단계
1. 이미지 전처리 (deskew, denoise)
2. PaddleOCR 기반 텍스트 추출
3. 필드 매핑 (rule + LLM)
4. 검증 (Qwen3 reranker)` },
  { id: 'd4', title: 'IFRS17 적용 가이드라인', topic: '재무', topics: ['finance'], url: 'kk-finance/ifrs17.md', updated: '1주 전', chunks: 14,
    content: `# IFRS17 적용 가이드라인

## CSM (Contractual Service Margin)
계약상 서비스 마진. 미래 이익을 부채로
인식한 후 보험서비스 기간에 걸쳐 인식.` },
  { id: 'd5', title: '신계약 수수료 정책 2026', topic: '영업', topics: ['sales'], url: 'kk-sales/commission-2026.md', updated: '1주 전', chunks: 9,
    content: `# 신계약 수수료 정책 2026

## 채널별 기본 수수료율
- TM: 신계약 보험료의 8.5%
- 대면: 12.0%
- 디지털 다이렉트: 4.5%` },
  { id: 'd6', title: 'kk-api 인증 흐름', topic: '엔지니어링', topics: ['engineering'], url: 'kk-api/auth-flow.md', updated: '2주 전', chunks: 4,
    content: `# kk-api 인증 흐름

JWT 기반 단기 토큰 + 리프레시. 사내망 IP
화이트리스트와 결합.` },
  { id: 'd7', title: 'hihihi', topic: '일반', topics: ['product'], url: '', updated: '방금', chunks: 1,
    content: `# 새 문서
ooooooooooooooooooooooooo
zzzzzzz` },
];

const SEARCH_TYPES = [
  { key: 'bm25',   name: '키워드',         desc: 'BM25' },
  { key: 'vector', name: '벡터',           desc: '임베딩 거리' },
  { key: 'rrf',    name: '퓨전',           desc: 'BM25 + Vector' },
  { key: 'rerank', name: '퓨전+리랭크',    desc: 'RRF + rerank' },
];

const NAV_ITEMS = [
  { key: 'docs', icon: 'doc',   label: '문서',      count: 102 },
  { key: 'git',  icon: 'git',   label: 'Git 저장소', count: 0 },
  { key: 'logs', icon: 'pulse', label: '로그',      count: 0 },
];

function SourcesScreen() {
  const [docs, setDocs] = useState(INITIAL_DOCS);
  const [activeId, setActiveId] = useState('d7');
  const [searchType, setSearchType] = useState('rerank');
  const [query, setQuery] = useState('계약');
  const [showResults, setShowResults] = useState(true);
  const [mode, setMode] = useState('split');  // 'edit' | 'split' | 'preview'

  const active = docs.find((d) => d.id === activeId) || docs[0];

  function updateActive(patch) {
    setDocs((prev) => prev.map((d) => d.id === activeId ? { ...d, ...patch } : d));
  }

  function runSearch() {
    if (query.trim()) setShowResults(true);
  }

  return (
    <div className="kk-sources">
      <aside className="kk-src-rail">
        {/* Header */}
        <div className="kk-src-rail-head">
          <span className="kk-eyebrow">문서와 출처</span>
          <button className="kk-src-rail-close" aria-label="접기">
            <Icon name="x" size={14} />
          </button>
        </div>

        {/* Nav */}
        <div className="kk-src-tabs">
          {NAV_ITEMS.map((it) => (
            <button
              key={it.key}
              className={`kk-src-tab ${it.key === 'docs' ? 'is-active' : ''}`}
            >
              <Icon name={it.icon} /> {it.label}
              <span className="kk-tab-count">{it.count}</span>
            </button>
          ))}
        </div>

        {/* Search bar */}
        <div className="kk-src-searchbar">
          <div className="kk-src-search">
            <Icon name="search" />
            <input
              placeholder="문서 내용 검색"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') runSearch(); }}
            />
          </div>
          <button className="kk-btn kk-btn-primary kk-btn-sm" onClick={runSearch}>
            <Icon name="search" size={12} /> 검색
          </button>
        </div>

        {/* Search type cards */}
        <div className="kk-src-section">
          <div className="kk-src-section-head" style={{display:'flex', alignItems:'baseline', justifyContent:'space-between'}}>
            <span className="kk-eyebrow">문서 검색 유형</span>
            <button className="kk-link" onClick={() => { setQuery(''); setShowResults(false); }}>결과 지우기</button>
          </div>
          <div className="kk-search-types">
            {SEARCH_TYPES.map((t) => (
              <button
                key={t.key}
                className={`kk-search-type ${searchType === t.key ? 'is-active' : ''}`}
                onClick={() => setSearchType(t.key)}
              >
                <span className="kk-search-type-name">{t.name}</span>
                <span className="kk-search-type-desc">{t.desc}</span>
              </button>
            ))}
          </div>
          <p className="kk-src-help">
            검색은 채팅 생성 없이 로컬 색인만 사용합니다. 토픽을 선택하면 해당 토픽 안에서만 검색합니다.
          </p>
        </div>

        {/* New document button */}
        <button className="kk-btn-dashed">
          <Icon name="plus" size={13} /> 새 문서
        </button>

        {/* Search results panel */}
        {showResults && query && (
          <div className="kk-search-results">
            <div className="kk-search-results-head">
              <div>
                <div className="kk-eyebrow">검색 결과</div>
                <div className="kk-search-results-title">{query}</div>
              </div>
              <button className="kk-link" onClick={() => setShowResults(false)}>닫기</button>
            </div>

            <div className="kk-search-results-tabs">
              <span className="kk-search-tab is-active">퓨전+리랭크</span>
              <span className="kk-search-tab">키워드 <span className="kk-search-tab-count">0</span></span>
              <span className="kk-search-tab">벡터 <span className="kk-search-tab-count">2</span></span>
              <span className="kk-search-tab">표시 <span className="kk-search-tab-count">2</span></span>
            </div>

            <div className="kk-search-result">
              <div className="kk-search-result-head">
                <span className="kk-search-result-title">hihihi</span>
                <span className="kk-search-result-score">0.565</span>
              </div>
              <div className="kk-search-result-badges">
                <span className="kk-tag">일반</span>
                <span className="kk-tag">청크 1</span>
                <span className="kk-tag">퓨전+리랭크</span>
              </div>
              <div className="kk-search-result-snippet">
                # 새 문서 ooooooooooooooooooooooo zzzzzzz
              </div>
              <div className="kk-search-result-scores">
                <span className="kk-score-pill"><span className="kk-score-pill-label">키워드</span> 0.000</span>
                <span className="kk-score-pill"><span className="kk-score-pill-label">벡터</span> 0.020</span>
                <span className="kk-score-pill"><span className="kk-score-pill-label">RRF</span> 0.033</span>
                <span className="kk-score-pill"><span className="kk-score-pill-label">리랭크</span> 0.000</span>
              </div>
              <div className="kk-search-result-foot">vector #1</div>
            </div>
          </div>
        )}
      </aside>

      {/* Editor */}
      <section className="kk-src-editor kk-src-editor-full">
        {active && (
          <>
            <div className="kk-editor-head">
              <div className="kk-editor-meta" style={{flex:1}}>
                <div className="kk-eyebrow">문서</div>
                <input
                  className="kk-input-bare"
                  value={active.title}
                  onChange={(e) => updateActive({ title: e.target.value })}
                />
                <div className="kk-editor-fields">
                  <div>
                    <div className="kk-field-label-kr">토픽</div>
                    <input className="kk-input" value={active.topic} onChange={(e) => updateActive({ topic: e.target.value })} />
                  </div>
                  <div>
                    <div className="kk-field-label-kr">출처 URI</div>
                    <input className="kk-input" value={active.url} onChange={(e) => updateActive({ url: e.target.value })} placeholder="https://..." />
                  </div>
                </div>
              </div>

              <div className="kk-editor-actions" style={{display:'flex', flexDirection:'column', alignItems:'flex-end', gap: 12}}>
                <div className="kk-mode-toggle">
                  <button className={mode === 'edit' ? 'is-active' : ''} onClick={() => setMode('edit')}>편집</button>
                  <button className={mode === 'split' ? 'is-active' : ''} onClick={() => setMode('split')}>분할</button>
                  <button className={mode === 'preview' ? 'is-active' : ''} onClick={() => setMode('preview')}>미리보기</button>
                </div>
                <div style={{display:'flex', gap: 6}}>
                  <button className="kk-btn kk-btn-ghost kk-btn-sm">
                    <Icon name="refresh" size={12} /> 현재 문서 재색인
                  </button>
                  <button className="kk-btn kk-btn-danger kk-btn-sm">삭제</button>
                  <button className="kk-btn kk-btn-primary kk-btn-sm">변경사항 저장</button>
                </div>
              </div>
            </div>

            <div className={`kk-editor-split kk-editor-mode-${mode}`}>
              {mode !== 'preview' && (
                <div className="kk-editor-pane">
                  <div className="kk-pane-head">
                    <span className="kk-eyebrow">마크다운</span>
                    <span className="kk-mono kk-muted">{active.content.split('\n').length}줄</span>
                  </div>
                  <textarea
                    className="kk-md-source"
                    value={active.content}
                    onChange={(e) => updateActive({ content: e.target.value })}
                    spellCheck={false}
                    style={{ border: 'none', resize: 'none', outline: 'none' }}
                  />
                </div>
              )}

              {mode !== 'edit' && (
                <div className="kk-editor-pane">
                  <div className="kk-pane-head">
                    <span className="kk-eyebrow">미리보기</span>
                    <span className="kk-mono kk-muted">{active.chunks}개 청크</span>
                  </div>
                  <div className="kk-md-preview">
                    <MdPreview text={active.content} />
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function MdPreview({ text }) {
  const lines = text.split('\n');
  const out = [];
  let list = [];
  let para = [];
  function flush() {
    if (para.length) { out.push({ type:'p', t: para.join(' ') }); para = []; }
    if (list.length) { out.push({ type:'ul', items: list }); list = []; }
  }
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    if (line.startsWith('# ')) { flush(); out.push({ type:'h1', t: line.slice(2) }); continue; }
    if (line.startsWith('## ')) { flush(); out.push({ type:'h2', t: line.slice(3) }); continue; }
    const ol = line.match(/^(\d+)\.\s+(.*)$/);
    if (ol) { if (para.length) flush(); list.push({ ordered:true, t: ol[2] }); continue; }
    if (line.startsWith('- ')) { if (para.length) flush(); list.push({ ordered:false, t: line.slice(2) }); continue; }
    para.push(line);
  }
  flush();
  return out.map((b, i) => {
    if (b.type === 'h1') return <h1 key={i} className="kk-serif-kr" style={{fontFamily:'var(--kk-serif-kr)', fontWeight: 700}}>{b.t}</h1>;
    if (b.type === 'h2') return <h2 key={i}>{b.t}</h2>;
    if (b.type === 'p')  return <p key={i}>{inline(b.t)}</p>;
    if (b.type === 'ul') {
      const Tag = b.items[0].ordered ? 'ol' : 'ul';
      return <Tag key={i}>{b.items.map((it, j) => <li key={j}>{inline(it.t)}</li>)}</Tag>;
    }
    return null;
  });
}
function inline(s) {
  const out = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let last = 0, m, k = 0;
  while ((m = re.exec(s)) !== null) {
    if (m.index > last) out.push(s.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('`')) out.push(<code key={k++}>{tok.slice(1,-1)}</code>);
    else                     out.push(<strong key={k++}>{tok.slice(2,-2)}</strong>);
    last = m.index + tok.length;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}

window.SourcesScreen = SourcesScreen;
