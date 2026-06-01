# Project Profile: dcp-front

이 파일은 폐쇄망 안에서 Qwen3.5-397B-A17B가 `dcp-front-develop` 계열 프로젝트를 문서화할 때 사용할 단일 프로젝트 프로필이다.

중요: 이 프로필은 현재 레포를 대신 분석한 결과가 아니다. Qwen은 이 내용을 시작 힌트로만 사용하고, 모든 결론은 폐쇄망 안의 실제 target repo 파일에서 다시 검증해야 한다.

## 프로젝트 정체성 힌트

- 유형: 삼성생명 DCP 프론트엔드.
- 기술 힌트: Vue 2.7, Vue CLI 3, Vue Router 3, Vuex 3, Options API 중심일 가능성이 높다.
- 주요 분리 축: PC/MO 채널, 업무 도메인, route 기반 화면 flow, 공통 component/modal, Vuex/DataStore.
- 핵심 위험: 화면 사이 값 전파, 공유 모달 consumer, positional array return, route params, `spotLoad`/`spotSave`, legacy branch driver.

반드시 현재 레포에서 검증할 것:

- 실제 Vue/Vue CLI/Router/Vuex 버전.
- source root, router root, views root, store root.
- PC/MO 분리 방식.
- API client/proxy path 규칙.
- `DataStore`, `spotLoad`, `spotSave`, `DATA_UPDATE`, `getDataJson` 존재 여부와 사용 방식.
- 보험금 청구 인터넷 flow가 현재 코드에 있는지, 경로가 동일한지.
- global/scoped/channel style root, 공통 button/control class, parent layout wrapper, DOM 직접 조작 패턴, animation/effect 구현 규칙.

## 우선 읽을 후보

먼저 `rg --files`로 실제 존재를 확인한 뒤 읽는다.

- `package.json`
- `vue.config.js`
- `babel.config.js`
- `src/main.js`
- `src/router`
- `src/views`
- `src/components`
- `src/store`
- `src/store/modules/com/DataStore.js`
- `src/utils`
- `src/plugins`
- `src/mixins`
- `src/styles`
- `src/assets`
- 전역 `*.css`, `*.scss`, `*.sass`, `*.less`
- `QWEN.md`
- `KIWI.md`
- `docs/llm`

보험금 청구 인터넷 flow가 대상이면 후보:

- `src/views/mo/mysamsunglife/insurance/internet`
- `src/router/mo/mysamsunglife/insurance/internet/route.js`
- `MDP-MYINT020110M`
- `MDP-MYINT020130M`
- `MDP-MYINT020530L`
- `MDP-MYINT020580M`
- `MDP-MYINT020720M`
- `MDP-MYINT020540M`
- `MDP-MYINT020542M`

## 필수 검색어

프로젝트 전체 구조:

```bash
rg -n "new Vue|createApp|Vue.use|VueRouter|routes|router|store|Vuex|modules" src package.json vue.config.js
rg -n "axios|fetch|http|api|proxy|/gw|/cms/contents|interceptor|request|response" src
rg -n "DataStore|DATA_UPDATE|getDataJson|spotLoad|spotSave|route.params|this.\\$route|this.\\$router" src
```

화면/flow 분석:

```bash
rg -n "name:|path:|component:|beforeEnter|redirect|children" src/router src/views
rg -n "created\\(|mounted\\(|activated\\(|beforeRoute|watch:|computed:|methods:" src/views src/components
rg -n "\\$emit|props:|model:|v-model|sync|callback|close|confirm" src/components src/views
```

CSS/DOM 구조 분석:

```bash
rg -n "class=|:class|v-bind:class|ref=|\\$refs|querySelector|getElementById|addEventListener|style=|:style" src
rg -n "position:|z-index|overflow|transform|transition|animation|::before|::after|box-shadow|filter" src
rg -n "button|btn|control|toolbar|tab|panel|drawer|inspector|modal|dialog" src
rg -n "scoped|lang=\"scss\"|lang='scss'|@import|require\\(.*css|import .*css|import .*scss" src
```

보험금 청구/legacy branch driver:

```bash
rg -n "whoGbn|busnScCd|clamReason|clamCause|inqrScCd|claim|clam|insurance|MYINT" src
rg -n "020110M|020130M|020530L|020580M|020720M|020540M|020542M" src
```

## 문서화해야 할 구조 패턴

### Route To Screen

문서화 목표:

- URL path와 route name.
- PC/MO 채널.
- route file 위치.
- lazy load component 경로.
- route guard, redirect, meta.
- route params/query.
- 다음 화면으로 넘기는 값.

문서 위치:

- `docs/knowledge/flows/<flow-name>.md`
- `docs/knowledge/modules/router.md`

필수 근거:

- route 선언부 `path`, `name`, `component`.
- 화면 component 파일.
- navigation 호출부.

### Screen To Component/Modal

문서화 목표:

- 화면의 책임.
- local state/data.
- computed/watch.
- child component/modal.
- modal return contract.
- shared component consumer 목록.

특별 주의:

- 공유 모달을 변경하는 작업은 모든 consumer를 먼저 찾아야 한다.
- 여러 consumer가 있는 모달은 positional return array가 위험하다. 문서에 return index 의미와 consumer별 해석을 분리한다.
- event 이름과 payload shape를 반드시 적는다.

### State And DataStore

문서화 목표:

