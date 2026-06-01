"use client";

import {
  Bot,
  BrainCircuit,
  ClipboardCheck,
  Copy,
  Flame,
  FolderOpen,
  Info,
  ListChecks,
  Loader2,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Play,
  RefreshCw,
  Send,
  Square,
  X
} from "lucide-react";
import { FormEvent, KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FitAddon as FitAddonType } from "@xterm/addon-fit";
import type { Terminal as XTermType } from "@xterm/xterm";

const API_BASE = process.env.NEXT_PUBLIC_KIWI_API_URL ?? "http://localhost:8787";
const TERMINAL_MIN_COLS = 80;
const TERMINAL_MAX_COLS = 500;
const TERMINAL_MIN_ROWS = 20;
const TERMINAL_MAX_ROWS = 160;

type KiwiSettings = {
  api_base_url: string;
  coder_api_base_url: string;
  orchestrator_model: string;
  coder_model: string;
  qwencode_command: string;
  dangerous_mode: boolean;
  request_timeout_seconds: number;
  max_context_chars: number;
  kk_docs_mcp_enabled: boolean;
  kk_docs_mcp_url: string;
  kk_code_analysis_mcp_enabled: boolean;
  kk_code_analysis_mcp_url: string;
  kk_mcp_token_set: boolean;
  api_key_set: boolean;
};

type Project = {
  id: string;
  name: string;
  root_path: string;
  summary: {
    stack?: string[];
    commands?: Array<{ name: string; command: string }>;
    risks?: string[];
    qwen_harness?: {
      status?: string;
      command?: string | string[];
      project_command?: string | null;
      reason?: string;
      error?: string;
    };
    runtime_checks?: {
      checked_at?: string;
      items?: RuntimeCheckItem[];
      qwen?: {
        harness_status?: string | null;
        harness_reason?: string | null;
        qwen_init_command?: string | null;
        qwen_init_available?: boolean;
        project_command?: string | null;
        project_command_exists?: boolean;
        runtime_dir?: string | null;
        project_runtime_dir?: string | null;
        preferred_runtime_dir?: string | null;
        runtime_mismatch?: boolean;
      };
    };
  };
};

type RuntimeCheckItem = {
  name: string;
  status?: string;
  version?: string | null;
  detail?: string | null;
  command?: string | null;
  path?: string | null;
  exit_code?: number | null;
};

type ConsoleStatus = "idle" | "starting" | "running" | "stopping" | "stopped" | "exited" | "failed";

type ConsoleSession = {
  id: string;
  project_id: string;
  project_name: string;
  root_path: string;
  command: string[];
  status: ConsoleStatus;
  mode: string;
  log_path: string;
  team_events_path: string | null;
  team_events_exists: boolean;
  team_events_size: number;
  team_event_offset: number;
  chat_events_dir: string | null;
  chat_events_path: string | null;
  chat_events_exists: boolean;
  chat_events_size: number;
  chat_event_offset: number;
  token_usage?: Record<string, number>;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  exit_code?: number | null;
  error?: string | null;
};

type TeamEvent = {
  timestamp?: string;
  event?: string;
  agent_type?: string | null;
  agent_id?: string | null;
  tool_name?: string | null;
  decision?: string | null;
  reason?: string | null;
  cwd?: string | null;
  tool_input?: Record<string, unknown>;
  error?: string;
  raw?: string;
};

type ChatEvent = {
  timestamp?: string;
  kind?: string;
  agent?: string;
  title?: string;
  content?: string;
  tool_name?: string | null;
  status?: string | null;
  error?: string | null;
  model?: string | null;
  tokens?: number | null;
  record_type?: string | null;
  uuid?: string | null;
  parent_uuid?: string | null;
  request_id?: string | null;
  pair_id?: string | null;
  prompt_id?: string | null;
  response_id?: string | null;
  tool_input?: Record<string, unknown>;
};

type AgentTokenUsage = {
  agent: string;
  detail: string;
  model: string;
  tone: string;
  tokens: number;
  ratio: number;
};

type EnrichedChatEvent = ChatEvent & {
  domId: string;
  requestDomId?: string;
  resultDomId?: string;
  relatedRequestTitle?: string;
};

type PromptBuilderMessage = {
  role: "user" | "assistant";
  content: string;
};

type PromptBuilderRun = {
  id: string;
  project_id: string;
  project_name: string;
  status: "running" | "succeeded" | "failed";
  created_at: string;
  completed_at?: string | null;
  message: string;
  assistant_message: string;
  questions: string[];
  interview_questions?: InterviewQuestion[];
  final_prompt: string;
  prompt_lint?: PromptLint;
  prompt_evaluation?: PromptEvaluation;
  log_path: string;
};

type InterviewOption = {
  label: string;
  description?: string;
};

type InterviewQuestion = {
  id: string;
  header: string;
  question: string;
  options: InterviewOption[];
  allow_other?: boolean;
};

type PromptLint = {
  passed?: boolean;
  score?: number;
  issues?: string[];
  missing_sections?: string[];
};

type PromptEvaluation = {
  score?: number;
  issues?: string[];
  improvements?: string[];
  deterministic_repair_applied?: boolean;
};

type PromptBuilderEvent = {
  type: string;
  timestamp?: string;
  step?: string;
  title?: string;
  message?: string;
  questions?: string[];
  interview_questions?: InterviewQuestion[];
  prompt?: string;
  lint?: PromptLint;
  evaluation?: PromptEvaluation;
  error?: string;
  run?: PromptBuilderRun;
  intent?: Record<string, unknown>;
  queries?: string[];
  result_count?: number;
  files_read?: string[];
  results?: unknown;
};

type ModelTooltip = {
  text: string;
  top: number;
  left: number;
};

const emptySettings: KiwiSettings = {
  api_base_url: "https://api.t.drt.samsunglife.kr/llmproxy/v1",
  coder_api_base_url: "https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1",
  orchestrator_model: "Qwen3.5-397B",
  coder_model: "qwen3-coder-next",
  qwencode_command: "qwen.cmd",
  dangerous_mode: true,
  request_timeout_seconds: 180,
  max_context_chars: 262144,
  kk_docs_mcp_enabled: true,
  kk_docs_mcp_url: "http://100.254.193.25:3007/mcp",
  kk_code_analysis_mcp_enabled: false,
  kk_code_analysis_mcp_url: "",
  kk_mcp_token_set: false,
  api_key_set: false
};

