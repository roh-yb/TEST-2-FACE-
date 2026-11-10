# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 현황

얼굴 사진을 업로드하면 OpenAI 이미지(vision) 모델이 관상을 풀이해 주는 Streamlit 웹앱이다. GitHub에 올린 뒤 Streamlit Community Cloud로 배포한다.

`PROMPTS.md`의 4단계 개발(뼈대 → 기능 → UI → Playwright 검토)과 검토 결과 수정까지 **모두 끝났다.** 남은 일은 실제 얼굴 사진으로 풀이 품질을 확인하는 것과 GitHub/Streamlit Cloud 배포다. 요구사항의 기준은 `PRD.md`다. 기능 ID(F1–F8 필수, O1–O5 선택), 출력 형식(6장), 예외 처리(13장)가 들어 있다.

## 명령어

가상환경은 `.venv/`(Python 3.12)에 있다. Windows에서 한글이나 이모지를 출력할 때는 `PYTHONIOENCODING=utf-8`을 붙인다. 붙이지 않으면 cp949 인코딩 오류가 난다.

```bash
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/streamlit run app.py
.venv/Scripts/streamlit run app.py --server.headless true --server.port 8501   # Playwright 테스트용
.venv/Scripts/python -m py_compile app.py prompts.py                            # 문법 확인
```

테스트 프레임워크나 린터는 없다. 검증 방법은 세 가지다.
- 함수 단위: `app.preprocess_image()`, `app.run_analysis()`를 직접 호출한다.
- 화면 단위: `streamlit.testing.v1.AppTest`로 실행한다.
- 브라우저: Playwright MCP 도구를 쓴다.
- API 키 없음이나 잘못된 키는 `OPENAI_API_KEY=""` 같은 환경변수를 주고 별도 포트로 실행해 확인한다. `load_dotenv`는 이미 있는 환경변수를 덮어쓰지 않는다.
- OpenAI 호출 횟수는 서버 로그의 `api.openai.com` 줄 수로 센다. httpx가 INFO 레벨로 남긴다.

Playwright MCP는 **프로젝트 폴더 안의 파일만** 업로드하거나 저장할 수 있다. 테스트 이미지는 `.playwright-mcp/test-images/`, 스크린샷은 `.playwright-mcp/screenshots/`에 있다. 이 폴더는 git에서 제외된다. 테스트 이미지에는 얼굴 그림, 얼굴 2개, 투명 PNG, 17MB, 손상 파일, 잘린 JPEG, 20000×20000 bomb가 있다.

## 아키텍처

**처리 흐름 (`app.py`)**
1. 입력: `render_inputs()`. 업로드 탭과 카메라 탭 두 가지다.
2. `reset_result_if_new_image()`: 이미지 바이트의 sha256이 바뀌면 이전 결과와 오류를 지운다.
3. `prepare_image()` → `preprocess_image()`:
   - 해상도는 픽셀을 디코딩하기 **전에** `MAX_PIXELS`(4천만)로 검사한다.
   - EXIF 회전 보정, 투명 배경은 흰색 합성, 긴 변 1024px, JPEG data URL
4. 미리보기: 원본 파일이 아니라 전처리를 마친 data URL을 쓴다.
5. `run_analysis()`: `(결과, 오류 메시지)`를 반환하고, 결과 앞의 서두는 `strip_preamble()`로 잘라낸다.
6. `render_result()`: 결과를 표시한다.

**중복 호출 방지 패턴 (main)**
- 버튼의 `on_click`은 `run_requested` 플래그만 세운다.
- `main()`은 그 플래그를 지역변수 `busy`로 옮기고 **곧바로 내린다.** 분석 도중 사진을 바꿔 실행이 중단돼도 새 사진이 자동으로 분석되지 않게 하기 위해서다.
- `busy`인 동안 모든 버튼을 `disabled`로 그린다. 분석 결과와 오류는 session_state에 넣고 `st.rerun()`으로 버튼을 다시 살린다.
- 따라서 오류 메시지는 `st.error`로 바로 그리지 않고 `session_state.error`를 거쳐 표시해야 rerun 뒤에도 남는다.

