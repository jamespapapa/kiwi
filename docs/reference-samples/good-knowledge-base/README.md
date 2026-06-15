# Good Knowledge Base Samples

This directory contains reference samples for KIWI project-documentation output.

These samples are for style, structure, evidence density, and cross-linking quality. They are not reusable facts for a new target project. When Qwen documents a new repository, it must re-read the actual target files and replace every claim, path, line number, and gap list with target-specific evidence.

## Sample Sets

| Sample | Source Repository Reviewed | Use As Reference For |
| --- | --- | --- |
| [dcp-front](dcp-front/README.md) | `/Users/jules/Desktop/work/untitle/dcp/dcp-front-develop` | Vue 2 / Vue CLI front-end route, screen, Vuex/DataStore, API, flow documentation. |
| [dcp-services](dcp-services/README.md) | `/Users/jules/Desktop/work/untitle/dcp/dcp-services-mevelop` | Java 8 / Spring / Maven multi-module backend, controller, EAI, Redis, security documentation. |

## Prompt Hint For Closed-Network Runs

Add this sentence to the documentation prompt when these samples are available:

> 참고 샘플로 `docs/reference-samples/good-knowledge-base/dcp-front/docs/knowledge/` 또는 `docs/reference-samples/good-knowledge-base/dcp-services/docs/knowledge/`를 읽고, 문서 구조/근거 표/상세도만 참고하라. 샘플의 사실관계는 target 프로젝트에 복사하지 말고, 모든 주장은 현재 target repo에서 다시 검증한 path:line 근거로 교체하라.
