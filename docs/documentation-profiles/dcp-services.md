# Project Profile: dcp-services

이 파일은 폐쇄망 안에서 Qwen3.5-397B가 `dcp-services-mevelop` 계열 프로젝트를 문서화할 때 사용할 단일 프로젝트 프로필이다.

중요: 이 프로필은 현재 레포를 대신 분석한 결과가 아니다. Qwen은 이 내용을 시작 힌트로만 사용하고, 모든 결론은 폐쇄망 안의 실제 target repo 파일에서 다시 검증해야 한다.

## 프로젝트 정체성 힌트

- 유형: 삼성생명 DCP 백엔드 서비스.
- 기술 힌트: Maven 멀티모듈, Java 8, Spring 5 MVC, MyBatis, Oracle, Redis, EAI 연계 중심일 가능성이 높다.
- 주요 분리 축: core/gateway/domain modules, controller/service/mapper/VO, EAI service id, Redis/session, Spring profile/resource config.
- 핵심 위험: module boundary, request/response DTO drift, EAI payload mapping, Redis/session side effect, MyBatis SQL, transaction/error handling.

반드시 현재 레포에서 검증할 것:

- 실제 Java/Maven/Spring 버전.
- root `pom.xml`의 module 목록.
- 각 module의 packaging, dependency direction, profile.
- controller route 규칙.
- request/response/VO naming convention.
- MyBatis mapper/resource 위치.
- EAI definition/client/helper 위치.
- Redis/session/security 설정 위치.

## 우선 읽을 후보

먼저 `rg --files`로 실제 존재를 확인한 뒤 읽는다.

- `pom.xml`
- `*/pom.xml`
- `README.md`
- `QWEN.md`
- `KIWI.md`
- `src/main/java`
- `src/main/resources`
- `src/test`
- `src/main/resources/spring`
- `src/main/resources/sqlconf`
- `src/main/resources/META-INF/eai`
- `application*.properties`
- `application*.yml`
- `logback*.xml`

모듈 후보:

- `dcp-core`
- `dcp-gateway`
- `dcp-insurance`
- `dcp-loan`
- `dcp-member`
- `dcp-retire`
- `dcp-pension`
- `dcp-fund`
- `dcp-trust`
- `dcp-product`
- `dcp-cms`
- `dcp-display`
- `dcp-batch`
- `dcp-async`
- `dcp-upload`

위 모듈 이름은 힌트다. 실제 module 목록은 root `pom.xml`에서 확정한다.

## 필수 검색어

Maven/module 구조:

```bash
rg -n "<modules>|<module>|<artifactId>|<packaging>|<parent>|<dependency>|<java.version>|maven-compiler" pom.xml */pom.xml
rg -n "spring-framework|spring-webmvc|mybatis|redis|jedis|lettuce|oracle|ojdbc|jackson|javax.servlet" pom.xml */pom.xml
```

Spring/controller/service:

```bash
rg -n "@Controller|@RestController|@RequestMapping|@GetMapping|@PostMapping|@ResponseBody|@Service|@Repository|@Component" .
rg -n "extends .*Controller|implements .*Service|@Autowired|@Resource|@Transactional" .
```

DTO/VO/request/response:

```bash
rg -n "class .*Request|class .*Response|class .*Req|class .*Res|class .*VO|class .*Dto|class .*DTO" .
rg -n "get[A-Z].*\\(|set[A-Z].*\\(|@JsonProperty|@RequestBody|@ModelAttribute|@RequestParam|@PathVariable" .
```

MyBatis/SQL:

```bash
rg -n "<mapper|namespace=|select id=|insert id=|update id=|delete id=|resultMap|parameterType|resultType" src/main/resources .
rg -n "@Mapper|SqlSession|selectOne|selectList|insert\\(|update\\(|delete\\(" src/main/java .
```

EAI/external/Redis/session:

```bash
rg -n "EAI|eai|serviceId|svcId|telegram|interface|external|send|receive|Redis|redis|session|cache" .
rg -n "FDS|auth|cert|login|token|cookie|header|interceptor|filter|security" .
```

Error/transaction/logging:

```bash
rg -n "Exception|ErrorCode|BizException|throw new|try \\{|catch \\(|rollback|@Transactional|Logger|log\\." src/main/java
```

## 문서화해야 할 구조 패턴

### Maven Multi-Module

문서화 목표:

- root module 목록.
- module별 artifactId, packaging, source/resource/test root.
- module dependency direction.
- domain module과 shared module 경계.
- build profile과 plugin.

주의:

- module 이름만 보고 책임을 확정하지 않는다. controller/service/package/resource 근거로 확인한다.
- `dcp-core` 같은 shared module은 consumer가 많으므로 변경 위험을 high로 둔다.

### Controller To Service

문서화 목표:

