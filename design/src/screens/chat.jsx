/* global React, KiwiMark, Icon */
const { useState, useRef, useEffect } = React;

const INITIAL_SESSIONS = [
  { id: 's1', title: '약관 해석 — 무배당 종신보험', time: '1분 전', messages: [
    { role: 'user', text: '무배당 종신보험에서 자살면책기간이 적용되지 않는 예외 케이스 정리해줘. 약관 근거 포함해서.' },
    { role: 'assistant', text: `**무배당 종신보험 약관 제14조(보험금을 지급하지 않는 사유)** 기준, 자살의 경우 책임개시일부터 *2년* 이내에는 원칙적으로 면책이지만, 다음 3가지 경우 면책기간이 적용되지 않습니다.

1. 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 경우 — 의학적 소견서 첨부 시 인정[1]
2. 계약의 보장개시일부터 2년이 경과한 이후 발생한 경우 — 재해사망보험금은 미지급, 사망보험금은 지급[1]
3. 피보험자가 본인의 의사와 관계없이 타인의 강요·기망에 의한 경우[2]

IFRS17 회계처리 관점에서는 면책 적용 여부와 무관하게 발생사고 시점에 CSM이 조정되며, 해당 회계 기준은 \`finance/ifrs17-guideline.md\`에 정리되어 있습니다.[3]`,
      sources: [
        { title: '무배당 종신보험 약관 v3.2', topic: 'product · policy', conf: 0.94 },
        { title: '보험금 지급 기준 — 종신', topic: 'claims', conf: 0.87 },
        { title: 'IFRS17 적용 가이드라인', topic: 'finance', conf: 0.71 },
      ],
    },
  ]},
  { id: 's2', title: '신계약 채널별 수수료 산정 절차', time: '3분 전', messages: [] },
  { id: 's3', title: 'kk-api에서 reranker 호출 흐름 설명', time: '12분 전', messages: [] },
  { id: 's4', title: 'OCR 파이프라인 재처리 기준은?', time: '24분 전', messages: [] },
  { id: 's5', title: 'IFRS17 CSM 계산 로직', time: '27분 전', messages: [] },
  { id: 's6', title: 'Qwen3 reranker 벤치마크', time: '29분 전', messages: [] },
];

const STARTERS = [
  { topic: '약관',     q: '무배당 종신보험에서 면책기간 적용 예외는?' },
  { topic: '코드',     q: 'kk-api에서 reranker 호출 흐름 설명해줘' },
  { topic: '로그',     q: '어제 발생한 OCR 파이프라인 5xx 원인 정리' },
  { topic: '프로세스', q: '신계약 채널별 수수료 산정 절차' },
];

const FAKE_SOURCES = [
  ['무배당 종신보험 약관 v3.2', 'product · policy'],
  ['보험금 지급 기준 — 종신/CI', 'claims'],
  ['IFRS17 적용 가이드라인', 'finance'],
  ['kk-api 아키텍처 노트', 'engineering'],
  ['신계약 수수료 정책 2026', 'sales'],
  ['청약서 OCR 파이프라인', 'engineering'],
];

function randomSources() {
  const shuffled = [...FAKE_SOURCES].sort(() => Math.random() - 0.5);
  const n = 2 + Math.floor(Math.random() * 2);
  return shuffled.slice(0, n).map(([title, topic]) => ({
    title, topic,
    conf: Math.round((0.62 + Math.random() * 0.34) * 100) / 100,
  }));
}

