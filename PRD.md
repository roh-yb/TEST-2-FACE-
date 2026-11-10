# PRD: AI 관상 분석 웹앱

## 1. 개요

| 항목 | 내용 |
|---|---|
| 제품명 | AI 관상가 (가칭) |
| 한 줄 설명 | 얼굴 사진을 업로드하면 OpenAI 이미지 분석 모델이 관상을 풀이해 주는 웹앱 |
| 플랫폼 | Streamlit (Python) 웹앱 |
| 배포 | GitHub 저장소 → Streamlit Community Cloud |
| AI 모델 | OpenAI Vision 지원 모델 (기본값 `gpt-4o-mini`, 환경변수로 변경 가능) |
| 문서 작성일 | 2026-11-10 |

## 2. 배경 및 목적

- 전통 관상학(이마, 눈, 코, 입, 귀, 얼굴형 등)을 바탕으로 한 재미 위주의 얼굴 풀이 서비스를 만든다.
- 사용자는 사진 한 장만 올리면 몇 초 안에 풀이 결과를 받는다.
- 로컬에서는 `.env` 파일로 API 키를 관리하고, 배포는 GitHub과 Streamlit Cloud로 간단하게 한다.

> ⚠️ 이 서비스는 **오락용**이며 과학적 근거가 없다. 결과 화면에 이 점을 항상 밝힌다.

## 3. 대상 사용자

- 재미로 관상을 보고 싶은 일반 사용자
- 친구·가족 사진으로 결과를 공유하며 즐기려는 사용자

## 4. 핵심 사용자 흐름

1. 사용자가 웹앱에 접속한다.
2. 얼굴 사진을 업로드한다 (JPG / JPEG / PNG / WEBP).
3. 업로드한 이미지 미리보기가 표시된다.
4. **「관상 보기」** 버튼을 누른다.
5. 로딩 스피너가 표시되는 동안 OpenAI API를 호출한다.
6. 관상 풀이 결과가 부위별 섹션과 종합 운세로 표시된다.
7. (선택) 결과를 텍스트 파일로 다운로드하거나 다시 시도한다.

## 5. 기능 요구사항

### 5.1 필수 기능 (MVP)

| ID | 기능 | 설명 |
|---|---|---|
| F1 | 이미지 업로드 | `st.file_uploader`로 jpg, jpeg, png, webp 업로드. 최대 10MB |
| F2 | 이미지 미리보기 | 업로드 즉시 `st.image`로 표시 |
| F3 | 이미지 전처리 | Pillow로 긴 변을 최대 1024px로 줄이고 EXIF 회전 보정, RGB 변환 후 JPEG base64 인코딩 |
| F4 | 관상 분석 요청 | OpenAI API에 이미지(base64 data URL)와 관상 프롬프트를 함께 전송 |
| F5 | 결과 표시 | Markdown으로 부위별 풀이와 종합 평가 표시 |
| F6 | 얼굴 미검출 처리 | 사람 얼굴이 없거나 식별이 어려우면 모델이 그렇게 답하게 하고, 안내 메시지를 표시 |
| F7 | 오류 처리 | API 키 누락, 네트워크 오류, 사용량 초과(rate limit) 등에 사용자 친화적 에러 메시지 표시 |
| F8 | 면책 문구 | "재미로 보는 결과이며 과학적 근거가 없습니다" 안내를 항상 표시 |

### 5.2 선택 기능 (추후)

| ID | 기능 | 설명 |
|---|---|---|
| O1 | 카메라 촬영 | `st.camera_input`으로 바로 촬영해서 분석 |
| O2 | 풀이 스타일 선택 | 전통 관상가 말투 / 현대식 / 유머 모드 |
| O3 | 결과 다운로드 | `st.download_button`으로 결과 .txt 저장 |
| O4 | 궁합 보기 | 사진 2장으로 궁합 분석 |
| O5 | 스트리밍 출력 | `st.write_stream`으로 결과를 실시간 출력 |

## 6. 관상 분석 출력 형식

모델은 아래 구조의 한국어 Markdown으로 답한다.

```
## 🧑 전체 인상
## 👁️ 부위별 관상
- 이마 (초년운)
- 눈썹 (형제운·대인관계)
- 눈 (성격·지혜)
- 코 (재물운·중년운)
- 입·입술 (언변·식복)
- 귀 (복·수명)
- 턱·얼굴형 (말년운)
## 💰 재물운 / ❤️ 애정운 / 💼 직업운 / 🏥 건강운
## ✨ 종합 평가 및 한 줄 조언
```

### 프롬프트 원칙

- 역할: 경험 많은 관상 전문가. 따뜻하고 긍정적인 말투.
- 단점을 말할 때도 보완 방법과 함께 부드럽게 표현한다.
- 외모를 비하하거나 인종, 성별, 장애 등 민감한 속성을 근거로 판단하지 않는다.
- 실존 인물이 누구인지 추측하거나 밝히지 않는다.
- 얼굴이 없거나 여러 명이면 그 사실을 알리고 분석을 제한한다.

## 7. 비기능 요구사항

| 항목 | 요구사항 |
|---|---|
| 응답 시간 | 업로드부터 결과까지 평균 15초 이내 |
| 보안 | API 키는 코드나 Git에 절대 포함하지 않는다. `.env`는 `.gitignore`에 등록한다 |
| 개인정보 | 업로드한 이미지는 서버에 저장하지 않고 메모리에서만 처리한다. 화면에 안내 문구 표시 |
| 비용 | 이미지 리사이즈와 `detail` 옵션, `max_tokens` 제한으로 토큰 비용을 관리한다 |
| 호환성 | 데스크톱과 모바일 브라우저에서 모두 동작 |
| 언어 | UI와 결과 모두 한국어 |

