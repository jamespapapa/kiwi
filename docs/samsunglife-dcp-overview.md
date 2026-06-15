# Samsung Life DCP Overview

이 문서는 KIWI 프롬프트 빌더가 삼성생명 홈페이지 작업 지시를 구조화할 때 참고하는 큰그림 컨텍스트다. 기준 소스는 `/Users/jules/Desktop/work/untitle/dcp/` 아래의 `dcp-front-develop`, `dcp-services-mevelop`, `memory/*/latest.md`이며, 해당 소스는 다소 오래된 스냅샷이므로 실제 구현 지시는 사용자가 초기화한 로컬 프로젝트 파일을 다시 읽고 확정해야 한다.

## 큰 구조

- DCP는 삼성생명 홈페이지의 프론트엔드와 백엔드 서비스 묶음이다.
- 프론트엔드는 `dcp-front-develop`에 있고 Vue 2.7, Vue CLI 3, Vue Router 3, Vuex 3, Options API 중심이다.
- 백엔드는 `dcp-services-mevelop`에 있고 Maven 멀티모듈, Java 8, Spring 5 MVC, MyBatis, Oracle, Redis, EAI 연계 중심이다.
- 작업 지시를 만들 때는 프론트 라우트/화면/상태 흐름과 백엔드 controller/service/EAI/Redis 흐름을 분리해서 추적해야 한다.

## 프론트엔드 지도

- 주요 루트: `dcp-front-develop/src`
- 화면: `src/views`
- 라우트: `src/router`
- 공통 컴포넌트: `src/components`
- Vuex 공유 상태: `src/store/modules/com`
- 공통 유틸/플러그인: `src/utils`, `src/plugins`, `src/mixins`
- 스타일: `src/styles/PC`, `src/styles/MO`, `src/styles/share`

주요 채널은 PC/MO로 분리된다. 모바일 업무 화면은 `src/views/mo`, 라우트는 `src/router/mo` 아래에 넓게 분포한다. 보험금 청구 인터넷 플로우는 다음 경로가 핵심 기준점이다.

- `src/views/mo/mysamsunglife/insurance/internet`
- `src/router/mo/mysamsunglife/insurance/internet/route.js`
- `src/store/modules/com/DataStore.js`

프론트 변경은 라우트, 상위 화면, 모달/공유 컴포넌트, Vuex/DataStore, route params, `spotLoad`, `spotSave`, downstream step 화면까지 이어지는 값 전파를 반드시 확인해야 한다.

## 백엔드 지도

백엔드는 루트 `pom.xml`에서 여러 `dcp-*` 모듈을 묶는다. 주요 모듈은 다음과 같다.

- `dcp-core`: 공통 파라미터, 예외, EAI helper, Redis/session, interceptor, 메시지/코드 같은 공유 기반
- `dcp-gateway`: 외부 요청의 전단, 인증/권한/세션/보안 솔루션 연계, 라우팅 성격
- `dcp-insurance`: 보험 도메인 업무 처리
- `dcp-loan`: 대출 도메인 업무 처리
- `dcp-member`: 회원 도메인 업무 처리
- `dcp-retire`, `dcp-pension`, `dcp-fund`, `dcp-trust`, `dcp-product`: 상품/연금/펀드/신탁/공시성 업무
- `dcp-cms`, `dcp-display`: CMS, 콘텐츠, 화면 데이터, 배너/게시판/전시성 업무
- `dcp-batch`, `dcp-async`, `dcp-upload`: 배치, 비동기, 업로드 보조 기능

각 도메인 모듈은 보통 `src/main/java/com/samsunglife/dcp/<domain>` 아래에 controller/service/response/request/VO 성격의 패키지를 가진다. SQL/MyBatis 설정은 `src/main/resources/sqlconf`, Spring 설정은 `src/main/resources/spring`, EAI 정의는 `src/main/resources/META-INF/eai` 계열을 확인한다.

## 통합 흐름

- 프론트는 `/gw`, `/cms/contents` 같은 프록시 경로를 통해 backend/gateway 계층과 통신한다.
- 핵심 금융/보험 처리는 백엔드 도메인 service에서 EAI service id와 VO를 구성해 후방 시스템을 호출하는 형태가 많다.
- Redis는 로그인 세션, 금융거래 로그, 임시 업무 상태, FDS/인증 관련 상태에 자주 관여한다.
- 프론트와 백엔드 연결은 코드 스냅샷만으로 완전히 신뢰하기 어렵다. 프롬프트 빌더는 큰그림만 제공하고, 실제 작업 전에는 로컬 파일 검색으로 API path, payload, route, state carrier를 다시 확인해야 한다.

## 작업 지시 원칙

프롬프트 빌더가 `qwencode`에 넘길 최종 프롬프트는 약한 코딩 모델 기준으로 충분히 구조화되어야 한다.

- 요구사항을 레포 용어로 다시 쓴다.
- 시작점 후보를 route, screen, modal, store, controller, service, EAI/SQL 관점으로 나눈다.
- 구현 전 필수 검색어를 명시한다.
- 값 추가/변경이면 default, UI binding, local state, modal result, store key, route params, load/save payload, downstream consumer를 추적하게 한다.
- 보험금 청구류 작업에서는 `whoGbn`, `busnScCd`, `clamReason`, `clamCause`, `inqrScCd` 같은 legacy branch driver의 의미를 임의로 바꾸지 못하게 한다.
- 변경 범위와 금지 범위를 명확히 분리한다.
- 구현 완료 후 changed files, diff 요약, 검증 명령, 남은 위험을 반드시 보고하게 한다.
- 모호하면 편집하지 말고 질문하게 한다.

## 기본 산출물 계약

최종 `qwencode` 프롬프트는 다음 섹션을 포함한다.

1. 실행 모드: `IMPLEMENT APPROVED`, `ANALYSIS ONLY`, 또는 `REVIEW ONLY`
2. 작업 목표
3. DCP 큰그림 요약
4. 현재 로컬 프로젝트에서 확인한 근거
5. 필수 읽기 파일
6. 필수 검색 명령
7. 구현 규칙
8. 검증 계획
9. 완료 보고 형식
10. 중단 조건