function ChatScreen() {
  const [sessions, setSessions] = useState(INITIAL_SESSIONS);
  const [activeId, setActiveId] = useState('s1');
  const [composer, setComposer] = useState('');
  const [streaming, setStreaming] = useState(false);
  const threadRef = useRef(null);

  const active = sessions.find((s) => s.id === activeId) || sessions[0];
  const isEmpty = !active || active.messages.length === 0;

  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [active?.messages.length, streaming]);

  function updateActive(updater) {
    setSessions((prev) => prev.map((s) => s.id === activeId ? updater(s) : s));
  }

  function newChat() {
    const id = 'n' + Date.now();
    setSessions((prev) => [{ id, title: '새 대화', time: '방금', messages: [] }, ...prev]);
    setActiveId(id);
    setComposer('');
  }

  function deleteSession(id, e) {
    e.stopPropagation();
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      if (id === activeId && next.length) setActiveId(next[0].id);
      return next;
    });
  }

  async function send(textOverride) {
    const text = (textOverride ?? composer).trim();
    if (!text || streaming) return;

    updateActive((s) => ({
      ...s,
      title: s.messages.length === 0 ? text.slice(0, 40) : s.title,
      time: '방금',
      messages: [...s.messages, { role: 'user', text }],
    }));
    setComposer('');
    setStreaming(true);

    const placeholder = { role: 'assistant', text: '', sources: [], thinking: true };
    updateActive((s) => ({ ...s, messages: [...s.messages, placeholder] }));

    try {
      const sys = `You are kiwi knows, an internal RAG assistant for Samsung Life engineering & policy. Answer succinctly in 3-5 sentences in KOREAN. Use markdown: bold for key terms, *italic* for emphasized phrases, \`code\` for filenames. Cite sources with bracket numbers like [1], [2]. Stay within the domain: insurance products, IFRS17, codebase, RAG pipeline, OCR, claims.`;

      const answer = await window.claude.complete({
        messages: [{ role: 'user', content: `[System context: ${sys}]\n\n질문: ${text}` }],
      });

      updateActive((s) => {
        const msgs = [...s.messages];
        msgs[msgs.length - 1] = {
          role: 'assistant',
          text: answer || '모델에 도달할 수 없습니다.',
          sources: randomSources(),
        };
        return { ...s, messages: msgs };
      });
    } catch (err) {
      updateActive((s) => {
        const msgs = [...s.messages];
        msgs[msgs.length - 1] = { role: 'assistant', text: '⚠ 모델 호출 실패. 다시 시도해주세요.', sources: [] };
        return { ...s, messages: msgs };
      });
    } finally {
      setStreaming(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="kk-chat">
      <aside className="kk-chat-side">
        <div className="kk-side-head">
          <div className="kk-side-title">
            <span className="kk-eyebrow">대화 목록</span>
            <span className="kk-count">{sessions.length}</span>
          </div>
          <button className="kk-btn kk-btn-ghost kk-btn-sm" onClick={newChat}>
            <Icon name="plus" size={12} /> 새 대화
          </button>
        </div>

        <div className="kk-side-search">
          <Icon name="search" />
          <input placeholder="대화 검색" />
        </div>

        <div className="kk-side-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`kk-session ${s.id === activeId ? 'is-active' : ''}`}
              onClick={() => setActiveId(s.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter') setActiveId(s.id); }}
            >
              <div className="kk-session-title">{s.title}</div>
              <div className="kk-session-meta">
                <span>{s.time}</span>
                <span className="kk-dot">·</span>
                <span>{s.messages.length}개 메시지</span>
              </div>
              <button
                className="kk-session-delete"
                aria-label="대화 삭제"
                onClick={(e) => deleteSession(s.id, e)}
              >
                <Icon name="x" size={13} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="kk-chat-main">
        {isEmpty
          ? <ChatEmpty onAsk={(q) => send(q)} />
          : <ChatThread session={active} threadRef={threadRef} streaming={streaming} />}

        <div className="kk-composer-wrap">
          <div className="kk-composer">
            <textarea
              rows={1}
              placeholder="약관, 코드, 로그에 대해 질문하세요…"
              value={composer}
              onChange={(e) => setComposer(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <div className="kk-composer-bar">
              <div className="kk-composer-chips">
                <span className="kk-chip">
                  <Icon name="database" size={11} />
                  전체 출처
                </span>
                <span className="kk-chip">
                  <Icon name="clock" size={11} />
                  표준 추론
                </span>
              </div>
              <button
                className="kk-btn kk-btn-primary kk-btn-sm"
                onClick={() => send()}
                disabled={streaming || !composer.trim()}
              >
                {streaming ? '전송 중…' : '전송'}
                {!streaming && <Icon name="send" size={12} />}
              </button>
            </div>
          </div>
          <div className="kk-composer-hint">
            <kbd>Enter</kbd> 전송 · <kbd>Shift</kbd><kbd>Enter</kbd> 줄바꿈
          </div>
        </div>
      </section>
    </div>
  );
}

function ChatEmpty({ onAsk }) {
  return (
    <div className="kk-empty">
      <div className="kk-empty-inner">
        <div className="kk-empty-mark"><KiwiMark size="xl" /></div>
        <h1 className="kk-empty-title-kr">
          무엇을 도와드릴까요?
        </h1>
        <p className="kk-empty-sub">
          약관, 저장소, 운영 로그에서 근거가 있는 답변을 찾아드립니다.
        </p>

        <div className="kk-starters">
          {STARTERS.map((s, i) => (
            <button key={i} className="kk-starter" onClick={() => onAsk(s.q)}>
              <span className="kk-starter-topic">{s.topic}</span>
              <span className="kk-starter-q">{s.q}</span>
              <span className="kk-starter-arrow"><Icon name="arrow-up-right" /></span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChatThread({ session, threadRef, streaming }) {
  return (
    <div className="kk-thread" ref={threadRef}>
      <div className="kk-thread-inner">
        {session.messages.map((m, i) => (
          m.role === 'user'
            ? <UserMessage key={i} text={m.text} />
            : <AssistantMessage key={i} text={m.text} sources={m.sources} thinking={m.thinking} streaming={streaming && i === session.messages.length - 1} />
        ))}
      </div>
    </div>
  );
}

function UserMessage({ text }) {
  return (
    <article className="kk-msg kk-msg-user">
      <div className="kk-msg-body">{text}</div>
    </article>
  );
}

function AssistantMessage({ text, sources = [], thinking, streaming }) {
  return (
    <article className="kk-msg kk-msg-assistant">
      <div className="kk-msg-avatar"><KiwiMark size="sm" /></div>
      <div className="kk-msg-body">
        {thinking && streaming
          ? <div className="kk-thinking-inline"><div className="kk-thinking"><span/><span/><span/></div>답변을 생성합니다.</div>
          : <Markdown text={text} />}

        {sources && sources.length > 0 && (
          <div className="kk-cited">
            <div className="kk-cited-head">
              <span className="kk-eyebrow">참고 출처</span>
              <span className="kk-count">{sources.length}</span>
            </div>
            <div className="kk-cited-list">
              {sources.map((s, i) => (
                <button key={i} className="kk-source">
                  <span className="kk-source-num">{i + 1}</span>
                  <span className="kk-source-body">
                    <span className="kk-source-title">{s.title}</span>
                    <span className="kk-source-meta">{s.topic}</span>
                  </span>
                  <span className="kk-source-conf">
                    <span className="kk-conf-bar"><span style={{ width: `${s.conf * 100}%` }} /></span>
                    <span className="kk-conf-num">{s.conf.toFixed(2)}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {!thinking && (
          <div className="kk-msg-actions">
            <button className="kk-icon-btn" aria-label="복사"><Icon name="copy" size={13} /></button>
            <button className="kk-icon-btn" aria-label="좋아요"><Icon name="thumb-up" size={13} /></button>
            <button className="kk-icon-btn" aria-label="별로"><Icon name="thumb-down" size={13} /></button>
            <button className="kk-icon-btn" aria-label="재생성"><Icon name="refresh" size={13} /></button>
          </div>
        )}
      </div>
    </article>
  );
}

function Markdown({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  const blocks = [];
  let list = [];
  let para = [];
  function flushPara() { if (para.length) { blocks.push({ type:'p', t: para.join(' ') }); para = []; } }
  function flushList() { if (list.length) { blocks.push({ type:'ol', items: list }); list = []; } }
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushPara(); flushList(); continue; }
    const m = line.match(/^(\d+)\.\s+(.*)$/);
    if (m) { flushPara(); list.push(m[2]); continue; }
    flushList();
    para.push(line);
  }
  flushPara(); flushList();
  return blocks.map((b, i) => {
    if (b.type === 'p') return <p key={i}>{inline(b.t)}</p>;
    if (b.type === 'ol') return <ol key={i}>{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ol>;
    return null;
  });
}

function inline(s) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[\d+\])/g;
  let last = 0, m, k = 0;
  while ((m = re.exec(s)) !== null) {
    if (m.index > last) out.push(s.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**'))     out.push(<strong key={k++}>{tok.slice(2,-2)}</strong>);
    else if (tok.startsWith('*')) out.push(<em key={k++}>{tok.slice(1,-1)}</em>);
    else if (tok.startsWith('`')) out.push(<code key={k++}>{tok.slice(1,-1)}</code>);
    else if (tok.startsWith('[')) out.push(<sup key={k++} className="kk-cite">{tok.slice(1,-1)}</sup>);
    last = m.index + tok.length;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}

window.ChatScreen = ChatScreen;