## 8. 기술 스택

| 구분 | 기술 |
|---|---|
| 언어 | Python 3.10+ |
| 웹 프레임워크 | Streamlit |
| AI | `openai` Python SDK (Chat Completions, vision 입력) |
| 환경변수 | `python-dotenv` |
| 이미지 처리 | `Pillow` |
| 배포 | GitHub + Streamlit Community Cloud |

### requirements.txt

```
streamlit
openai
python-dotenv
Pillow
```

## 9. 환경변수 및 API 키 관리

### 9.1 로컬 개발: `.env`

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 9.2 Streamlit Cloud 배포: Secrets

Streamlit Cloud에는 `.env` 파일이 올라가지 않는다(`.gitignore` 처리). 그래서 앱 설정의 **Settings → Secrets**에 같은 값을 TOML 형식으로 입력한다.

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

### 9.3 키 로딩 로직

```python
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_secret(key, default=None):
    # 1순위: 환경변수(.env), 2순위: st.secrets(Streamlit Cloud)
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except Exception:
        return default
```

키가 없으면 앱에서 `st.error`로 설정 방법을 안내하고 `st.stop()`으로 멈춘다.

## 10. 프로젝트 구조

```
관상/
├── app.py               # Streamlit 메인 앱
├── prompts.py           # 시스템/사용자 프롬프트 정의
├── requirements.txt
├── .env                 # 로컬 전용 (Git 제외)
├── .env.example         # 키 형식 예시 (Git 포함)
├── .gitignore           # .env, .streamlit/secrets.toml, __pycache__/ 등
├── .streamlit/
│   └── config.toml      # (선택) 테마 설정
├── PRD.md
└── README.md
```

> 참고: Streamlit Cloud와 GitHub에서 문제가 생기지 않도록 **저장소 이름은 영문**(예: `ai-face-reading`)으로 짓는 것을 권장한다.

## 11. 화면 구성 (UI)

```
┌─────────────────────────────────────┐
│  🔮 AI 관상가                        │
│  사진 한 장으로 보는 나의 관상          │
├─────────────────────────────────────┤
│  [사이드바]                          │
│   - 사용 방법                        │
│   - 개인정보 안내                     │
│   - 면책 문구                        │
├─────────────────────────────────────┤
│  📤 얼굴 사진 업로드 (드래그 & 드롭)    │
│  ┌──────────┐                       │
│  │ 미리보기   │                       │
│  └──────────┘                       │
│        [ 🔍 관상 보기 ]               │
├─────────────────────────────────────┤
│  📜 관상 풀이 결과 (Markdown)          │
│  ⚠️ 재미로 보는 결과입니다              │
└─────────────────────────────────────┘
```

- `st.session_state`에 결과를 저장해서 화면이 다시 그려져도 결과가 남게 한다.
- 새 이미지를 올리면 이전 결과를 지운다.

## 12. 배포 절차

1. 로컬 테스트: `pip install -r requirements.txt` 후 `streamlit run app.py`
2. `.gitignore`에 `.env`가 있는지 확인한다.
3. GitHub에 새 저장소를 만들고 push한다.
4. [share.streamlit.io](https://share.streamlit.io)에 GitHub 계정으로 로그인한다.
5. **New app**에서 저장소, 브랜치(`main`), 메인 파일(`app.py`)을 선택한다.
6. **Advanced settings → Secrets**에 `OPENAI_API_KEY`와 `OPENAI_MODEL`을 입력한다.
7. **Deploy**를 누르고 배포된 URL에서 동작을 확인한다.

## 13. 예외 상황 처리

| 상황 | 처리 |
|---|---|
| API 키 없음 | 설정 방법을 안내하고 앱을 멈춤 |
| 지원하지 않는 파일 형식 | 업로더에서 차단 |
| 파일 용량 초과 | 경고 메시지 표시 |
| 얼굴 없음 / 여러 명 | 모델 응답을 그대로 안내하고 다른 사진 업로드 권유 |
| `RateLimitError` | "잠시 후 다시 시도해 주세요" |
| `AuthenticationError` | "API 키를 확인해 주세요" |
| 네트워크 / 기타 오류 | 일반 오류 메시지를 보여주고 상세 내용은 로그에만 기록 |
| 모델이 분석을 거부함 | 거부 메시지를 부드럽게 안내 |

## 14. 성공 기준

- [ ] 로컬에서 `.env`로 키를 읽어 이미지 분석 결과가 나온다.
- [ ] Streamlit Cloud에서 Secrets로 키를 읽어 동일하게 동작한다.
- [ ] `.env`가 GitHub 저장소에 올라가지 않는다.
- [ ] 얼굴 사진 업로드 후 15초 안에 구조화된 한국어 관상 결과가 나온다.
- [ ] 얼굴이 없는 사진에 적절한 안내가 나온다.
- [ ] 면책 문구와 개인정보 안내가 항상 보인다.

## 15. 개발 일정 (예시)

| 단계 | 작업 | 산출물 |
|---|---|---|
| 1 | 프로젝트 세팅, `.env`, 키 로딩 | 기본 구조 |
| 2 | 업로드, 전처리, OpenAI 호출 | 동작하는 MVP |
| 3 | 프롬프트 튜닝, 결과 UI 정리 | 완성된 결과 화면 |
| 4 | 예외 처리, 면책 문구 | 안정화 |
| 5 | GitHub push, Streamlit Cloud 배포 | 공개 URL |