- Vuex module, action, mutation, getter.
- `DataStore` 또는 유사 장기 carrier.
- local object에서 store object로 옮겨지는 시점.
- route param으로 넘어가는 값.
- reload/back/skip branch에서 default가 어떻게 되는지.

필수 추적:

- producer.
- local carrier.
- store carrier.
- route carrier.
- `spotLoad` binding.
- `spotSave` payload.
- downstream consumer.

### API Client And Proxy

문서화 목표:

- HTTP client wrapper.
- base URL/proxy path.
- request interceptor.
- response interceptor.
- error display.
- loading/progress handling.
- backend endpoint 또는 service id 추정.

주의:

- front path와 backend controller path가 1:1이 아닐 수 있다.
- `/gw`, `/cms/contents` 같은 gateway/proxy 경로는 backend에서 다시 매핑될 수 있다.
- payload field 이름은 화면 label이 아니라 API object 기준으로 문서화한다.

### Styles And Channel Variants

문서화 목표:

- PC/MO style root.
- shared style.
- component scoped style 여부.
- responsive/channel split.
- image/static asset 위치.
- parent layout/wrapper와 주요 container class.
- 공통 button/control/tab/panel/modal selector와 우선순위.
- DOM 직접 조작, refs/directives/class toggle/style binding 패턴.
- `position`, `z-index`, `overflow`, `transform`, fixed width/min-width 등 layout에 영향을 주는 CSS.
- `transition`, `animation`, `::before`, `::after`, glow/bling effect가 대상 bounds 안에 갇히는지 여부.
- resize/zoom에서 text overflow, horizontal scroll, layout shift를 일으키기 쉬운 패턴.

주의:

- 문서화 시 visual 설명보다 어떤 화면 family가 어떤 style root를 쓰는지가 더 중요하다.
- 단순 버튼 스타일 변경도 기존 containing block, scoped/global style 위치, selector 충돌, overflow/animation 영향도를 확인하지 않으면 high risk로 분류한다.
- 작은 control의 shine/bling 효과는 pseudo-element가 부모나 주변 UI를 덮지 않게 bounds와 clipping 전략을 문서화한다.
- `position: relative`를 추가하는 행위도 새로운 containing block을 만들 수 있으므로 기존 absolute/fixed child와 주변 layout 영향을 함께 적는다.

## 보험금 청구 인터넷 flow 특화 힌트

이 섹션은 현재 레포에서 실제 존재를 확인한 뒤에만 사용한다.

기준 후보:

- `020110M`: intro/direct start 계열 후보.
- `020130M`: 청구 주체 선택 후보.
- `020530L`: 질문 modal 후보.
- `020580M` ~ `020720M`: 대리/수익자 flow 후보.
- `020540M` ~ `020542M`: 본인/자녀 flow 후보.

branch driver 후보:

- `whoGbn`
- `busnScCd`
- `clamReason`
- `clamCause`
- `inqrScCd`

값 후보 예시:

- `whoGbn`: `1`, `5`, `13`
- `busnScCd`: `AG`, `DF`, `DT`
- `clamReason`: `hsptl`, `dth`
- `clamCause`: `1`, `2`

주의:

- 이 값들의 의미는 반드시 현재 코드 분기와 label에서 다시 확인한다.
- branch driver 의미를 모르면 “미확인”으로 남긴다.
- 보험금 청구 flow 문서에는 intro, 질문 modal, 저장/로드, 다음 step, skipped branch default를 반드시 포함한다.

## dcp-front 산출물 우선순위

1. `00-index.md`: PC/MO, route, store, API, 위험 flow 인덱스.
2. `01-repository-map.md`: `src/router`, `src/views`, `src/store`, `src/components`, `src/utils` 책임.
3. `02-build-and-runtime.md`: Node/npm/Vue CLI 명령과 proxy/dev server.
4. `04-domain-glossary.md`: 화면ID, branch driver, 업무 코드값.
5. `07-state-and-data-propagation.md`: `DataStore`, route params, `spotLoad`, `spotSave`.
6. `05-api-and-contracts.md`: front API wrapper와 gateway path.
7. `flows/insurance-claim-internet.md`: 보험금 청구 인터넷 flow가 있으면 최우선 상세화.
8. `12-change-playbooks.md`: 화면 필드 추가, 공유 모달 변경, API field 변경, route 변경.

## dcp-front 품질 체크리스트

- route에서 화면까지 연결된 주요 flow가 최소 5개 이상 문서화되었는가?
- 공통 modal/component consumer 추적 방법이 문서화되었는가?
- `DataStore` 또는 동등 carrier의 producer/consumer가 설명되었는가?
- `spotLoad`/`spotSave`가 있다면 payload와 저장 시점이 정리되었는가?
- branch driver 후보가 값/의미/근거/위험으로 정리되었는가?
- API wrapper와 error handling이 설명되었는가?
- PC/MO 채널 분리와 route root가 구분되었는가?
- 변경 playbook이 실제 검색어와 중단 조건을 포함하는가?

## dcp-front 중단 조건

- 현재 레포에서 route root를 찾지 못하면 문서 작성을 멈추고 gap을 남긴다.
- API client를 찾지 못하면 endpoint contract를 확정하지 않는다.
- branch driver 의미가 label 또는 분기 코드로 확인되지 않으면 의미를 확정하지 않는다.
- 공유 modal consumer를 찾지 못하면 변경 playbook에 “consumer search required”를 high risk로 남긴다.
