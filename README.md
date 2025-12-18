# AI 협업툴 디벨롭 버전

**공과대학(특히 컴퓨터공학과) 저학년 학생들이 쉽게 팀을 꾸리고, 업무를 나누고, 프로젝트를 끝까지 가져갈 수 있도록 돕는 AI 기반 협업 웹 서비스입니다.**

## 1. Key Improvements: From Synchronous to Asynchronous

본 프로젝트는 단순한 기능 구현을 넘어, **다수의 사용자가 동시에 AI 기능을 요청해도 서버가 중단되지 않는 프로덕션 레벨의 안정성**을 확보하는 데 주력했습니다. 이를 위해 **Async I/O, Non-blocking Process, Background Auto-save** 기술을 적용하여 시스템의 응답성과 처리량을 대폭 향상시켰습니다.

## 2. Technical Evolution: Basic vs. Production Code

| 구분 | 기존 구현 (Baseline) | 디벨롭 버전 (Advanced Async) | 개선 효과 |
| :--- | :--- | :--- | :--- |
| **Architecture** | **Synchronous (Blocking)**<br>(요청 처리 중 서버 스레드 점유) | **Asynchronous (Non-blocking)**<br>(`async def`, `await` 기반 비동기 처리) | AI 생성(약 10~30초) 중에도 다른 API 요청(페이지 이동 등) 정상 처리 |
| **AI Client** | **openai.OpenAI**<br>(동기 클라이언트 사용) | **openai.AsyncOpenAI**<br>(비동기 클라이언트 및 코루틴 적용) | GPT-4o와 같은 대규모 모델 호출 시 I/O 대기 시간의 리소스 효율화 |
| **UX Flow** | **Modal Waiting**<br>(생성 완료까지 사용자가 화면에서 대기) | **Background Save & Toast**<br>(백그라운드 자동 저장 + 실시간 알림) | 사용자의 대기 시간을 제거하고(Zero-waiting), 업무 흐름 끊김 방지 |
| **Data Integrity** | **Silent Caching Issue**<br>(브라우저 캐시로 인한 데이터 갱신 지연) | **Cache Busting Strategy**<br>(Timestamping & Force Reload) | 데이터 생성 직후 사용자 화면에 즉각 반영되도록 데이터 일관성 보장 |

## 3. Detailed Technical Implementations

#### 1. Backend: 비동기 서버 전환 (Async Transformation)
- **구현:** Django Views를 `def`에서 `async def`로 전환하고, OpenAI 요청 로직을 `await client.chat.completions.create`로 변경했습니다.
- **DB 안정성:** 비동기 환경에서 동기식 ORM(Django ORM)을 안전하게 사용하기 위해 `sync_to_async` 래퍼(Wrapper)를 적용하여 데이터베이스 접근 시 발생할 수 있는 스레드 충돌을 방지했습니다.
- **코드 통합:** 산재되어 있던 보고서 관련 로직(`users/views`)을 `gptapi` 앱으로 통합하여 유지보수성을 높였습니다.

#### 2. UX/UI: Non-blocking 사용자 경험 설계
- **자동 저장 프로세스:** AI가 문서를 생성하는 즉시 사용자의 개입 없이 DB에 **자동 저장(Auto-save)**되도록 로직을 변경했습니다. 불필요한 "확인 팝업"을 제거하여 프로세스를 단축했습니다.
- **Smart Toast Notification:** `React-Toastify`를 고도화하여 진행 상황(생성 중 -> 저장 중 -> 완료)을 실시간으로 시각화했습니다.
- **Interactive Feedback:** 완료 토스트를 클릭하면 `window.location.reload()`를 트리거하여, 저장된 최신 데이터를 사용자가 즉시 확인할 수 있도록 UX를 개선했습니다.

#### 3. Reliability: 데이터 신뢰성 확보
- **캐시 방지(Cache Busting):** SPA(Single Page Application) 특성상 발생하는 데이터 미갱신 문제를 해결하기 위해, API 호출 시 `?t={timestamp}` 쿼리 파라미터를 추가하여 브라우저가 강제로 최신 데이터를 페칭하도록 설계했습니다.
- **세션 유지:** 모든 `axios` 요청에 `withCredentials: true` 옵션을 강제하여, 비동기 작업 도중 세션이 만료되거나 인증 오류가 발생하는 엣지 케이스를 차단했습니다.

---

#### 초기 버전 & 상세 설명
[![GitHub](https://img.shields.io/badge/GitHub-View_Repository-181717?style=for-the-badge&logo=github)](https://github.com/gazxxni/AI_collaboration_tool)