**풀이와 안내 구분**
- 정상 풀이에는 `prompts.RESULT_MARKER`("전체 인상")가 들어간 Markdown **제목 줄**이 있다. `is_reading()`이 이 줄로 판단한다.
- 제목 줄이 없으면(얼굴 없음, 여러 명 등) `st.info` 안내로만 보여주고, 저장·다시 보기 버튼은 숨긴다.
- 안내 문장에도 "전체 인상"이라는 단어가 나올 수 있으므로 단순 포함 여부로 판단하면 안 된다.
- 프롬프트는 `###` 제목을 쓰게 한다. 결과 제목(`st.header`, h2)보다 작게 보이게 하기 위해서다.

**설정**
- `.streamlit/config.toml`:
  - `server.maxUploadSize = 10`: `app.py`의 `MAX_FILE_SIZE_MB`와 같게 유지한다. 10MB를 넘는 파일은 Streamlit이 직접 막고 영어 메시지를 보여준다. 이 문구는 바꿀 수 없다.
  - `client.showErrorDetails = "none"`: 처리되지 않은 오류가 나도 traceback을 화면에 보여주지 않는다.
  - 테마
  - 설정을 바꾸면 서버를 재시작해야 반영된다.
- `analyze_face()`는 `temperature`를 지정하지 않는다. 추론형 모델이 기본값 외의 값을 거부하기 때문이다. 답변 길이 제한은 `max_completion_tokens`로 한다.

### 키와 설정 로딩: 로컬과 Cloud 두 경로

`get_secret(key, default)`는 먼저 `os.getenv`(`python-dotenv`로 읽은 `.env`)를 보고, 없으면 `st.secrets`를 본다. Streamlit Cloud에는 `.env`가 올라가지 않으므로 앱의 Secrets(TOML)에 같은 키를 넣어야 한다. `secrets.toml`이 없을 때 `st.secrets` 접근이 예외를 내므로 try/except로 감싼다.

- `OPENAI_API_KEY`: 필수. 없으면 `st.error`로 안내한 뒤 `st.stop()`
- `OPENAI_MODEL`: 기본값 `gpt-4o-mini`. 잘못된 모델이면 `NotFoundError`나 `BadRequestError`가 나고, 설정을 확인하라는 안내로 바꿔 보여준다.

`.env`에는 실제 키가 들어 있다. 내용을 읽거나 출력하지 않는다.

## 지켜야 할 제품 규칙

- UI와 결과는 모두 한국어로 한다. 풀이는 존댓말로 쓴다. 면책 문구("재미로 보는 결과이며 과학적 근거가 없다")를 항상 표시한다.
- 이미지는 디스크에 저장하지 않는다. 대신 OpenAI로 **전송된다는 사실**을 개인정보 안내(`PRIVACY_NOTICE`)에 밝힌다. "바로 사라진다"처럼 전송 사실을 감추는 문구는 쓰지 않는다.
- 프롬프트 원칙:
  - 외모를 비하하거나 인종·성별·장애 같은 민감한 속성으로 판단하지 않는다. 실존 인물이 누구인지 추측하지 않는다.
  - 가정형 표현("~하다면")을 쓰지 않고, 사진에서 관찰한 생김새를 근거로 풀이한다.
  - 얼굴 판정을 너무 엄격하게 하면 정상 사진도 거절하므로, 얼굴 없음과 두 명 이상일 때만 거절한다.
- OpenAI 예외는 사용자용 메시지로 바꾸고, 상세 내용은 로그에만 남긴다. 로그 속 키는 SDK가 마스킹한다.
- GitHub 저장소 이름은 영문을 권장한다. 로컬 폴더 이름이 한글(`관상`)이다.
