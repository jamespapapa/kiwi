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
import { FormEvent, KeyboardEvent, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
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
      project_key?: string;
      project_label?: string;
      items?: RuntimeCheckItem[];
      requirements?: RuntimeRequirement[];
      actions?: RuntimeAction[];
      components?: {
        backend?: RuntimeComponent | null;
        frontend?: RuntimeComponent | null;
        playwright?: Record<string, unknown> | null;
      };
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
  cwd?: string | null;
  exit_code?: number | null;
};

type RuntimeRequirement = {
  id: string;
  name: string;
  expected?: string | null;
  actual?: string | null;
  status?: string;
  detail?: string | null;
};

type RuntimeAction = {
  id: string;
  label: string;
  cwd: string;
  command: string;
  terminal?: boolean;
  status?: string;
  detail?: string | null;
};

type RuntimeComponent = {
  type?: string;
  cwd?: string;
  package_manager?: string;
  node_required?: string;
  java_required?: string;
  vue?: string | null;
  vite?: string | null;
  modules?: string[];
  dcp_core?: {
    ok?: boolean;
    summary?: string;
    detail?: string;
  };
};

type ConsoleStatus = "idle" | "starting" | "running" | "stopping" | "stopped" | "exited" | "failed";
type WorkMode = "fast" | "ultrawork" | "superpowers";
type TaskSize = "xsmall" | "small" | "medium" | "large" | "xlarge";

