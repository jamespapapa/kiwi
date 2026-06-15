# FAST Benchmark Tasks

These deterministic benchmark tasks validate FAST/lightwork prompt quality without calling Qwen3.5.

The fenced JSON below is the canonical task set consumed by `scripts/run-fast-benchmarks.py`.

```json
{
  "schema_version": "fast-benchmark-tasks.v1",
  "tasks": [
    {
      "id": "front_claim_intro_text",
      "profile": "dcp-front",
      "user_prompt": "보험금 청구 인트로 화면의 안내 문구 한 줄을 현재 화면 파일 기준으로 수정하고 확인해줘.",
      "required_project_info_artifacts": ["project-summary.md", "architecture-map.md", "entrypoints.md", "key-flows.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["route: claim intro route path", "view: ClaimIntro Vue screen", "component: shared notice component", "Vuex: claim state module", "DataStore: claim draft carrier", "Axios: claim save client", "CSS: scoped text layout", "Playwright: claim intro smoke check"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to the requested text", "Report evidence from route view component Vuex DataStore Axios CSS Playwright surfaces"],
      "stop_question_conditions": ["stop and ask if route ownership is unclear", "stop and ask if DataStore carrier is ambiguous", "stop and ask if focused verification cannot prove the text change"],
      "verification_expectation": ["focused verification: run existing type or lint command when available", "focused verification: record Playwright or manual DOM text check"]
    },
    {
      "id": "front_button_css_containment",
      "profile": "dcp-front",
      "user_prompt": "청구 화면 버튼 hover 효과가 주변 레이아웃을 밀지 않도록 CSS 범위를 좁혀줘.",
      "required_project_info_artifacts": ["project-summary.md", "architecture-map.md", "module-responsibility-map.md", "entrypoints.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["route: claim button route", "view: button owner Vue view", "component: reusable button component", "Vuex: no state mutation expected", "DataStore: no carrier change expected", "Axios: no API change expected", "CSS: containing block and overflow", "Playwright: screenshot path or DOM metric check"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff to CSS selector and containment only", "Report evidence from route view component Vuex DataStore Axios CSS Playwright surfaces"],
      "stop_question_conditions": ["stop and ask if the target button owner is unclear", "stop and ask if CSS change could affect sibling controls", "stop and ask if focused verification cannot confirm layout containment"],
      "verification_expectation": ["focused verification: inspect DOM class and CSS metric evidence", "focused verification: run narrow UI or lint check when available"]
    },
    {
      "id": "front_datastore_payload_trace",
      "profile": "dcp-front",
      "user_prompt": "청구 구분 선택값이 Vuex DataStore와 Axios payload에 반영되는 경로를 확인하고 누락만 고쳐줘.",
      "required_project_info_artifacts": ["project-summary.md", "module-responsibility-map.md", "entrypoints.md", "key-flows.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["route: claim selection route", "view: selection Vue view", "component: selector component", "Vuex: selected claim type state", "DataStore: selected claim type carrier", "Axios: payload field mapping", "CSS: no visual change expected", "Playwright: selection flow check"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to missing carrier mapping", "Report evidence from route view component Vuex DataStore Axios CSS Playwright surfaces"],
      "stop_question_conditions": ["stop and ask if business meaning of the selection value is unclear", "stop and ask if payload field name is ambiguous", "stop and ask if focused verification cannot confirm the mapping"],
      "verification_expectation": ["focused verification: run targeted type or lint command", "focused verification: report static payload trace when runtime check is unavailable"]
    },
    {
      "id": "front_playwright_route_smoke",
      "profile": "dcp-front",
      "user_prompt": "청구 상세 진입 route와 화면 렌더링 확인 절차를 현재 파일 기준으로 정리하고 필요한 최소 보강만 해줘.",
      "required_project_info_artifacts": ["project-summary.md", "architecture-map.md", "entrypoints.md", "key-flows.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["route: claim detail route name", "view: detail Vue view", "component: detail section component", "Vuex: detail state lookup", "DataStore: detail cache carrier", "Axios: detail load client", "CSS: detail layout wrapper", "Playwright: route render smoke check"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only when verification gap is concrete", "Report evidence from route view component Vuex DataStore Axios CSS Playwright surfaces"],
      "stop_question_conditions": ["stop and ask if route parameters are unclear", "stop and ask if detail load API contract is ambiguous", "stop and ask if focused verification cannot reach the route"],
      "verification_expectation": ["focused verification: run route smoke check when available", "focused verification: report manual route DOM check fallback"]
    },
    {
      "id": "services_mybatis_condition",
      "profile": "dcp-services",
      "user_prompt": "보험금 조회 조건 하나가 MyBatis 동적 SQL에서 누락되는지 확인하고 필요한 최소 수정만 해줘.",
      "required_project_info_artifacts": ["project-summary.md", "architecture-map.md", "module-responsibility-map.md", "api/eai-interface-index.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["controller: claim query mapping", "service: claim query method", "repository: claim query repository", "MyBatis: claim query XML id", "EAI: no outbound interface change expected", "resources-env: active datasource property", "profile: Maven local profile", "verification: module compile check"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to confirmed SQL condition gap", "Report evidence from controller service repository MyBatis EAI resources-env profile verification surfaces"],
      "stop_question_conditions": ["stop and ask if query business condition is unclear", "stop and ask if DTO field meaning is ambiguous", "stop and ask if focused verification cannot prove mapper syntax"],
      "verification_expectation": ["focused verification: run module compile or mapper-related check", "focused verification: report exact Maven directory and profile"]
    },
    {
      "id": "services_eai_parameter_trace",
      "profile": "dcp-services",
      "user_prompt": "EAI 호출 파라미터 한 필드가 controller부터 mapper 또는 interface resource까지 전달되는지 확인하고 누락만 고쳐줘.",
      "required_project_info_artifacts": ["project-summary.md", "key-flows.md", "api/eai-interface-index.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["controller: request field intake", "service: outbound preparation method", "repository: lookup support path", "MyBatis: supporting mapper query", "EAI: interface id and payload field", "resources-env: interface endpoint property", "profile: runtime environment selection", "verification: focused service check"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to missing EAI field propagation", "Report evidence from controller service repository MyBatis EAI resources-env profile verification surfaces"],
      "stop_question_conditions": ["stop and ask if EAI field semantics are unclear", "stop and ask if endpoint profile changes behavior", "stop and ask if focused verification cannot prove outbound payload"],
      "verification_expectation": ["focused verification: run narrow compile or service test when available", "focused verification: report static EAI payload trace fallback"]
    },
    {
      "id": "services_resources_env_profile",
      "profile": "dcp-services",
      "user_prompt": "로컬 실행 profile에서 사용하는 resources-env 설정 키가 현재 서비스 코드와 맞는지 확인하고 누락만 보강해줘.",
      "required_project_info_artifacts": ["project-summary.md", "architecture-map.md", "module-responsibility-map.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["controller: no endpoint change expected", "service: config consumer method", "repository: no query change expected", "MyBatis: no mapper change expected", "EAI: no interface change expected", "resources-env: local property key", "profile: Maven or Spring profile selector", "verification: config load check"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to confirmed resources-env key gap", "Report evidence from controller service repository MyBatis EAI resources-env profile verification surfaces"],
      "stop_question_conditions": ["stop and ask if target runtime profile is unclear", "stop and ask if property default changes production behavior", "stop and ask if focused verification cannot confirm config load path"],
      "verification_expectation": ["focused verification: run config-related compile or package check", "focused verification: report active profile fallback evidence"]
    },
    {
      "id": "services_controller_validation",
      "profile": "dcp-services",
      "user_prompt": "controller 요청 필드 검증 누락 여부를 service 흐름과 repository 사용처 기준으로 확인하고 최소 수정만 해줘.",
      "required_project_info_artifacts": ["project-summary.md", "entrypoints.md", "key-flows.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["controller: validation annotation or guard", "service: business validation branch", "repository: downstream query consumer", "MyBatis: parameter null behavior", "EAI: no interface change expected", "resources-env: no config change expected", "profile: Maven test profile", "verification: controller or service test"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to confirmed validation gap", "Report evidence from controller service repository MyBatis EAI resources-env profile verification surfaces"],
      "stop_question_conditions": ["stop and ask if validation rule is business-specific", "stop and ask if null behavior differs by caller", "stop and ask if focused verification cannot prove request handling"],
      "verification_expectation": ["focused verification: run controller or service test when available", "focused verification: report request validation trace fallback"]
    },
    {
      "id": "generic_readme_script_alignment",
      "profile": "generic",
      "user_prompt": "README 실행 명령이 현재 package scripts와 맞는지 확인하고 틀린 줄만 고쳐줘.",
      "required_project_info_artifacts": ["project-summary.md", "architecture-map.md", "entrypoints.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["entrypoint: documented start command", "module: package root", "config: package scripts", "data: no schema change expected", "tests: command smoke check", "scripts: npm script list"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to incorrect README command", "Report evidence from entrypoint module config data tests scripts surfaces"],
      "stop_question_conditions": ["stop and ask if preferred command target is unclear", "stop and ask if current script has multiple valid environments", "stop and ask if focused verification cannot confirm command existence"],
      "verification_expectation": ["focused verification: run package script listing or dry check", "focused verification: report README and package evidence"]
    },
    {
      "id": "generic_config_test_surface",
      "profile": "generic",
      "user_prompt": "config 파일의 옵션 이름 변경 요청이 현재 tests와 scripts에 어떤 영향을 주는지 확인하고 필요한 최소 수정만 해줘.",
      "required_project_info_artifacts": ["project-summary.md", "module-responsibility-map.md", "entrypoints.md", "verification-guide.md"],
      "expected_file_symbol_surfaces": ["entrypoint: config consumer entry", "module: config owner module", "config: option definition", "data: option value shape", "tests: option coverage test", "scripts: verification command"],
      "expected_behavior": ["Read central knowledge docs first when present", "Verify current files before editing", "Apply minimal diff only to confirmed config option gap", "Report evidence from entrypoint module config data tests scripts surfaces"],
      "stop_question_conditions": ["stop and ask if option rename compatibility is unclear", "stop and ask if data shape changes are broader than requested", "stop and ask if focused verification cannot prove config behavior"],
      "verification_expectation": ["focused verification: run targeted test or type check when available", "focused verification: report config consumer trace fallback"]
    }
  ]
}
```