- URL route 또는 request mapping.
- request binding 방식.
- auth/session/context dependency.
- service method.
- response wrapper.
- error handling.

문서 위치:

- `D:/aiops/docs/<project-key>/knowledge/apis/<route-or-controller>.md`
- `D:/aiops/docs/<project-key>/knowledge/modules/<module>.md`

필수 근거:

- controller annotation.
- request/response class.
- service invocation.
- exception/logging branch.

### Service To EAI/Mapper/Redis

문서화 목표:

- business service 책임.
- EAI service id 또는 external client.
- MyBatis mapper/SQL.
- Redis/session/cache key.
- transaction boundary.
- downstream response mapping.

주의:

- 금융/보험 업무 처리는 service layer의 EAI payload mapping이 핵심일 수 있다.
- EAI request/response VO는 필드 의미와 code value를 반드시 별도 표로 정리한다.
- Redis/session 값은 key format, ttl, invalidation, consumer를 찾아야 한다.

### MyBatis/SQL

문서화 목표:

- mapper namespace.
- SQL id.
- parameterType/resultType.
- table name.
- dynamic SQL condition.
- caller method.

주의:

- SQL 파일만 보고 API 의미를 확정하지 않는다. service caller와 DTO를 함께 봐야 한다.
- dynamic SQL branch는 request field와 연결해 문서화한다.

### EAI/External Integration

문서화 목표:

- service id.
- request VO.
- response VO.
- external system hint.
- timeout/retry/error behavior.
- mapping method.
- caller service.

주의:

- EAI id는 문서화 우선순위가 높다. 미래 작업에서 API보다 EAI contract가 더 중요한 경우가 많다.
- `String` map 기반 payload는 field source와 consumer를 추가로 추적한다.

### Gateway/Security/Session

문서화 목표:

- gateway entrypoint.
- filter/interceptor.
- auth/session object.
- cookie/header/user context.
- permission/role branch.
- audit/log/FDS.

주의:

- 보안/세션 관련 값은 확실한 근거 없이 설명하지 않는다.
- masking/encryption은 code path와 config를 함께 확인한다.

## dcp-services 산출물 우선순위

1. `00-index.md`: module, domain, controller, EAI, Redis, mapper 인덱스.
2. `01-repository-map.md`: root module과 resource 구조.
3. `02-build-and-runtime.md`: Maven build/profile/test/local runtime.
4. `03-system-boundaries.md`: core/gateway/domain/external boundary.
5. `05-api-and-contracts.md`: controller route와 request/response.
6. `08-integrations.md`: EAI, Redis, external service, gateway.
7. `06-data-model.md`: request/response/VO/DTO/mapper model.
8. `09-security-auth-privacy.md`: session, auth, role, audit, masking.
9. `12-change-playbooks.md`: API field 추가, EAI 변경, mapper SQL 변경, Redis/session 변경.

## module 문서 표준

각 module 문서는 다음 형식을 따른다.

```markdown
# Module: <module-name>

## Summary

## Maven Identity

## Responsibilities

## Controllers

## Services

## Data/Mapper Resources

## EAI/External Integrations

## Redis/Session Usage

## Dependencies

## Test/Verification

## Change Risks

## Evidence
```

## API contract 문서 표준

backend API 문서는 request handling과 downstream을 함께 다룬다.

```markdown
# API: <route-or-controller-method>

## Summary

## Entrypoint

## Request Binding

## Validation/Default

## Service Flow

## EAI/Mapper/Redis

## Response Mapping

## Error Handling

## Security/Session

## Test Evidence

## Change Risks

## Evidence
```

## dcp-services 품질 체크리스트

- root `pom.xml` module 목록과 실제 module 문서가 일치하는가?
- core/gateway/domain dependency direction이 문서화되었는가?
- controller route에서 service, mapper/EAI, response까지 이어지는 API 문서가 최소 주요 도메인별로 작성되었는가?
- EAI service id와 VO mapping이 인덱싱되었는가?
- Redis/session/cache usage가 key/producer/consumer 관점으로 정리되었는가?
- MyBatis mapper namespace와 service caller가 연결되었는가?
- transaction/error handling이 service flow 문서에 포함되었는가?
- 보안/개인정보 관련 설명이 근거 기반인가?
- 변경 playbook이 실제 검색어와 중단 조건을 포함하는가?

## dcp-services 중단 조건

- root `pom.xml`을 찾지 못하면 module 구조를 확정하지 않는다.
- controller annotation 또는 route mapping을 찾지 못하면 API contract를 확정하지 않는다.
- EAI service id가 추정만 가능하면 `08-integrations.md`에 `미확인`으로 남긴다.
- Redis/session key format을 찾지 못하면 key 의미를 확정하지 않는다.
- SQL mapper와 service caller를 연결하지 못하면 DB 영향도를 low confidence로 둔다.