export default function Home() {
  const [settings, setSettings] = useState<KiwiSettings>(emptySettings);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projectPath, setProjectPath] = useState("");
  const [consoleSession, setConsoleSession] = useState<ConsoleSession | null>(null);
  const [terminalLog, setTerminalLog] = useState("");
  const [teamEvents, setTeamEvents] = useState<TeamEvent[]>([]);
  const [chatEvents, setChatEvents] = useState<ChatEvent[]>([]);
  const [agentTokenTotals, setAgentTokenTotals] = useState<Record<string, number>>({});
  const [rightTab, setRightTab] = useState<"builder" | "chat">("builder");
  const [builderInput, setBuilderInput] = useState("");
  const [builderMessages, setBuilderMessages] = useState<PromptBuilderMessage[]>([]);
  const [builderEvents, setBuilderEvents] = useState<PromptBuilderEvent[]>([]);
  const [builderQuestions, setBuilderQuestions] = useState<string[]>([]);
  const [builderInterviewQuestions, setBuilderInterviewQuestions] = useState<InterviewQuestion[]>([]);
  const [builderInterviewAnswers, setBuilderInterviewAnswers] = useState<Record<string, string>>({});
  const [builderInterviewOther, setBuilderInterviewOther] = useState<Record<string, string>>({});
  const [builtPrompt, setBuiltPrompt] = useState("");
  const [builderRun, setBuilderRun] = useState<PromptBuilderRun | null>(null);
  const [builderRunning, setBuilderRunning] = useState(false);
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [commandText, setCommandText] = useState("");
  const [commandBarFocused, setCommandBarFocused] = useState(false);
  const [ultraworkMode, setUltraworkMode] = useState(false);
  const [ultraworkLocked, setUltraworkLocked] = useState(false);
  const terminalHostRef = useRef<HTMLDivElement | null>(null);
  const xtermRef = useRef<XTermType | null>(null);
  const fitAddonRef = useRef<FitAddonType | null>(null);
  const inputSessionRef = useRef<string | null>(null);
  const builderSourceRef = useRef<EventSource | null>(null);
  const commandTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const ultraworkInjectedRef = useRef(false);
  const submitAfterCompositionRef = useRef(false);
  const chatListRef = useRef<HTMLDivElement | null>(null);
  const chatPinnedToBottomRef = useRef(true);
  const pendingFitFrameRef = useRef<number | null>(null);
  const lastResizeSentRef = useRef<{ sessionId: string; cols: number; rows: number } | null>(null);
  const [highlightedChatId, setHighlightedChatId] = useState<string | null>(null);
  const [modelTooltip, setModelTooltip] = useState<ModelTooltip | null>(null);

  const consoleStatus: ConsoleStatus = consoleSession?.status ?? "idle";
  const consoleRunning = consoleStatus === "running" || consoleStatus === "starting";

  const showModelTooltip = useCallback((text: string, target: HTMLElement) => {
    const rect = target.getBoundingClientRect();
    const width = Math.min(300, window.innerWidth - 24);
    const left = Math.min(rect.right + 8, Math.max(12, window.innerWidth - width - 12));
    const top = Math.min(Math.max(rect.top + rect.height / 2, 20), window.innerHeight - 20);
    setModelTooltip({ text, top, left });
  }, []);

  const hideModelTooltip = useCallback(() => {
    setModelTooltip(null);
  }, []);

  const modelRoles = useMemo(
    () => [
      {
        role: "kiwi",
        detail: "Orchestrator",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "메인 조율자입니다. 사용자 의도를 정리하고 계획, 위임, 결과 통합, 최종 보고를 담당합니다."
      },
      {
        role: "planner-35",
        detail: "Plan",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "요구사항, 누락 정보, 실행 순서, acceptance criteria를 정리해야 할 때 활성화됩니다."
      },
      {
        role: "architect-35",
        detail: "Design",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "영향 범위가 넓거나 cross-module, 데이터, 보안, 설계 판단이 필요한 작업에서 구조와 위험을 검토합니다."
      },
      {
        role: "reviewer-35",
        detail: "Review",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "완료 전 diff, 검증 결과, 누락 테스트, 회귀 위험을 독립적으로 검토할 때 활성화됩니다."
      },
      {
        role: "debugger-35",
        detail: "Debug",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "실패 원인 분석, 반복 tool 실패, 테스트 실패, 애매한 런타임 문제를 깊게 추적할 때 사용합니다."
      },
      {
        role: "coder-35",
        detail: "Code",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "Qwen3.5-397B 구현 담당자입니다. 코드 수정, 파일 작성, 테스트 추가, 좁은 repair slice를 맡습니다."
      },
      {
        role: "explorer-next",
        detail: "Explore",
        model: settings.coder_model,
        tone: "coder",
        description: "coder endpoint를 쓰는 빠른 read-only 탐색 역할입니다. 독립 질문은 최대 5개까지 병렬 호출할 수 있습니다."
      },
      {
        role: "tester-35",
        detail: "Verify",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "검증 명령 실행, 결과 해석, 테스트 실패 재현 등 독립 확인이 필요할 때 활성화됩니다."
      }
    ],
    [settings.coder_model, settings.orchestrator_model]
  );

  const agentTokenUsage = useMemo<AgentTokenUsage[]>(() => {
    const totals = new Map<string, number>();
    for (const [agent, tokens] of Object.entries(agentTokenTotals)) {
      if (!Number.isFinite(tokens) || tokens <= 0) {
        continue;
      }
      const key = normalizeAgentKey(agent);
      totals.set(key, (totals.get(key) ?? 0) + tokens);
    }
    const entries = Array.from(totals.entries());
    const maxTokens = Math.max(1, ...entries.map(([, tokens]) => tokens));
    return entries
      .map(([agent, tokens]) => {
        const role = modelRoles.find((item) => normalizeAgentKey(item.role) === agent);
        return {
          agent: role?.role ?? agent,
          detail: role?.detail ?? "Active",
          model: role?.model ?? "",
          tone: role?.tone ?? "coder",
          tokens,
          ratio: tokens / maxTokens
        };
      })
      .sort((a, b) => b.tokens - a.tokens);
  }, [agentTokenTotals, modelRoles]);

  const enrichedChatEvents = useMemo<EnrichedChatEvent[]>(() => {
    const enriched: EnrichedChatEvent[] = chatEvents.map((event, index) => ({
      ...event,
      domId: chatDomId(event, index)
    }));
    const requestByPair = new Map<string, EnrichedChatEvent>();
    const lastRequestByAgent = new Map<string, EnrichedChatEvent>();
    for (const event of enriched) {
      if (event.kind === "agent_request") {
        const key = event.pair_id || event.request_id || event.uuid || event.domId;
        requestByPair.set(key, event);
        lastRequestByAgent.set(normalizeAgentKey(event.agent || ""), event);
        continue;
      }
      if (event.kind === "agent_result") {
        const key = event.pair_id || event.request_id || "";
        const request =
          (key ? requestByPair.get(key) : undefined) ||
          lastRequestByAgent.get(normalizeAgentKey(event.agent || ""));
        if (request) {
          event.requestDomId = request.domId;
          event.relatedRequestTitle = request.title || compactText(request.content || "", 90) || request.agent || "agent request";
          request.resultDomId = event.domId;
        }
        continue;
      }
      if (event.kind === "completion" && normalizeAgentKey(event.agent || "") !== "kiwi") {
        const request = lastRequestByAgent.get(normalizeAgentKey(event.agent || ""));
        if (request) {
          event.requestDomId = request.domId;
          event.relatedRequestTitle = request.title || compactText(request.content || "", 90) || request.agent || "agent request";
          request.resultDomId ??= event.domId;
        }
      }
    }
    return enriched;
  }, [chatEvents]);

  const fitTerminalSafely = useCallback(() => {
    const terminal = xtermRef.current;
    const fitAddon = fitAddonRef.current;
    const host = terminalHostRef.current;
    if (!terminal || !fitAddon || !host) {
      return;
    }
    const rect = host.getBoundingClientRect();
    if (rect.width < 240 || rect.height < 180) {
      return;
    }
    const proposed = fitAddon.proposeDimensions();
    if (!proposed) {
      return;
    }
    const cols = clampTerminalSize(proposed.cols, TERMINAL_MIN_COLS, TERMINAL_MAX_COLS);
    const rows = clampTerminalSize(proposed.rows, TERMINAL_MIN_ROWS, TERMINAL_MAX_ROWS);
    if (cols !== terminal.cols || rows !== terminal.rows) {
      terminal.resize(cols, rows);
    }
    const sessionId = inputSessionRef.current;
    const last = lastResizeSentRef.current;
    if (!sessionId || (last?.sessionId === sessionId && last.cols === cols && last.rows === rows)) {
      return;
    }
    lastResizeSentRef.current = { sessionId, cols, rows };
    void api(`/api/ultrawork/sessions/${sessionId}/resize`, {
      method: "POST",
      body: JSON.stringify({ cols, rows })
    }).catch(showError);
  }, []);

  const loadSettings = useCallback(async () => {
    const data = await api<KiwiSettings>("/api/settings");
    setSettings(data);
  }, []);

  const loadProjects = useCallback(async () => {
    const data = await api<Project[]>("/api/projects");
    setProjects(data);
    if (!selectedProject && data.length > 0) {
      setSelectedProject(data[0]);
      setProjectPath(data[0].root_path);
    }
  }, [selectedProject]);

  useEffect(() => {
    loadSettings().catch(showError);
    loadProjects().catch(showError);
  }, [loadProjects, loadSettings]);

  useEffect(() => {
    if (!consoleSession?.id) {
      return;
    }
    const source = new EventSource(`${API_BASE}/api/ultrawork/sessions/${consoleSession.id}/events`);
    const handle = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "snapshot") {
        setConsoleSession(payload.session);
        setTerminalLog(payload.terminal ?? "");
        resetTerminal(payload.terminal || "콘솔이 연결되었습니다.\r\n");
        setTeamEvents(payload.team_events ?? []);
        setChatEvents(payload.chat_events ?? []);
        setAgentTokenTotals(payload.session?.token_usage ?? {});
      }
      if (payload.type === "terminal") {
        setTerminalLog((current) => `${current}${payload.data ?? ""}`.slice(-240000));
        xtermRef.current?.write(payload.data ?? "");
      }
      if (payload.type === "team_event") {
        setTeamEvents((current) => [...current, payload.event].slice(-300));
      }
      if (payload.type === "chat_event") {
        const event = payload.event as ChatEvent;
        setChatEvents((current) => [...current, event].slice(-500));
        if (payload.token_usage) {
          setAgentTokenTotals(payload.token_usage);
        } else {
          setAgentTokenTotals((current) => accumulateTokenTotals(current, event));
        }
      }
      if (payload.type === "status" || payload.type === "done") {
        setConsoleSession(payload.session);
      }
      if (payload.type === "team_error") {
        setNotice(`team-events tail 실패: ${payload.error}`);
      }
      if (payload.type === "chat_error") {
        setNotice(`chat jsonl tail 실패: ${payload.error}`);
      }
    };
    ["snapshot", "terminal", "team_event", "chat_event", "status", "done", "team_error", "chat_error"].forEach((type) =>
      source.addEventListener(type, handle)
    );
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, [consoleSession?.id]);

  useEffect(() => {
    if (!terminalHostRef.current || xtermRef.current) {
      return;
    }
    let cancelled = false;
    let terminal: XTermType | null = null;
    let resizeObserver: ResizeObserver | null = null;

    void Promise.all([import("@xterm/xterm"), import("@xterm/addon-fit")]).then(
      ([{ Terminal: BrowserTerminal }, { FitAddon }]) => {
        if (cancelled || !terminalHostRef.current) {
          return;
        }
        terminal = new BrowserTerminal({
          cols: 160,
          rows: 44,
          convertEol: false,
          cursorBlink: true,
          disableStdin: false,
          fontFamily: '"SFMono-Regular", "JetBrains Mono", Consolas, "Liberation Mono", Menlo, monospace',
          fontSize: 13,
          rightClickSelectsWord: true,
          scrollback: 10000,
          theme: {
            background: "#05080f",
            foreground: "#e2e8f5",
            cursor: "#6aa9ff",
            cursorAccent: "#05080f",
            selectionBackground: "rgba(77, 150, 255, 0.32)",
            black: "#05080f",
            red: "#ff7a82",
            green: "#65e3a4",
            yellow: "#f1c47a",
            blue: "#6aa9ff",
            magenta: "#69b7ff",
            cyan: "#5ddbe6",
            white: "#e2e8f5",
            brightBlack: "#3a4663",
            brightRed: "#ff9aa3",
            brightGreen: "#8aedba",
            brightYellow: "#f8d590",
            brightBlue: "#8cb9ff",
            brightMagenta: "#9ed0ff",
            brightCyan: "#7aebf2",
            brightWhite: "#f5f7fb"
          },
          windowsMode: true
        });
        const fitAddon = new FitAddon();
        terminal.loadAddon(fitAddon);
        terminal.open(terminalHostRef.current);
        xtermRef.current = terminal;
        fitAddonRef.current = fitAddon;
        fitTerminalSafely();
        terminal.write("콘솔을 시작하면 qwencode 출력이 여기에 실시간으로 표시됩니다.\r\n");
        terminal.attachCustomKeyEventHandler((event) => {
          if (event.type === "keydown" && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "c") {
            const selection = terminal?.getSelection();
            if (selection) {
              event.preventDefault();
              void copyTerminalSelection(selection);
              return false;
            }
          }
          if (event.type === "keydown" && event.key === "Tab") {
            event.preventDefault();
            const sessionId = inputSessionRef.current;
            if (sessionId) {
              void api(`/api/ultrawork/sessions/${sessionId}/input`, {
                method: "POST",
                body: JSON.stringify({ text: "\t", submit: false })
              }).catch(showError);
            }
            return false;
          }
          return true;
        });
        terminal.onData((data) => {
          const sessionId = inputSessionRef.current;
          if (!sessionId) {
            return;
          }
          void api(`/api/ultrawork/sessions/${sessionId}/input`, {
            method: "POST",
            body: JSON.stringify({ text: data, submit: false })
          }).catch(showError);
        });
        resizeObserver = new ResizeObserver(() => {
          if (pendingFitFrameRef.current !== null) {
            window.cancelAnimationFrame(pendingFitFrameRef.current);
          }
          pendingFitFrameRef.current = window.requestAnimationFrame(() => {
            pendingFitFrameRef.current = null;
            fitTerminalSafely();
          });
        });
        resizeObserver.observe(terminalHostRef.current);
      }
    );

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (pendingFitFrameRef.current !== null) {
        window.cancelAnimationFrame(pendingFitFrameRef.current);
        pendingFitFrameRef.current = null;
      }
      terminal?.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, [fitTerminalSafely]);

  useEffect(() => {
    inputSessionRef.current = consoleRunning && consoleSession ? consoleSession.id : null;
    if (!consoleRunning || !consoleSession) {
      lastResizeSentRef.current = null;
    } else {
      window.requestAnimationFrame(fitTerminalSafely);
    }
  }, [consoleRunning, consoleSession, fitTerminalSafely]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(fitTerminalSafely);
    const timeout = window.setTimeout(fitTerminalSafely, 520);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timeout);
    };
  }, [fitTerminalSafely, leftPanelOpen, rightPanelOpen]);

  useEffect(() => {
    return () => {
      builderSourceRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (rightTab !== "chat" || !chatPinnedToBottomRef.current) {
      return;
    }
    window.requestAnimationFrame(() => scrollChatToBottom());
  }, [enrichedChatEvents.length, rightTab]);

  async function pickFolder() {
    setBusy(true);
    try {
      const data = await api<{ path: string | null; cancelled: boolean; error: string | null }>(
        "/api/folders/pick",
        { method: "POST" }
      );
      if (data.error) {
        setNotice(data.error);
      } else if (data.path) {
        setProjectPath(data.path);
      }
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  async function initializeProject() {
    if (!projectPath.trim()) {
      setNotice("프로젝트 경로를 입력하세요.");
      return;
    }
    setBusy(true);
    try {
      const data = await api<{ project: Project }>("/api/projects/initialize", {
        method: "POST",
        body: JSON.stringify({ path: projectPath.trim(), extra_notes: null })
      });
      setSelectedProject(data.project);
      setProjects((current) => [data.project, ...current.filter((item) => item.id !== data.project.id)]);
      setNotice("초기화가 완료되었습니다. KIWI.md, docs/, qwen 하네스를 확인했습니다.");
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  async function startConsole() {
    if (!selectedProject) {
      setNotice("먼저 프로젝트를 선택하거나 초기화하세요.");
      return;
    }
    setBusy(true);
    try {
      fitTerminalSafely();
      const cols = clampTerminalSize(xtermRef.current?.cols ?? 160, TERMINAL_MIN_COLS, TERMINAL_MAX_COLS);
      const rows = clampTerminalSize(xtermRef.current?.rows ?? 44, TERMINAL_MIN_ROWS, TERMINAL_MAX_ROWS);
      const data = await api<{ session: ConsoleSession }>("/api/ultrawork/sessions", {
        method: "POST",
        body: JSON.stringify({
          project_id: selectedProject.id,
          cols,
          rows
        })
      });
      setConsoleSession(data.session);
      setTerminalLog("");
      setTeamEvents([]);
      setChatEvents([]);
      setAgentTokenTotals({});
      setNotice(`Ultrawork Console 시작: ${data.session.mode}`);
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  async function stopConsole() {
    if (!consoleSession) {
      return;
    }
    setBusy(true);
    try {
      const data = await api<{ session: ConsoleSession }>(
        `/api/ultrawork/sessions/${consoleSession.id}/stop`,
        { method: "POST" }
      );
      setConsoleSession(data.session);
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  async function sendQuickPrompt(text: string) {
    if (!consoleSession) {
      setNotice("먼저 콘솔을 시작하세요.");
      return;
    }
    const prepared = prepareConsoleText(text);
    try {
      await sendConsoleText(prepared.text);
      lockUltraworkMode(prepared.lock);
    } catch (error) {
      showError(error);
    }
  }

  async function submitCommandBar() {
    const text = commandTextareaRef.current?.value ?? commandText;
    if (!text.trim()) {
      return;
    }
    if (!consoleSession || !consoleRunning) {
      setNotice("먼저 콘솔을 시작하세요.");
      return;
    }
    const prepared = prepareConsoleText(text);
    try {
      await sendConsoleText(prepared.text);
      lockUltraworkMode(prepared.lock);
      setCommandText("");
      setCommandBarFocused(false);
      commandTextareaRef.current?.blur();
    } catch (error) {
      showError(error);
    }
  }

  async function sendConsoleText(text: string) {
    if (!consoleSession) {
      setNotice("먼저 콘솔을 시작하세요.");
      return;
    }
    await api(`/api/ultrawork/sessions/${consoleSession.id}/input`, {
      method: "POST",
      body: JSON.stringify({ text, submit: true, bracketed_paste: true })
    });
    xtermRef.current?.focus();
  }

  function prepareConsoleText(text: string): { text: string; lock: boolean } {
    if (!ultraworkMode || ultraworkInjectedRef.current) {
      return { text, lock: false };
    }
    const alreadyPrefixed = /^\s*ultrawork(?:\r?\n|$)/i.test(text);
    return {
      text: alreadyPrefixed ? text : `ultrawork\n\n${text}`,
      lock: true
    };
  }

  function lockUltraworkMode(shouldLock: boolean) {
    if (!shouldLock) {
      return;
    }
    ultraworkInjectedRef.current = true;
    setUltraworkMode(true);
    setUltraworkLocked(true);
  }

  function toggleUltraworkMode() {
    if (ultraworkLocked) {
      return;
    }
    setUltraworkMode((current) => !current);
  }

  function delay(ms: number) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function handleCommandKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (event.nativeEvent.isComposing) {
        submitAfterCompositionRef.current = true;
        return;
      }
      void submitCommandBar();
    }
  }

  function handleCommandCompositionEnd() {
    if (!submitAfterCompositionRef.current) {
      return;
    }
    submitAfterCompositionRef.current = false;
    window.setTimeout(() => void submitCommandBar(), 0);
  }

  async function buildUltraworkPrompt(event?: FormEvent) {
    event?.preventDefault();
    const text = builderInput.trim();
    if (!selectedProject) {
      setNotice("먼저 프로젝트를 선택하거나 초기화하세요.");
      return;
    }
    if (!text || builderRunning) {
      return;
    }
    const history = builderMessages.slice(-12);
    await startPromptBuilderRun(text, history);
  }

  async function startPromptBuilderRun(text: string, history: PromptBuilderMessage[]) {
    if (!selectedProject) {
      setNotice("먼저 프로젝트를 선택하거나 초기화하세요.");
      return;
    }
    setBuilderInput("");
    setBuilderMessages((current) => [...current, { role: "user", content: text }]);
    setBuilderEvents([]);
    setBuilderQuestions([]);
    setBuilderInterviewQuestions([]);
    setBuilderInterviewAnswers({});
    setBuilderInterviewOther({});
    setBuiltPrompt("");
    setBuilderRun(null);
    setBuilderRunning(true);
    setRightTab("builder");

    try {
      const data = await api<{ run: PromptBuilderRun }>("/api/prompt-builder/runs", {
        method: "POST",
        body: JSON.stringify({
          project_id: selectedProject.id,
          message: text,
          history
        })
      });
      setBuilderRun(data.run);
      builderSourceRef.current?.close();
      const source = new EventSource(`${API_BASE}/api/prompt-builder/runs/${data.run.id}/events`);
      builderSourceRef.current = source;
      const handle = (streamEvent: MessageEvent<string>) => {
        const payload = JSON.parse(streamEvent.data) as PromptBuilderEvent;
        if (payload.type === "snapshot") {
          setBuilderEvents(((payload as PromptBuilderEvent & { events?: PromptBuilderEvent[] }).events ?? []).slice(-200));
          applyBuilderRun(payload.run);
          return;
        }
        setBuilderEvents((current) => [...current, payload].slice(-200));
        if (payload.type === "question" || payload.type === "interview") {
          setBuilderQuestions(payload.questions ?? []);
          setBuilderInterviewQuestions(payload.interview_questions ?? []);
          const questionText = [payload.message, ...(payload.questions ?? [])].filter(Boolean).join("\n");
          if (questionText) {
            appendBuilderMessage("assistant", questionText);
          }
        }
        if (payload.type === "final_prompt") {
          setBuiltPrompt(payload.prompt ?? "");
          setBuilderInterviewQuestions([]);
          appendBuilderMessage("assistant", payload.message || "ultrawork 지시 프롬프트를 만들었습니다.");
        }
        if (payload.type === "prompt_evaluation" && payload.prompt) {
          setBuiltPrompt(payload.prompt);
        }
        if (payload.type === "done") {
          setBuilderRunning(false);
          applyBuilderRun(payload.run);
          source.close();
        }
        if (payload.type === "error") {
          setBuilderRunning(false);
          applyBuilderRun(payload.run);
          setNotice(payload.error ?? "프롬프트 빌더 실행이 실패했습니다.");
          source.close();
        }
      };
      [
        "snapshot",
        "step",
        "intent",
        "file_search",
        "question",
        "interview",
        "prompt_lint",
        "prompt_evaluation",
        "final_prompt",
        "done",
        "error"
      ].forEach((type) => source.addEventListener(type, handle));
      source.onerror = () => {
        setBuilderRunning(false);
        source.close();
      };
    } catch (error) {
      setBuilderRunning(false);
      showError(error);
    }
  }

  async function submitInterviewAnswers() {
    if (!builderInterviewQuestions.length || builderRunning) {
      return;
    }
    const missing = builderInterviewQuestions.find((question) => !resolveInterviewAnswer(question).trim());
    if (missing) {
      setNotice(`'${missing.header}' 질문에 답변을 선택하거나 직접 입력하세요.`);
      return;
    }
    const lines = builderInterviewQuestions.map((question) => {
      const answer = resolveInterviewAnswer(question).trim();
      return `- ${question.header} / ${question.question}: ${answer}`;
    });
    const content = `[Prompt Builder interview answers]\n${lines.join("\n")}`;
    const rerunMessage =
      "사용자 인터뷰 답변입니다. 이 답변을 반영해서 최초 요청에 대한 최종 ultrawork 프롬프트를 완성해라.\n\n" +
      content;
    const history: PromptBuilderMessage[] = [
      ...builderMessages.slice(-10),
      { role: "assistant", content: "추가 확인이 필요해 사용자 인터뷰를 요청했습니다." },
      { role: "user", content }
    ];
    await startPromptBuilderRun(rerunMessage, history);
  }

  function resolveInterviewAnswer(question: InterviewQuestion) {
    const selected = builderInterviewAnswers[question.id] ?? "";
    if (selected === "__other__") {
      return builderInterviewOther[question.id] ?? "";
    }
    return selected;
  }

  function applyBuilderRun(run?: PromptBuilderRun) {
    if (!run) {
      return;
    }
    setBuilderRun(run);
    if (run.questions?.length) {
      setBuilderQuestions(run.questions);
    }
    if (run.interview_questions?.length) {
      setBuilderInterviewQuestions(run.interview_questions);
    }
    if (run.final_prompt) {
      setBuiltPrompt(run.final_prompt);
      setBuilderInterviewQuestions([]);
    }
    if (run.status !== "running") {
      setBuilderRunning(false);
    }
  }

  function appendBuilderMessage(role: PromptBuilderMessage["role"], content: string) {
    const trimmed = content.trim();
    if (!trimmed) {
      return;
    }
    setBuilderMessages((current) => [...current, { role, content: trimmed }].slice(-40));
  }

  async function sendBuiltPromptToConsole() {
    if (!builtPrompt.trim()) {
      return;
    }
    await sendQuickPrompt(builtPrompt);
  }

  async function copyBuiltPrompt() {
    if (!builtPrompt.trim()) {
      return;
    }
    try {
      await navigator.clipboard.writeText(builtPrompt);
      setNotice("프롬프트를 클립보드에 복사했습니다.");
    } catch {
      setNotice("브라우저 클립보드 권한이 없어 복사하지 못했습니다.");
    }
  }

  async function copyTerminalSelection(selection: string) {
    try {
      await navigator.clipboard.writeText(selection);
      setNotice("터미널 선택 영역을 클립보드에 복사했습니다.");
    } catch {
      setNotice("브라우저 클립보드 권한이 없어 터미널 선택 영역을 복사하지 못했습니다.");
    }
  }

  function selectProject(projectId: string) {
    const project = projects.find((item) => item.id === projectId);
    if (!project) {
      return;
    }
    setSelectedProject(project);
    setProjectPath(project.root_path);
    setConsoleSession(null);
    setTerminalLog("");
    setTeamEvents([]);
    setChatEvents([]);
    setAgentTokenTotals({});
    setBuilderMessages([]);
    setBuilderEvents([]);
    setBuilderQuestions([]);
    setBuilderInterviewQuestions([]);
    setBuilderInterviewAnswers({});
    setBuilderInterviewOther({});
    setBuiltPrompt("");
    setBuilderRun(null);
    setBuilderRunning(false);
    builderSourceRef.current?.close();
    resetTerminal("프로젝트가 변경되었습니다. 콘솔을 시작하세요.\r\n");
  }

  function showError(error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    setNotice(message);
  }

  function resetTerminal(text: string) {
    const terminal = xtermRef.current;
    if (!terminal) {
      return;
    }
    terminal.reset();
    terminal.write(normalizeTerminalSnapshot(text));
  }

  function handleChatScroll() {
    const node = chatListRef.current;
    if (!node) {
      return;
    }
    chatPinnedToBottomRef.current = node.scrollHeight - node.scrollTop - node.clientHeight < 36;
  }

  function scrollChatToBottom() {
    const node = chatListRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }

  function jumpToChatItem(id?: string) {
    if (!id) {
      return;
    }
    const node = document.getElementById(id);
    if (!node) {
      return;
    }
    chatPinnedToBottomRef.current = false;
    node.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlightedChatId(id);
    window.setTimeout(() => {
      setHighlightedChatId((current) => (current === id ? null : current));
    }, 1400);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <img src="/kiwi-icon.svg" alt="kiwi" />
          </span>
          <div className="brand-text">
            <span className="brand-name">kiwi</span>
            <span className="brand-tag">
              <code>ultrawork</code>Console for SSLife · Platform
            </span>
          </div>
        </div>

        <div className="topbar-center">
          {selectedProject ? (
            <div className="project-pill" title={selectedProject.root_path}>
              <span className="pill-ico">
                <FolderOpen size={14} />
              </span>
              <span className="pill-name">{selectedProject.name}</span>
              <span className="pill-path">{selectedProject.root_path}</span>
            </div>
          ) : null}
        </div>

        <div className="topbar-actions">
          <div className="topbar-metrics" aria-label="session summary">
            <span className="topbar-metric">
              <strong>{formatConsoleStatus(consoleStatus)}</strong>
              <small>session</small>
            </span>
            <span className="topbar-metric">
              <strong>{teamEvents.length + chatEvents.length}</strong>
              <small>events</small>
            </span>
            <span className="topbar-metric">
              <strong>{formatTokens(agentTokenUsage.reduce((total, item) => total + item.tokens, 0))}</strong>
              <small>tokens</small>
            </span>
          </div>
        </div>
      </header>

      {notice ? (
        <div className="notice-layer" role="status" aria-live="polite">
          <div className="notice info">
            <div className="notice-body">
              <strong>KIWI</strong>
              <p>{notice}</p>
            </div>
            <button className="notice-close" onClick={() => setNotice("")} title="닫기" aria-label="알림 닫기">
              <X size={16} />
            </button>
          </div>
        </div>
      ) : null}

      <div
        className={`workspace console-workspace ${leftPanelOpen ? "left-open" : "left-closed"} ${
          rightPanelOpen ? "inspector-open" : "inspector-closed"
        }`}
      >
        {!leftPanelOpen ? (
          <button
            className="panel-rescue-toggle panel-rescue-left"
            type="button"
            onClick={() => setLeftPanelOpen(true)}
            title="좌측 패널 열기"
            aria-label="좌측 패널 열기"
          >
            <PanelLeftOpen size={19} />
          </button>
        ) : null}
        {!rightPanelOpen ? (
          <button
            className="panel-rescue-toggle panel-rescue-right"
            type="button"
            onClick={() => setRightPanelOpen(true)}
            title="우측 패널 열기"
            aria-label="우측 패널 열기"
          >
            <PanelRightOpen size={19} />
          </button>
        ) : null}
        <section className={`left-pane left-panel ${leftPanelOpen ? "open" : "closed"}`}>
          <div className="left-panel-content" aria-hidden={!leftPanelOpen}>
            <button
              className="left-panel-close-button icon-button ghost square"
              type="button"
              onClick={() => setLeftPanelOpen(false)}
              title="좌측 패널 닫기"
              aria-label="좌측 패널 닫기"
            >
              <PanelLeftClose size={17} />
            </button>

          <section className={`ultrawork-panel ${ultraworkMode ? "on" : "off"} ${ultraworkLocked ? "locked" : ""}`}>
            <div className="ultrawork-mode-row">
              <div className="ultrawork-mode-left">
                <div className="section-title">
                  <Flame size={18} />
                  <h2>ultrawork mode</h2>
                </div>
                <div className="ultrawork-switch-row">
                  <button
                    type="button"
                    className={`ultrawork-switch ${ultraworkMode ? "on" : ""}`}
                    role="switch"
                    aria-checked={ultraworkMode}
                    aria-label="ultrawork mode"
                    disabled={ultraworkLocked}
                    onClick={toggleUltraworkMode}
                  >
                    <span />
                  </button>
                  <strong>{ultraworkMode ? "ON" : "OFF"}</strong>
                </div>
              </div>
              <button
                className={
                  consoleRunning
                    ? "icon-button wide stop-console-button"
                    : "icon-button wide primary start-console-button"
                }
                onClick={consoleRunning ? stopConsole : startConsole}
                disabled={busy || (!consoleRunning && !selectedProject)}
              >
                {busy ? (
                  <Loader2 className="spin" size={18} />
                ) : consoleRunning ? (
                  <Square size={18} />
                ) : (
                  <Play size={18} />
                )}
                {consoleRunning ? "중지" : "콘솔 시작"}
              </button>
            </div>
          </section>

          <details className="project-panel collapsible-panel" open>
            <summary className="section-title">
              <FolderOpen size={18} />
              <h2>프로젝트</h2>
            </summary>
            <div className="collapsible-body">
              {projects.length > 0 ? (
                <label>
                  최근 프로젝트
                  <select value={selectedProject?.id ?? ""} onChange={(event) => selectProject(event.target.value)}>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name} - {project.root_path}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <div className="path-row">
                <input
                  value={projectPath}
                  placeholder="예: C:\\work\\my-project"
                  onChange={(event) => setProjectPath(event.target.value)}
                />
                <button className="icon-button" onClick={pickFolder} disabled={busy} title="폴더 선택">
                  <FolderOpen size={18} />
                </button>
                <button className="icon-button primary" onClick={initializeProject} disabled={busy} title="초기화">
                  {busy ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
                  초기화
                </button>
              </div>
              {selectedProject?.summary.runtime_checks ? (
                <div className="project-runtime-summary" aria-label="프로젝트 런타임 체크">
                  <div className="project-runtime-heading">
                    <strong>런타임 체크</strong>
                    <span>{formatRuntimeCheckedAt(selectedProject.summary.runtime_checks.checked_at)}</span>
                  </div>
                  <div className="runtime-check-list">
                    {(selectedProject.summary.runtime_checks.items ?? []).map((item) => (
                      <div className="runtime-check-row" key={item.name}>
                        <strong>{item.name}</strong>
                        <code title={item.detail ?? item.version ?? ""}>{item.version ?? item.detail ?? "not found"}</code>
                        <span className={`runtime-status ${runtimeStatusClass(item.status)}`}>{formatRuntimeStatus(item.status)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="qwen-harness-state">
                    <span>qwen-init</span>
                    <strong className={selectedProject.summary.runtime_checks.qwen?.qwen_init_available ? "ok" : "warn"}>
                      {selectedProject.summary.runtime_checks.qwen?.qwen_init_available ? "ready" : "missing"}
                    </strong>
                    <span>qwen.cmd</span>
                    <strong className={selectedProject.summary.runtime_checks.qwen?.project_command_exists ? "ok" : "warn"}>
                      {selectedProject.summary.runtime_checks.qwen?.project_command_exists ? "ready" : "not created"}
                    </strong>
                    <span>runtime</span>
                    <code>{selectedProject.summary.runtime_checks.qwen?.runtime_dir ?? "not found"}</code>
                    {selectedProject.summary.runtime_checks.qwen?.runtime_mismatch ? (
                      <>
                        <span>runtime mismatch</span>
                        <strong className="warn">re-run qwen-init</strong>
                      </>
                    ) : null}
                  </div>
                </div>
              ) : selectedProject ? (
                <div className="project-runtime-summary muted">
                  <div className="project-runtime-heading">
                    <strong>런타임 체크</strong>
                    <span>초기화를 다시 실행하면 표시됩니다.</span>
                  </div>
                </div>
              ) : null}
            </div>
          </details>

          <details className="runtime-panel collapsible-panel" open>
            <summary className="section-title">
              <BrainCircuit size={18} />
              <h2>AI 모델 정보</h2>
            </summary>
            <div className="runtime-grid compact-models collapsible-body">
              <div className="model-role-table" aria-label="Qwen runtime model roles">
                {modelRoles.map((item) => (
                  <div className="model-role-row" key={item.role}>
                    <span className="model-role-name">
                      <strong>{item.role}</strong>
                      <small>{item.detail}</small>
                      <span
                        className="agent-info"
                        tabIndex={0}
                        aria-label={`${item.role} 역할 설명`}
                        onMouseEnter={(event) => showModelTooltip(item.description, event.currentTarget)}
                        onMouseLeave={hideModelTooltip}
                        onFocus={(event) => showModelTooltip(item.description, event.currentTarget)}
                        onBlur={hideModelTooltip}
                      >
                        <Info size={12} />
                      </span>
                    </span>
                    <span className={`model-badge ${item.tone}`}>{item.model}</span>
                  </div>
                ))}
                <div className="model-role-row runtime-command-row">
                  <span className="model-role-name">
                    <strong>qwencode</strong>
                    <small>Runtime</small>
                  </span>
                  <code>{settings.qwencode_command}</code>
                </div>
                <div className="model-role-row runtime-command-row">
                  <span className="model-role-name">
                    <strong>kk-docs MCP</strong>
                    <small>{settings.kk_docs_mcp_enabled ? "enabled" : "disabled"}</small>
                  </span>
                  <code>{settings.kk_docs_mcp_enabled ? settings.kk_docs_mcp_url : "disabled"}</code>
                </div>
                <div className="model-role-row runtime-command-row">
                  <span className="model-role-name">
                    <strong>kk-code-analysis MCP</strong>
                    <small>{settings.kk_code_analysis_mcp_enabled ? "enabled" : "disabled"}</small>
                  </span>
                  <code>{settings.kk_code_analysis_mcp_enabled ? settings.kk_code_analysis_mcp_url : "disabled"}</code>
                </div>
              </div>
            </div>
          </details>

          <details className="token-panel collapsible-panel" open>
            <summary className="section-title">
              <ListChecks size={18} />
              <h2>AGENT TOKENS</h2>
            </summary>
            <div className="agent-token-usage collapsible-body" aria-label="Agent token usage">
              <div className="agent-token-title">
                <strong>Token usage</strong>
                <span>new console session</span>
              </div>
              {agentTokenUsage.length === 0 ? (
                <div className="agent-token-empty">활성화된 agent token 사용량이 아직 없습니다.</div>
              ) : (
                agentTokenUsage.map((item) => (
                  <div className="agent-token-row" key={item.agent}>
                    <span className="agent-token-agent">
                      <strong>{item.agent}</strong>
                      <small>{item.detail}</small>
                    </span>
                    <span className="agent-token-bar" aria-hidden>
                      <span className={`agent-token-fill ${item.tone}`} style={{ width: `${Math.max(4, Math.round(item.ratio * 100))}%` }} />
                    </span>
                    <code>{formatTokens(item.tokens)}</code>
                  </div>
                ))
              )}
            </div>
          </details>

          {modelTooltip ? (
            <div
              className="agent-info-tooltip"
              style={{ top: modelTooltip.top, left: modelTooltip.left }}
              role="tooltip"
            >
              {modelTooltip.text}
            </div>
          ) : null}

          </div>
        </section>

        <section className="terminal-panel console-panel">
          <div className="terminal-area">
            <header className="terminal-head">
              <div className="terminal-head-left">
                <div className="tdots" aria-hidden>
                  <span />
                  <span />
                  <span />
                </div>
                <span className="terminal-title">
                  <strong>qwencode</strong>
                  {selectedProject ? ` · ${selectedProject.root_path}` : ""}
                  {consoleSession?.mode ? ` · ${consoleSession.mode}` : ""}
                </span>
              </div>
            </header>
            <div ref={terminalHostRef} className="terminal console-terminal" />
          </div>

          <div className={`terminal-statusbar ${commandBarFocused ? "command-focused" : ""}`}>
            <div
              className={`terminal-command-bar ${commandBarFocused ? "focused" : ""} ${
                consoleRunning ? "" : "disabled"
              }`}
            >
              <span className="command-bar-prompt" aria-hidden>❯</span>
              <textarea
                ref={commandTextareaRef}
                className="command-bar-input"
                value={commandText}
                onChange={(event) => setCommandText(event.target.value)}
                onFocus={() => setCommandBarFocused(true)}
                onBlur={() => setCommandBarFocused(false)}
                onKeyDown={handleCommandKeyDown}
                onCompositionEnd={handleCommandCompositionEnd}
                placeholder={
                  consoleRunning
                    ? "qwencode 터미널로 바로 전송 · Enter 실행, Shift+Enter 줄바꿈"
                    : "콘솔을 먼저 시작하세요"
                }
                disabled={!consoleRunning}
                spellCheck={false}
                rows={1}
              />
              <span className="command-bar-hint" aria-hidden>
                Enter ↵ · Shift+Enter ⏎
              </span>
              <button
                type="button"
                className="command-bar-send"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => void submitCommandBar()}
                disabled={!commandText.trim() || !consoleRunning}
                title="qwencode 터미널로 전송"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </section>

        <aside className={`event-panel right-panel ${rightPanelOpen ? "open" : "closed"}`}>
          <div className="right-panel-content" aria-hidden={!rightPanelOpen}>
          <div className="right-panel-header">
            <div className="section-title">
              <Bot size={18} />
              <h2>{rightTab === "builder" ? "프롬프트" : "타임라인"}</h2>
            </div>
            <div className="right-panel-controls">
              <div className="tab-row" role="tablist" aria-label="right panel tabs">
                <button
                  className={rightTab === "builder" ? "tab active" : "tab"}
                  onClick={() => setRightTab("builder")}
                  type="button"
                >
                  <MessageSquare size={15} />
                  확장하기
                </button>
                <button
                  className={rightTab === "chat" ? "tab active" : "tab"}
                  onClick={() => setRightTab("chat")}
                  type="button"
                >
                  <Bot size={15} />
                  타임라인
                </button>
              </div>
              <button className="icon-button ghost square" type="button" onClick={() => setRightPanelOpen(false)} title="패널 닫기">
                <PanelRightClose size={17} />
              </button>
            </div>
          </div>

          {rightTab === "builder" ? (
            <div className="builder-panel">
              <div className="builder-status">
                <span className={`inline-status ${builderRunning ? "active" : ""}`}>
                  {builderRunning ? <Loader2 className="spin" size={14} /> : <ListChecks size={14} />}
                  {builderRun?.status ?? "ready"}
                </span>
                <code>{builderRun?.id ?? "no run"}</code>
              </div>

              <div className="builder-chat">
                {builderMessages.length === 0 ? (
                  <div className="empty-state">
                    ultrawork 작업 프롬프트를 생성합니다.
                  </div>
                ) : (
                  builderMessages.map((message, index) => (
                    <article className={`builder-message ${message.role}`} key={`${message.role}-${index}`}>
                      <strong>{message.role === "user" ? "User" : "Kiwi Builder"}</strong>
                      <p>{message.content}</p>
                    </article>
                  ))
                )}
              </div>

              <form className="builder-composer" onSubmit={buildUltraworkPrompt}>
                <textarea
                  value={builderInput}
                  onChange={(event) => setBuilderInput(event.target.value)}
                  placeholder="예: 모바일 보험금 청구 화면에 직접 수령 여부 질문을 추가하는 ultrawork 지시문을 만들어줘."
                  disabled={!selectedProject || builderRunning}
                />
                <button className="icon-button primary" disabled={!builderInput.trim() || builderRunning || !selectedProject}>
                  {builderRunning ? <Loader2 className="spin" size={17} /> : <ClipboardCheck size={17} />}
                  확장하기
                </button>
              </form>

              {builderInterviewQuestions.length > 0 ? (
                <div className="interview-box">
                  <div className="interview-title">
                    <strong>interview_user</strong>
                    <span>필요한 정보를 선택하면 빌더가 이어서 최종 프롬프트를 조립합니다.</span>
                  </div>
                  {builderInterviewQuestions.map((question) => (
                    <article className="interview-question" key={question.id}>
                      <div className="interview-question-title">
                        <span>{question.header}</span>
                        <p>{question.question}</p>
                      </div>
                      <div className="interview-options">
                        {question.options.map((option) => (
                          <button
                            type="button"
                            className={builderInterviewAnswers[question.id] === option.label ? "selected" : ""}
                            key={`${question.id}-${option.label}`}
                            onClick={() =>
                              setBuilderInterviewAnswers((current) => ({ ...current, [question.id]: option.label }))
                            }
                          >
                            <strong>{option.label}</strong>
                            {option.description ? <small>{option.description}</small> : null}
                          </button>
                        ))}
                        {question.allow_other ? (
                          <button
                            type="button"
                            className={builderInterviewAnswers[question.id] === "__other__" ? "selected" : ""}
                            onClick={() =>
                              setBuilderInterviewAnswers((current) => ({ ...current, [question.id]: "__other__" }))
                            }
                          >
                            <strong>기타</strong>
                            <small>직접 입력합니다.</small>
                          </button>
                        ) : null}
                      </div>
                      {question.allow_other && builderInterviewAnswers[question.id] === "__other__" ? (
                        <textarea
                          className="interview-other"
                          value={builderInterviewOther[question.id] ?? ""}
                          onChange={(event) =>
                            setBuilderInterviewOther((current) => ({
                              ...current,
                              [question.id]: event.target.value
                            }))
                          }
                          placeholder="원하는 답변을 직접 입력하세요."
                        />
                      ) : null}
                    </article>
                  ))}
                  <button className="icon-button primary" type="button" onClick={submitInterviewAnswers} disabled={builderRunning}>
                    <Send size={16} />
                    답변 제출
                  </button>
                </div>
              ) : null}

              {builderQuestions.length > 0 ? (
                <div className="question-box">
                  <strong>확인 질문</strong>
                  {builderQuestions.map((question, index) => (
                    <p key={`${question}-${index}`}>{question}</p>
                  ))}
                </div>
              ) : null}

              <div className="builder-activity">
                <strong>Workflow Activity</strong>
                {builderEvents.length === 0 ? (
                  <small>Workflow 기록 표시</small>
                ) : (
                  builderEvents
                    .filter((event) => event.type !== "snapshot")
                    .slice(-8)
                    .reverse()
                    .map((event, index) => (
                      <article className="activity-item" key={`${event.timestamp ?? event.type}-${index}`}>
                        <div>
                          <span>{event.title ?? event.type}</span>
                          <small>{formatEventTime(event.timestamp)}</small>
                        </div>
                        <p>{summarizeBuilderEvent(event)}</p>
                      </article>
                    ))
                )}
              </div>

              {builtPrompt ? (
                <div className="prompt-preview">
                  <div className="prompt-preview-title">
                    <strong>Ultrawork Prompt</strong>
                    <div>
                      <button className="icon-button" type="button" onClick={copyBuiltPrompt} title="복사">
                        <Copy size={16} />
                      </button>
                      <button className="icon-button primary" type="button" onClick={sendBuiltPromptToConsole} disabled={!consoleRunning}>
                        <Send size={16} />
                        콘솔 전송
                      </button>
                    </div>
                  </div>
                  <textarea value={builtPrompt} readOnly />
                </div>
              ) : null}
            </div>
          ) : (
            <div className="chat-list" ref={chatListRef} onScroll={handleChatScroll}>
              {enrichedChatEvents.length === 0 ? (
                <div className="empty-state">Qwen chat JSONL에서 추출한 사용자, Kiwi, subagent 대화가 여기에 표시됩니다.</div>
              ) : (
                enrichedChatEvents.map((event) => (
                  <article
                    id={event.domId}
                    className={`chat-item ${chatEventClass(event)} ${
                      event.requestDomId && event.kind === "completion" ? "paired-response" : ""
                    } ${highlightedChatId === event.domId ? "highlight" : ""}`}
                    key={event.domId}
                  >
                    <div className="chat-meta">
                      <div>
                        <strong>{formatChatEventTitle(event)}</strong>
                        <span>{formatChatEventSubtitle(event)}</span>
                      </div>
                      <time>{formatEventTime(event.timestamp)}</time>
                    </div>
                    {event.relatedRequestTitle ? (
                      <div className="chat-related-note">
                        요청: {event.relatedRequestTitle}
                      </div>
                    ) : null}
                    {event.content ? <pre className="chat-content">{event.content}</pre> : null}
                    <div className="event-tags">
                      <span>{formatChatKind(event.kind)}</span>
                      <span>{event.agent ?? "unknown"}</span>
                      {event.tool_name ? <code>{event.tool_name}</code> : null}
                      {event.status ? <em>{event.status}</em> : null}
                      {event.tokens ? <em>{event.tokens.toLocaleString("ko-KR")} tokens</em> : null}
                      {event.resultDomId ? (
                        <button type="button" onClick={() => jumpToChatItem(event.resultDomId)}>
                          응답으로
                        </button>
                      ) : null}
                      {event.requestDomId ? (
                        <button type="button" onClick={() => jumpToChatItem(event.requestDomId)}>
                          요청으로
                        </button>
                      ) : null}
                    </div>
                    {event.error ? <small className="error-text">{event.error}</small> : null}
                  </article>
                ))
              )}
            </div>
          )}
          </div>
        </aside>
      </div>
    </main>
  );
}

async function api<T = Record<string, unknown>>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }
  return response.json();
}

function formatEventTime(value?: string) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString("ko-KR", { hour12: false });
}

function clampTerminalSize(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.max(min, Math.min(max, Math.floor(value)));
}

function normalizeTerminalSnapshot(text: string) {
  return text.replace(/\r\n/g, "\n").replace(/\n/g, "\r\n");
}

function summarizeToolInput(input: Record<string, unknown>) {
  const preferred = [
    "subagent_type",
    "description",
    "prompt",
    "file_path",
    "path",
    "directory",
    "command",
    "query",
    "pattern"
  ];
  const parts = preferred
    .filter((key) => input[key] !== undefined && input[key] !== null)
    .map((key) => `${key}: ${String(input[key]).slice(0, key === "prompt" ? 1600 : 900)}`);
  if (parts.length > 0) {
    return parts.join("\n");
  }
  return JSON.stringify(input, null, 2).slice(0, 1200);
}

function formatAgentName(event: TeamEvent) {
  return getToolString(event, "subagent_type") || event.agent_type || "main";
}

function chatEventClass(event: ChatEvent) {
  if (event.kind === "error" || event.status === "error" || event.error) {
    return "error";
  }
  if (event.kind === "user_message") {
    return "user";
  }
  if (event.kind === "assistant_message") {
    return normalizeAgentKey(event.agent || "") === "kiwi" ? "kiwi" : "message";
  }
  if (event.kind === "agent_request") {
    return "request";
  }
  if (event.kind === "agent_result") {
    return "result";
  }
  if (event.kind === "completion") {
    return "completion";
  }
  if (event.kind === "tool_request" || event.kind === "tool_call") {
    return "tool";
  }
  if (event.kind === "tool_result") {
    return "tool-result";
  }
  return "";
}

function formatChatEventTitle(event: ChatEvent) {
  const agent = event.agent ?? "unknown";
  if (event.kind === "user_message") {
    return "User";
  }
  if (event.kind === "assistant_message") {
    return `${agent} 메시지`;
  }
  if (event.kind === "agent_request") {
    return `${agent} 요청`;
  }
  if (event.kind === "agent_result") {
    return `${agent} 결과`;
  }
  if (event.kind === "completion") {
    return `${agent} 응답`;
  }
  if (event.kind === "tool_call") {
    return `${agent} · ${event.tool_name ?? "tool"}`;
  }
  if (event.kind === "error") {
    return `${agent} 오류`;
  }
  return event.title ?? event.kind ?? "chat";
}

function formatChatEventSubtitle(event: ChatEvent) {
  const parts = [event.title, event.model, event.record_type].filter(Boolean).map(String);
  return parts.join(" · ");
}

function formatChatKind(kind?: string) {
  switch (kind) {
    case "user_message":
      return "user";
    case "assistant_message":
      return "message";
    case "agent_request":
      return "agent request";
    case "agent_result":
      return "agent result";
    case "completion":
      return "completion";
    case "tool_call":
      return "tool";
    case "tool_request":
      return "tool request";
    case "tool_result":
      return "tool result";
    case "error":
      return "error";
    default:
      return kind ?? "chat";
  }
}

function normalizeAgentKey(value: string) {
  const text = value.trim();
  if (!text || text === "Qwen3.5-397B" || text.toLowerCase() === "kiwi") {
    return "kiwi";
  }
  const lower = text.toLowerCase();
  if (lower === "coder-next" || lower.startsWith("coder-next-")) {
    return "coder-35";
  }
  return lower;
}

function accumulateTokenTotals(current: Record<string, number>, event: ChatEvent) {
  const tokens = typeof event.tokens === "number" && Number.isFinite(event.tokens) ? event.tokens : 0;
  if (event.kind !== "completion" || tokens <= 0) {
    return current;
  }
  const agent = normalizeAgentKey(event.agent || "kiwi");
  return {
    ...current,
    [agent]: (current[agent] ?? 0) + tokens
  };
}

function chatDomId(event: ChatEvent, index: number) {
  const stable = event.uuid || event.response_id || event.prompt_id || event.timestamp || String(index);
  const kind = event.kind || event.record_type || "chat";
  return `chat-${kind}-${stable}-${index}`.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function formatTokens(tokens: number) {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(tokens >= 10_000_000 ? 0 : 1)}m`;
  }
  if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(tokens >= 10_000 ? 0 : 1)}k`;
  }
  return String(tokens);
}

function formatRuntimeCheckedAt(value?: string) {
  if (!value) {
    return "not checked";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });
}

function formatRuntimeStatus(status?: string) {
  switch (status) {
    case "ok":
      return "OK";
    case "missing":
      return "없음";
    case "failed":
      return "실패";
    default:
      return status ?? "미확인";
  }
}

function formatConsoleStatus(status: ConsoleStatus) {
  switch (status) {
    case "running":
      return "running";
    case "starting":
      return "starting";
    case "stopping":
      return "stopping";
    case "stopped":
      return "stopped";
    case "exited":
      return "exited";
    case "failed":
      return "failed";
    default:
      return "idle";
  }
}

function runtimeStatusClass(status?: string) {
  if (status === "ok") {
    return "ok";
  }
  if (status === "missing") {
    return "warn";
  }
  if (status === "failed") {
    return "error";
  }
  return "neutral";
}

function formatTeamEventTitle(event: TeamEvent) {
  const agent = formatAgentName(event);
  const tool = event.tool_name ?? "";
  if (event.event === "PreToolUse" && isAgentTool(tool)) {
    return `${agent} 요청`;
  }
  if (event.event === "PostToolUse" && isAgentTool(tool)) {
    return `${agent} 응답 완료`;
  }
  if (event.event === "PostToolUseFailure") {
    return `${agent} 도구 실패`;
  }
  if (event.event === "SubagentStart") {
    return `${agent} 시작`;
  }
  if (event.event === "SubagentStop") {
    return `${agent} 종료`;
  }
  if (event.event === "PermissionRequest") {
    return `${agent} 권한 요청`;
  }
  if (tool) {
    return `${agent} · ${tool}`;
  }
  return event.event ?? "event";
}

function formatTeamEventSubtitle(event: TeamEvent) {
  const description = getToolString(event, "description");
  if (description) {
    return description;
  }
  const target = getEventTarget(event);
  if (target) {
    return target;
  }
  if (event.reason) {
    return event.reason;
  }
  return event.cwd ?? "";
}

function formatTeamEventSummary(event: TeamEvent) {
  const tool = event.tool_name ?? "";
  const promptText = getToolString(event, "prompt");
  const command = getToolString(event, "command");
  const query = getToolString(event, "query") || getToolString(event, "pattern");
  const target = getEventTarget(event);

  if (event.event === "PreToolUse" && isAgentTool(tool)) {
    return promptText ? `작업 지시: ${compactText(promptText, 260)}` : "서브에이전트 작업을 시작합니다.";
  }
  if (event.event === "PostToolUse" && isAgentTool(tool)) {
    return "서브에이전트 실행이 완료되었습니다. 자세한 응답은 중앙 터미널의 Ultrawork 응답과 후속 이벤트를 확인하세요.";
  }
  if (event.event === "PostToolUseFailure") {
    return event.error ? compactText(event.error, 260) : "도구 실행이 실패했습니다.";
  }
  if (command) {
    return `명령: ${compactText(command, 260)}`;
  }
  if (query) {
    return `검색: ${compactText(query, 260)}`;
  }
  if (target) {
    return `대상: ${compactText(target, 260)}`;
  }
  return event.reason || event.raw || "세부 이벤트를 기록했습니다.";
}

function getEventTarget(event: TeamEvent) {
  return (
    getToolString(event, "file_path") ||
    getToolString(event, "path") ||
    getToolString(event, "directory") ||
    getToolString(event, "command") ||
    getToolString(event, "query") ||
    getToolString(event, "pattern")
  );
}

function getToolString(event: TeamEvent, key: string) {
  const value = event.tool_input?.[key];
  return value === undefined || value === null ? "" : String(value).trim();
}

function isAgentTool(toolName: string) {
  return ["agent", "task"].includes(toolName.trim().toLowerCase().replace(/[\s-]/g, "_"));
}

function compactText(value: string, max: number) {
  const text = value.replace(/\s+/g, " ").trim();
  return text.length <= max ? text : `${text.slice(0, max - 3)}...`;
}

function summarizeBuilderEvent(event: PromptBuilderEvent) {
  if (event.error) {
    return event.error;
  }
  if (event.type === "interview") {
    const count = event.interview_questions?.length ?? event.questions?.length ?? 0;
    return count > 0 ? `${count}개 확인 질문을 사용자 선택지로 표시` : event.message ?? "사용자 인터뷰 필요";
  }
  if (event.type === "intent" && event.intent) {
    const task = event.intent.task_summary ? String(event.intent.task_summary) : "";
    const mode = event.intent.mode ? String(event.intent.mode) : "";
    return [mode, task].filter(Boolean).join(" · ") || "의도 분석 완료";
  }
  if (event.type === "file_search") {
    const files = event.files_read?.length ? `, files=${event.files_read.length}` : "";
    return `matches=${event.result_count ?? 0}${files}`;
  }
  if (event.type === "prompt_lint" && event.lint) {
    const status = event.lint.passed ? "통과" : "보완 필요";
    const issues = event.lint.issues?.length ? ` · ${event.lint.issues.join(", ")}` : "";
    return `lint ${status} · score=${event.lint.score ?? "-"}${issues}`;
  }
  if (event.type === "prompt_evaluation" && event.evaluation) {
    const score = event.evaluation.score ?? event.lint?.score ?? "-";
    const issues = event.evaluation.issues?.length ? ` · ${event.evaluation.issues.join(", ")}` : "";
    return `평가/개선 완료 · score=${score}${issues}`;
  }
  if (event.questions?.length) {
    return event.questions.join(" / ");
  }
  if (event.prompt) {
    return `${event.prompt.length.toLocaleString("ko-KR")}자 프롬프트`;
  }
  if (event.queries?.length) {
    return event.queries.join(", ");
  }
  return event.message ?? event.step ?? event.type;
}