type ConsoleSession = {
  id: string;
  project_id: string;
  project_name: string;
  root_path: string;
  command: string[];
  status: ConsoleStatus;
  mode: string;
  work_mode: WorkMode;
  work_mode_label: string;
  work_mode_prefix: string;
  task_size?: TaskSize | null;
  work_mode_locked: boolean;
  work_mode_activated: boolean;
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

type ProjectInfoStatus = {
  status?: "ready" | "stale" | "missing" | "invalid" | string;
  profile?: {
    key?: string;
    label?: string;
    execution_owner?: string;
  };
  required_reading?: string[];
  target_hints?: string[];
  domain_hints?: string[];
  action?: string;
  stale?: {
    is_stale?: boolean;
    changed?: Array<{ path?: string }>;
    missing?: Array<{ path?: string }>;
    added?: Array<{ path?: string }>;
  };
};

type PromptBuilderRun = {
  id: string;
  project_id: string;
  project_name: string;
  work_mode?: WorkMode;
  work_mode_label?: string;
  status: "running" | "succeeded" | "failed";
  created_at: string;
  completed_at?: string | null;
  message: string;
  assistant_message: string;
  questions: string[];
  interview_questions?: InterviewQuestion[];
  final_prompt: string;
  task_size?: TaskSize | null;
  task_size_reason?: string;
  task_size_source?: string;
  selected_task_size?: TaskSize | null;
  recommended_task_size?: TaskSize | null;
  recommended_task_size_reason?: string;
  ultrawork_mode?: string;
  prompt_lint?: PromptLint;
  prompt_evaluation?: PromptEvaluation;
  project_info?: ProjectInfoStatus;
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
  project_info?: ProjectInfoStatus;
  intent?: Record<string, unknown>;
  policy?: Record<string, unknown>;
  queries?: string[];
  result_count?: number;
  files_read?: string[];
  results?: unknown;
};

type ModelTooltip = {
  text: string;
  top: number;
  left: number;
  anchor: {
    top: number;
    right: number;
    bottom: number;
    left: number;
    width: number;
    height: number;
  };
};

type WorkModeOption = {
  key: WorkMode;
  label: string;
  prefix: string;
  description: string;
};

type TaskSizeOption = {
  key: TaskSize;
  label: string;
  mode: string;
  team: string;
  operation: string;
};

type ConsoleSendMeta = {
  task_size?: TaskSize;
  task_size_reason?: string;
};

const workModeOptions: WorkModeOption[] = [
  {
    key: "fast",
    label: "FAST",
    prefix: "lightwork",
    description: "Kiwi가 단독으로 계획, 직접 수정, focused verification까지 수행합니다. 티셔츠 사이징과 subagent 위임은 없습니다."
  },
  {
    key: "ultrawork",
    label: "ultrawork",
    prefix: "ultrawork",
    description: "사용자가 선택한 티셔츠 사이즈를 기준으로 explorer/planner/architect/coder/reviewer 등 Qwen agent 팀을 조율합니다."
  },
  {
    key: "superpowers",
    label: "superpowers",
    prefix: "superpowers",
    description: "superpowers skill library를 먼저 로드해 impact map과 검증 계약을 강화한 뒤 필요한 경우 agent 팀으로 확장합니다."
  }
];

const taskSizeOptions: TaskSizeOption[] = [
  {
    key: "xsmall",
    label: "XS",
    mode: "solo",
    team: "Kiwi 단독",
    operation: "subagent 없이 현재 파일을 직접 읽고 최소 수정과 focused verification만 수행합니다."
  },
  {
    key: "small",
    label: "S",
    mode: "light",
    team: "explorer-35, 구현 agent, 조건부 reviewer-35",
    operation: "짧은 탐색 뒤 한 번의 좁은 구현 위임을 기본으로 하고 planner/architect는 생략합니다."
  },
  {
    key: "medium",
    label: "M",
    mode: "balanced",
    team: "explorer-35, 구현 agent, architect-35, reviewer-35",
    operation: "한두 개 repair slice를 구현하고 공유/API/store 위험이 보이면 architect-35가 짧게 검토합니다."
  },
  {
    key: "large",
    label: "L",
    mode: "full",
    team: "planner-35, architect-35, explorer-35, 구현 agent, reviewer-35, debugger-35, tester-35",
    operation: "요구사항과 영향도를 먼저 나눈 뒤 여러 repair slice, 리뷰, 디버그, 검증 루프로 진행합니다."
  },
  {
    key: "xlarge",
    label: "XL",
    mode: "full-phased",
    team: "planner-35, architect-35, explorer-35, 구현 agent, reviewer-35, debugger-35, tester-35",
    operation: "phase별 계획, phase별 리뷰, 최종 통합 리뷰를 분리하고 파일 ownership이 분리될 때만 병렬화합니다."
  }
];

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
  const [selectedTaskSize, setSelectedTaskSize] = useState<TaskSize>("medium");
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [commandText, setCommandText] = useState("");
  const [commandBarFocused, setCommandBarFocused] = useState(false);
  const [workMode, setWorkMode] = useState<WorkMode>("ultrawork");
  const [workModeLocked, setWorkModeLocked] = useState(false);
  const terminalHostRef = useRef<HTMLDivElement | null>(null);
  const xtermRef = useRef<XTermType | null>(null);
  const fitAddonRef = useRef<FitAddonType | null>(null);
  const inputSessionRef = useRef<string | null>(null);
  const builderSourceRef = useRef<EventSource | null>(null);
  const commandTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const workModeActivatedRef = useRef(false);
  const submitAfterCompositionRef = useRef(false);
  const chatListRef = useRef<HTMLDivElement | null>(null);
  const chatPinnedToBottomRef = useRef(true);
  const pendingFitFrameRef = useRef<number | null>(null);
  const terminalLogRef = useRef("");
  const lastSnapshotSessionRef = useRef<string | null>(null);
  const lastResizeSentRef = useRef<{ sessionId: string; cols: number; rows: number } | null>(null);
  const [highlightedChatId, setHighlightedChatId] = useState<string | null>(null);
  const [modelTooltip, setModelTooltip] = useState<ModelTooltip | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  const consoleStatus: ConsoleStatus = consoleSession?.status ?? "idle";
  const consoleRunning = consoleStatus === "running" || consoleStatus === "starting";
  const builderWorkMode = consoleSession?.work_mode ?? workMode;
  const showTaskSizeSelector = builderWorkMode !== "fast";
  const selectedTaskSizeOption = taskSizeOptions.find((item) => item.key === selectedTaskSize) ?? taskSizeOptions[2];

  const showModelTooltip = useCallback((text: string, target: HTMLElement) => {
    const rect = target.getBoundingClientRect();
    setModelTooltip({
      text,
      top: rect.top + rect.height / 2,
      left: rect.right + 10,
      anchor: {
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        left: rect.left,
        width: rect.width,
        height: rect.height
      }
    });
  }, []);

  const hideModelTooltip = useCallback(() => {
    setModelTooltip(null);
  }, []);

  useLayoutEffect(() => {
    if (!modelTooltip || !tooltipRef.current) {
      return;
    }
    const tooltip = tooltipRef.current;
    const tooltipRect = tooltip.getBoundingClientRect();
    const anchor = modelTooltip.anchor;
    const gap = 10;
    const margin = 12;
    let left = anchor.right + gap;
    if (left + tooltipRect.width + margin > window.innerWidth) {
      left = anchor.left - tooltipRect.width - gap;
    }
    if (left < margin) {
      left = anchor.left + anchor.width / 2 - tooltipRect.width / 2;
    }
    left = Math.min(Math.max(margin, left), Math.max(margin, window.innerWidth - tooltipRect.width - margin));

    let top = anchor.top + anchor.height / 2 - tooltipRect.height / 2;
    top = Math.min(Math.max(margin, top), Math.max(margin, window.innerHeight - tooltipRect.height - margin));

    if (Math.abs(modelTooltip.left - left) > 0.5 || Math.abs(modelTooltip.top - top) > 0.5) {
      setModelTooltip((current) => (current ? { ...current, top, left } : current));
    }
  }, [modelTooltip]);

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
        role: "dcp-front-developer",
        detail: "DCP Front",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "dcp-front 전용 Vue 2 개발자입니다. route, view, Vuex DataStore, Axios, CSS/DOM 변경을 맡습니다."
      },
      {
        role: "dcp-backend-developer",
        detail: "DCP Back",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "dcp-services 전용 Java/Spring 개발자입니다. controller, service, Redis, EAI, mapper 변경을 맡습니다."
      },
      {
        role: "drt-front-developer",
        detail: "DRT Front",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "DRT 고객용 Vue 3/Vite 개발자입니다. route, view, Pinia store, DrtHttpClient, service 변경을 맡습니다."
      },
      {
        role: "drt-backend-developer",
        detail: "DRT API",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "DRT API 전용 Spring Boot 개발자입니다. controller, service, mapper XML, profile config 변경을 맡습니다."
      },
      {
        role: "drt-cms-front-developer",
        detail: "CMS Front",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "DRT CMS 관리자 프론트 개발자입니다. Quasar route, view, service/model, grid, store 변경을 맡습니다."
      },
      {
        role: "drt-cms-backend-developer",
        detail: "CMS Back",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "DRT CMS 관리자 백엔드 개발자입니다. REST resource, service, repository, MyBatis XML, security/batch 변경을 맡습니다."
      },
      {
        role: "explorer-35",
        detail: "Explore",
        model: settings.orchestrator_model,
        tone: "orchestrator",
        description: "Qwen3.5-397B를 쓰는 read-only 탐색 역할입니다. 독립 질문은 최대 5개까지 병렬 호출할 수 있습니다."
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
    let cols = clampTerminalSize(proposed.cols, TERMINAL_MIN_COLS, TERMINAL_MAX_COLS);
    let rows = clampTerminalSize(proposed.rows, TERMINAL_MIN_ROWS, TERMINAL_MAX_ROWS);
    for (let attempt = 0; attempt < 4; attempt += 1) {
      if (cols !== terminal.cols || rows !== terminal.rows) {
        terminal.resize(cols, rows);
      }
      const overflow = measureTerminalOverflow(host, terminal.cols, terminal.rows);
      if (!overflow || (overflow.x <= 0 && overflow.y <= 0)) {
        break;
      }
      const nextCols =
        overflow.x > 0 && overflow.cellWidth > 0
          ? clampTerminalSize(cols - Math.max(1, Math.ceil((overflow.x + 1) / overflow.cellWidth)), TERMINAL_MIN_COLS, TERMINAL_MAX_COLS)
          : cols;
      const nextRows =
        overflow.y > 0 && overflow.cellHeight > 0
          ? clampTerminalSize(rows - Math.max(1, Math.ceil((overflow.y + 1) / overflow.cellHeight)), TERMINAL_MIN_ROWS, TERMINAL_MAX_ROWS)
          : rows;
      if (nextCols === cols && nextRows === rows) {
        break;
      }
      cols = nextCols;
      rows = nextRows;
    }
    if (cols !== terminal.cols || rows !== terminal.rows) {
      terminal.resize(cols, rows);
    }
  }, []);

  const scheduleTerminalFit = useCallback(() => {
    if (pendingFitFrameRef.current !== null) {
      window.cancelAnimationFrame(pendingFitFrameRef.current);
    }
    pendingFitFrameRef.current = window.requestAnimationFrame(() => {
      pendingFitFrameRef.current = null;
      fitTerminalSafely();
    });
  }, [fitTerminalSafely]);

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
        syncWorkModeFromSession(payload.session);
        const snapshotSessionId = payload.session?.id ?? null;
        const snapshotText = payload.terminal || "콘솔이 연결되었습니다.\r\n";
        replaceTerminalLog(payload.terminal ?? "");
        if (lastSnapshotSessionRef.current !== snapshotSessionId) {
          lastSnapshotSessionRef.current = snapshotSessionId;
          resetTerminal(snapshotText);
          scheduleTerminalFit();
        }
        setTeamEvents(payload.team_events ?? []);
        setChatEvents(payload.chat_events ?? []);
        setAgentTokenTotals(payload.session?.token_usage ?? {});
      }
      if (payload.type === "terminal") {
        const chunk = payload.data ?? "";
        appendTerminalLog(chunk);
        xtermRef.current?.write(chunk);
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
        syncWorkModeFromSession(payload.session);
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
          rows: TERMINAL_MIN_ROWS,
          convertEol: true,
          cursorBlink: false,
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
          windowsPty: {
            backend: "winpty"
          }
        });
        const fitAddon = new FitAddon();
        terminal.loadAddon(fitAddon);
        terminal.open(terminalHostRef.current);
        xtermRef.current = terminal;
        fitAddonRef.current = fitAddon;
        fitTerminalSafely();
        scheduleTerminalFit();
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
          if (event.type === "keydown" && event.key === "Enter" && event.shiftKey) {
            event.preventDefault();
            const sessionId = inputSessionRef.current;
            if (!sessionId) {
              setNotice("먼저 콘솔을 시작하세요.");
              return false;
            }
            void api(`/api/ultrawork/sessions/${sessionId}/input`, {
              method: "POST",
              body: JSON.stringify({ text: "\n", submit: false, bracketed_paste: true })
            }).catch(showError);
            return false;
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
        if (terminalHostRef.current) {
          resizeObserver = new ResizeObserver(() => scheduleTerminalFit());
          resizeObserver.observe(terminalHostRef.current);
        }
      }
    );

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (pendingFitFrameRef.current !== null) {
        window.cancelAnimationFrame(pendingFitFrameRef.current);
        pendingFitFrameRef.current = null;
      }
      lastSnapshotSessionRef.current = null;
      terminal?.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, [fitTerminalSafely, scheduleTerminalFit]);

  useEffect(() => {
    inputSessionRef.current = consoleRunning && consoleSession ? consoleSession.id : null;
    if (!consoleRunning || !consoleSession) {
      lastResizeSentRef.current = null;
    }
  }, [consoleRunning, consoleSession?.id]);

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

  async function refreshRuntimeChecks() {
    if (!selectedProject) {
      setNotice("먼저 프로젝트를 선택하거나 초기화하세요.");
      return;
    }
    setBusy(true);
    try {
      const data = await api<{ project: Project; runtime_checks: Project["summary"]["runtime_checks"] }>(
        `/api/projects/${selectedProject.id}/runtime/check`,
        { method: "POST" }
      );
      setSelectedProject(data.project);
      setProjects((current) => current.map((item) => (item.id === data.project.id ? data.project : item)));
      setNotice("프로젝트 런타임 체크를 갱신했습니다.");
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  async function runRuntimeAction(action: RuntimeAction) {
    if (!selectedProject) {
      setNotice("먼저 프로젝트를 선택하거나 초기화하세요.");
      return;
    }
    if (action.status === "unavailable") {
      setNotice(action.detail || `${action.label} 실행 조건이 충족되지 않았습니다.`);
      return;
    }
    try {
      await api(`/api/projects/${selectedProject.id}/runtime/actions/${encodeURIComponent(action.id)}`, {
        method: "POST"
      });
      setNotice(`새 터미널에서 ${action.label} 실행을 시작했습니다.`);
    } catch (error) {
      showError(error);
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
          work_mode: workMode,
          ...(workMode !== "fast"
            ? {
                task_size: selectedTaskSize,
                task_size_reason: `사용자가 ${selectedTaskSize}를 선택했다.`
              }
            : {}),
          cols,
          rows
        })
      });
      setConsoleSession(data.session);
      setWorkMode(data.session.work_mode);
      if (data.session.task_size) {
        setSelectedTaskSize(data.session.task_size);
      }
      setWorkModeLocked(data.session.work_mode_locked);
      workModeActivatedRef.current = data.session.work_mode_activated;
      replaceTerminalLog("");
      setTeamEvents([]);
      setChatEvents([]);
      setAgentTokenTotals({});
      setNotice(`Console 시작: ${data.session.work_mode_label} · ${data.session.mode}`);
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

  async function sendQuickPrompt(text: string, meta: ConsoleSendMeta = {}) {
    if (!consoleSession) {
      setNotice("먼저 콘솔을 시작하세요.");
      return;
    }
    const prepared = prepareConsoleText(text);
    try {
      await sendConsoleText(prepared.text, hasConsoleMeta(meta) ? meta : selectedTaskSizeConsoleMeta());
      lockWorkMode(prepared.lock);
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
      await sendConsoleText(prepared.text, selectedTaskSizeConsoleMeta());
      lockWorkMode(prepared.lock);
      setCommandText("");
      setCommandBarFocused(false);
      commandTextareaRef.current?.blur();
    } catch (error) {
      showError(error);
    }
  }

  async function sendConsoleText(text: string, meta: ConsoleSendMeta = {}) {
    if (!consoleSession) {
      setNotice("먼저 콘솔을 시작하세요.");
      return;
    }
    await api(`/api/ultrawork/sessions/${consoleSession.id}/input`, {
      method: "POST",
      body: JSON.stringify({ text, submit: true, bracketed_paste: true, ...meta })
    });
    xtermRef.current?.focus();
  }

  function selectedTaskSizeConsoleMeta(): ConsoleSendMeta {
    const mode = consoleSession?.work_mode ?? workMode;
    if (mode === "fast") {
      return {};
    }
    return {
      task_size: selectedTaskSize,
      task_size_reason: `사용자가 ${selectedTaskSize}를 선택했다.`
    };
  }

  function prepareConsoleText(text: string): { text: string; lock: boolean } {
    const mode = consoleSession?.work_mode ?? workMode;
    if (workModeActivatedRef.current) {
      return { text, lock: false };
    }
    const alreadyPrefixed = textHasAnyWorkModePrefix(text);
    return {
      text: alreadyPrefixed ? text : `${workModePrefix(mode, selectedTaskSize)}\n\n${text}`,
      lock: true
    };
  }

  function lockWorkMode(shouldLock: boolean) {
    if (!shouldLock) {
      return;
    }
    workModeActivatedRef.current = true;
    setWorkModeLocked(true);
  }

  function selectWorkMode(mode: WorkMode) {
    if (workModeLocked || consoleRunning) {
      return;
    }
    setWorkMode(mode);
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
      const requestWorkMode = consoleSession?.work_mode ?? workMode;
      const data = await api<{ run: PromptBuilderRun }>("/api/prompt-builder/runs", {
        method: "POST",
        body: JSON.stringify({
          project_id: selectedProject.id,
          message: text,
          work_mode: requestWorkMode,
          ...(requestWorkMode !== "fast" ? { task_size: selectedTaskSize } : {}),
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
          appendBuilderMessage(
            "assistant",
            payload.message || `${workModeLabel(consoleSession?.work_mode ?? workMode)} 지시 프롬프트를 만들었습니다.`
          );
        }
        if (payload.type === "project_info" && payload.project_info) {
          setBuilderRunProjectInfo(payload.project_info);
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
        "fast_policy",
        "task_size",
        "project_info",
        "file_search",
        "kk_docs_search",
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
    const label = workModeLabel(consoleSession?.work_mode ?? workMode);
    const rerunMessage =
      `사용자 인터뷰 답변입니다. 이 답변을 반영해서 최초 요청에 대한 최종 ${label} 프롬프트를 완성해라.\n\n` +
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
    if (run.work_mode !== "fast" && run.task_size) {
      setSelectedTaskSize(run.task_size);
    }
    if (run.final_prompt) {
      setBuiltPrompt(run.final_prompt);
      setBuilderInterviewQuestions([]);
    }
    if (run.status !== "running") {
      setBuilderRunning(false);
    }
  }

  function setBuilderRunProjectInfo(projectInfo?: ProjectInfoStatus) {
    if (!projectInfo) {
      return;
    }
    setBuilderRun((current) => (current ? { ...current, project_info: projectInfo } : current));
  }

  function syncWorkModeFromSession(session?: ConsoleSession | null) {
    if (!session?.work_mode) {
      return;
    }
    setWorkMode(session.work_mode);
    setWorkModeLocked(Boolean(session.work_mode_locked));
    workModeActivatedRef.current = Boolean(session.work_mode_activated);
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
    await sendQuickPrompt(builtPrompt, promptBuilderConsoleMeta(builderRun));
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
    setWorkModeLocked(false);
    workModeActivatedRef.current = false;
    lastSnapshotSessionRef.current = null;
    replaceTerminalLog("");
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

  function replaceTerminalLog(text: string) {
    terminalLogRef.current = text.slice(-240000);
  }

  function appendTerminalLog(chunk: string) {
    if (!chunk) {
      return;
    }
    terminalLogRef.current = `${terminalLogRef.current}${chunk}`.slice(-240000);
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
    <main className="shell" data-kiwi-ui-build="xterm-fit-v4-port-guard">
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

          <section className={`ultrawork-panel work-mode-panel mode-${workMode} ${workModeLocked ? "locked" : ""}`}>
            <div className="ultrawork-mode-row">
              <div className="ultrawork-mode-left">
                <div className="section-title">
                  <Flame size={18} />
                  <h2>work mode</h2>
                </div>
                <div className="work-mode-picker" role="radiogroup" aria-label="KIWI work mode">
                  {workModeOptions.map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      className={option.key === workMode ? "active" : ""}
                      role="radio"
                      aria-checked={option.key === workMode}
                      disabled={workModeLocked || consoleRunning}
                      onClick={() => selectWorkMode(option.key)}
                      title={`${option.label} · ${option.prefix}`}
                    >
                      <strong>{option.label}</strong>
                      <span
                        className="work-mode-info"
                        aria-hidden
                        onMouseEnter={(event) => showModelTooltip(option.description, event.currentTarget)}
                        onMouseLeave={hideModelTooltip}
                      >
                        <Info size={13} />
                      </span>
                    </button>
                  ))}
                </div>
                <div className="work-mode-state">
                  <code>{consoleSession?.work_mode_prefix ?? workModePrefix(workMode, selectedTaskSize)}</code>
                  <span>{workModeLocked ? "locked" : "ready"}</span>
                </div>
                {showTaskSizeSelector ? (
                  <div className="task-size-selector work-mode-task-size" aria-label="ultrawork 티셔츠 사이즈">
                    <div className="task-size-selector-header">
                      <strong>티셔츠 사이즈</strong>
                      <span>
                        선택 <code>{selectedTaskSize}</code> · {selectedTaskSizeOption.mode}
                      </span>
                    </div>
                    <div className="task-size-options" role="radiogroup" aria-label="ultrawork/superpowers size selector">
                      {taskSizeOptions.map((option) => {
                        const tooltip = `${option.key} / ${option.mode}\nagent 팀 구성: ${option.team}\n운영 방식: ${option.operation}`;
                        return (
                          <div className={`task-size-option ${option.key === selectedTaskSize ? "selected" : ""}`} key={option.key}>
                            <button
                              type="button"
                              className="task-size-choice"
                              role="radio"
                              aria-checked={option.key === selectedTaskSize}
                              disabled={builderRunning || consoleRunning || workModeLocked}
                              onClick={() => setSelectedTaskSize(option.key)}
                            >
                              <strong>{option.label}</strong>
                              <small>{option.key}</small>
                            </button>
                            <button
                              type="button"
                              className="task-size-info"
                              title={`${option.key} agent 팀 구성과 운영 방식`}
                              aria-label={`${option.key} agent 팀 구성과 운영 방식`}
                              onMouseEnter={(event) => showModelTooltip(tooltip, event.currentTarget)}
                              onMouseLeave={hideModelTooltip}
                              onFocus={(event) => showModelTooltip(tooltip, event.currentTarget)}
                              onBlur={hideModelTooltip}
                            >
                              <Info size={13} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
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
                    <strong>런타임 체크 · {selectedProject.summary.runtime_checks.project_key ?? "generic"}</strong>
                    <span>{formatRuntimeCheckedAt(selectedProject.summary.runtime_checks.checked_at)}</span>
                    <button className="mini-action-button" onClick={refreshRuntimeChecks} disabled={busy}>
                      재검사
                    </button>
                  </div>
                  <div className="runtime-check-list">
                    {(selectedProject.summary.runtime_checks.items ?? []).map((item) => (
                      <div className="runtime-check-row" key={item.name}>
                        <strong>{item.name}</strong>
                        <code title={runtimeCheckTitle(item)}>{item.version ?? item.detail ?? "not found"}</code>
                        <span className={`runtime-status ${runtimeStatusClass(item.status)}`}>{formatRuntimeStatus(item.status)}</span>
                      </div>
                    ))}
                  </div>
                  {(selectedProject.summary.runtime_checks.requirements ?? []).length > 0 ? (
                    <>
                      <div className="project-runtime-heading compact">
                        <strong>프로젝트 요구사항</strong>
                      </div>
                      <div className="runtime-check-list">
                        {(selectedProject.summary.runtime_checks.requirements ?? []).map((item) => (
                          <div className="runtime-check-row requirement" key={item.id}>
                            <strong>{item.name}</strong>
                            <code title={item.detail ?? ""}>
                              {item.expected ?? ""}
                              {item.actual ? ` · ${item.actual}` : ""}
                            </code>
                            <span className={`runtime-status ${runtimeStatusClass(item.status)}`}>{formatRuntimeStatus(item.status)}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : null}
                  {(selectedProject.summary.runtime_checks.actions ?? []).length > 0 ? (
                    <>
                      <div className="project-runtime-heading compact">
                        <strong>실행 액션</strong>
                      </div>
                      <div className="runtime-action-list">
                        {(selectedProject.summary.runtime_checks.actions ?? []).map((action) => (
                          <button
                            key={action.id}
                            className="runtime-action-button"
                            onClick={() => void runRuntimeAction(action)}
                            disabled={action.status === "unavailable"}
                            title={`${action.command}\n${action.cwd}\n${action.detail ?? ""}`}
                          >
                            <span>{action.label}</span>
                            <code>{action.command}</code>
                          </button>
                        ))}
                      </div>
                    </>
                  ) : null}
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
              <ClipboardCheck size={18} />
              <h2>런타임 정보</h2>
            </summary>
            <div className="runtime-grid compact-models collapsible-body">
              <div className="model-role-table" aria-label="KIWI runtime information">
                <div className="model-role-row runtime-command-row">
                  <span className="model-role-name">
                    <strong>qwencode</strong>
                  </span>
                  <code>{settings.qwencode_command}</code>
                </div>
                <div className="model-role-row runtime-command-row">
                  <span className="model-role-name">
                    <strong>kk-docs MCP</strong>
                  </span>
                  <code>{settings.kk_docs_mcp_enabled ? settings.kk_docs_mcp_url : "disabled"}</code>
                </div>
                <div className="model-role-row runtime-command-row">
                  <span className="model-role-name">
                    <strong>kk-code-analysis MCP</strong>
                  </span>
                  <code>{settings.kk_code_analysis_mcp_enabled ? settings.kk_code_analysis_mcp_url : "disabled"}</code>
                </div>
              </div>
            </div>
          </details>

          <details className="runtime-panel collapsible-panel" open>
            <summary className="section-title">
              <BrainCircuit size={18} />
              <h2>에이전트 정보</h2>
            </summary>
            <div className="runtime-grid compact-models collapsible-body">
              <div className="model-role-table" aria-label="Qwen runtime model roles">
                {modelRoles.map((item) => (
                  <div className="model-role-row" key={item.role}>
                    <span className="model-role-name">
                      <strong>{item.role}</strong>
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

          </div>
        </section>

        {modelTooltip && typeof document !== "undefined"
          ? createPortal(
              <div
                ref={tooltipRef}
                className="agent-info-tooltip"
                style={{ top: modelTooltip.top, left: modelTooltip.left }}
                role="tooltip"
              >
                {modelTooltip.text}
              </div>,
              document.body
            )
          : null}

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
                  {consoleSession?.work_mode_label ? ` · ${consoleSession.work_mode_label}` : ""}
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
                  프롬프트
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
                    {workModeLabel(consoleSession?.work_mode ?? workMode)} 작업 프롬프트를 생성합니다.
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
                  placeholder={`예: 모바일 보험금 청구 화면에 직접 수령 여부 질문을 추가하는 ${workModeLabel(consoleSession?.work_mode ?? workMode)} 지시문을 만들어줘.`}
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
                    <strong>{workModeLabel(builderRun?.work_mode ?? consoleSession?.work_mode ?? workMode)} Prompt</strong>
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

function measureTerminalOverflow(host: HTMLElement, cols: number, rows: number) {
  const viewport = host.querySelector<HTMLElement>(".xterm-viewport");
  const screen = host.querySelector<HTMLElement>(".xterm-screen");
  const rowLayer = host.querySelector<HTMLElement>(".xterm-rows");
  if (!viewport || !screen) {
    return null;
  }
  const viewportRect = viewport.getBoundingClientRect();
  const screenRect = screen.getBoundingClientRect();
  const rowLayerRect = rowLayer?.getBoundingClientRect();
  const renderedWidth = Math.max(screenRect.width, rowLayerRect?.width ?? 0);
  return {
    x: Math.max(0, renderedWidth - viewportRect.width),
    y: Math.max(0, screenRect.height - viewportRect.height),
    cellWidth: screenRect.width / Math.max(cols, 1),
    cellHeight: screenRect.height / Math.max(rows, 1)
  };
}

function normalizeTerminalSnapshot(text: string) {
  return text.replace(/\r\n/g, "\n").replace(/\n/g, "\r\n");
}

function workModePrefix(mode: WorkMode, taskSize: TaskSize = "medium") {
  const base = workModeOptions.find((item) => item.key === mode)?.prefix ?? "ultrawork";
  if (mode === "ultrawork" || mode === "superpowers") {
    return `${base}_${taskSize}`;
  }
  return base;
}

function workModeLabel(mode: WorkMode) {
  return workModeOptions.find((item) => item.key === mode)?.label ?? "ultrawork";
}

function promptBuilderConsoleMeta(run: PromptBuilderRun | null): ConsoleSendMeta {
  if (!run?.task_size || run.work_mode === "fast") {
    return {};
  }
  return {
    task_size: run.task_size,
    task_size_reason: run.task_size_reason
  };
}

function hasConsoleMeta(meta: ConsoleSendMeta) {
  return Boolean(meta.task_size);
}

function workModeAliases(): Record<WorkMode, string[]> {
  return {
    fast: ["lightwork", "fast", "lw"],
    ultrawork: ["ultrawork", "ulw"],
    superpowers: ["superpowers", "spw"]
  };
}

function textHasAnyWorkModePrefix(text: string) {
  const firstLine = text.replace(/^\uFEFF/, "").split(/\r?\n/, 1)[0]?.trim().toLowerCase() ?? "";
  if (!firstLine) {
    return false;
  }
  return Object.values(workModeAliases()).some(
    (aliases) =>
      aliases.includes(firstLine) ||
      aliases.some(
        (alias) =>
          ["ultrawork", "ulw", "superpowers", "spw"].includes(alias) &&
          Boolean(firstLine.match(new RegExp(`^${alias}_(xsmall|small|medium|large|xlarge)$`)))
      )
  );
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
    case "ready":
      return "준비";
    case "warn":
      return "주의";
    case "error":
      return "오류";
    case "unavailable":
      return "불가";
    case "missing":
      return "없음";
    case "failed":
      return "실패";
    default:
      return status ?? "미확인";
  }
}

function runtimeCheckTitle(item: RuntimeCheckItem) {
  return [
    item.command ? `command: ${item.command}` : "",
    item.path ? `path: ${item.path}` : "",
    item.cwd ? `cwd: ${item.cwd}` : "",
    item.exit_code !== undefined && item.exit_code !== null ? `exit: ${item.exit_code}` : "",
    item.detail ? `detail: ${item.detail}` : ""
  ]
    .filter(Boolean)
    .join("\n");
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
  if (status === "ok" || status === "ready") {
    return "ok";
  }
  if (status === "missing" || status === "warn" || status === "unavailable") {
    return "warn";
  }
  if (status === "failed" || status === "error") {
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
  if (event.type === "task_size" && event.policy) {
    const selected = event.policy.task_size ? String(event.policy.task_size) : "";
    const summary = selected ? `사용자 선택=${selected}` : "";
    return summary || event.message || "티셔츠 사이징";
  }
  if (event.type === "project_info" && event.project_info) {
    return formatProjectInfoEventSummary(event.project_info);
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

function formatProjectInfoEventSummary(projectInfo: ProjectInfoStatus) {
  const status = projectInfo.status ?? "missing";
  const profile = projectInfo.profile?.key ?? "unknown";
  const required = projectInfo.required_reading?.length ?? 0;
  const hints = (projectInfo.target_hints?.length ?? 0) + (projectInfo.domain_hints?.length ?? 0);
  if (status === "ready") {
    return `Project Info ready · profile=${profile} · required=${required} · hints=${hints}`;
  }
  if (status === "stale") {
    const changed = projectInfo.stale?.changed?.length ?? 0;
    const missing = projectInfo.stale?.missing?.length ?? 0;
    const added = projectInfo.stale?.added?.length ?? 0;
    return `Project Info stale · profile=${profile} · changed=${changed} · missing=${missing} · added=${added}`;
  }
  if (status === "invalid") {
    return `Project Info invalid · ${projectInfo.action ?? "refresh required"}`;
  }
  return `Project Info missing · ${projectInfo.action ?? "refresh required"}`;
}
