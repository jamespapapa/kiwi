# Ultrawork Agent Prompts

이 디렉터리는 KIWI가 Qwen runtime의 `extensions/ultrawork/agents/`로 설치하는 subagent 시스템 프롬프트 원본이다.

- `dcp-front-developer.md`: dcp-front 전용 구현 agent
- `dcp-backend-developer.md`: dcp-services 및 하위 모듈 전용 구현 agent
- `drt-front-developer.md`: DRT 고객용 Vue 3/Vite 프론트 전용 구현 agent
- `drt-backend-developer.md`: DRT API Spring Boot/MyBatis 백엔드 전용 구현 agent
- `drt-cms-front-developer.md`: DRT CMS/관리자 Quasar 프론트 전용 구현 agent
- `drt-cms-backend-developer.md`: DRT CMS/관리자 Spring/MyBatis 백엔드 전용 구현 agent

프롬프트는 Qwen3.5-397B가 짧은 지시만으로도 프로젝트 구조, 변경 전 탐색 순서, 중단 조건, 검증 방식을 떠올릴 수 있게 작성한다. 너무 긴 지식 베이스를 붙이지 말고, 실제 작업 전 현재 target repo의 파일을 다시 읽도록 유지한다.
