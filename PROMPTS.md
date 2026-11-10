# 단계별 개발 프롬프트

> 각 단계 프롬프트를 순서대로 Claude Code에 붙여넣어 사용하세요.
> 한 단계가 끝나면 직접 실행해 보고 확인한 뒤 다음 단계로 넘어가세요.

---

## 1단계: 기본 뼈대 작성

```
PRD.md를 꼼꼼히 읽고, PRD 10장 "프로젝트 구조"에 맞춰 프로젝트 기본 뼈대를 만들어줘.

[만들 파일]
1. requirements.txt: streamlit, openai, python-dotenv, Pillow
2. .gitignore: .env, .streamlit/secrets.toml, __pycache__/, *.pyc, .venv/, venv/
3. .env.example: OPENAI_API_KEY=sk-your-key-here, OPENAI_MODEL=gpt-4o-mini
4. .env: .env.example과 같은 형식 (실제 키는 내가 직접 넣을게)
5. prompts.py: 아직 비워두고 SYSTEM_PROMPT, USER_PROMPT 변수만 placeholder로 선언
6. app.py:
   - st.set_page_config(페이지 제목 "AI 관상가", 아이콘 🔮, layout="centered")
   - PRD 9.3의 get_secret() 함수 구현 (1순위 os.getenv / .env, 2순위 st.secrets)
   - OPENAI_API_KEY가 없으면 st.error로 설정 방법(.env 또는 Streamlit Secrets)을 안내하고 st.stop()
   - 타이틀, 부제, 이미지 업로더(jpg/jpeg/png/webp), 미리보기, "관상 보기" 버튼까지만 배치
   - 버튼을 누르면 아직은 "분석 기능 준비 중" 메시지만 출력
7. README.md: 프로젝트 소개, 로컬 실행 방법, Streamlit Cloud 배포 방법(PRD 12장) 요약

[조건]
- 아직 OpenAI API는 호출하지 마.
- 함수 단위로 나눠서 2단계에서 기능을 붙이기 쉽게 구조를 잡아줘.
- 끝나면 가상환경을 만들고 패키지를 설치한 뒤 `streamlit run app.py`가 오류 없이 뜨는지 확인해줘.
```

---

## 2단계: 주요 기능 추가

```
PRD.md의 5.1 필수 기능(F1~F8), 6장 출력 형식, 13장 예외 처리를 기준으로 app.py와 prompts.py에 핵심 기능을 구현해줘.

[구현 내용]
1. 이미지 검증 (F1)
   - 업로드 파일이 10MB를 넘으면 st.warning을 띄우고 중단
2. 이미지 전처리 (F3) – preprocess_image() 함수
   - Pillow ImageOps.exif_transpose로 회전 보정
   - RGB 변환 (PNG 투명도, RGBA 대응)
   - 긴 변을 최대 1024px로 축소 (비율 유지)
   - JPEG로 저장 후 base64 data URL(data:image/jpeg;base64,...)로 반환
3. 프롬프트 작성 (prompts.py)
   - SYSTEM_PROMPT: PRD 6장 "프롬프트 원칙"을 모두 반영 (따뜻하고 긍정적인 관상 전문가, 외모 비하·민감 속성 판단 금지, 실존 인물 추측 금지, 얼굴이 없거나 여러 명이면 그 사실을 알리고 분석 제한)
   - USER_PROMPT: PRD 6장의 Markdown 출력 구조를 그대로 따르도록 지시, 한국어로 답변
4. OpenAI 호출 (F4) – analyze_face() 함수
   - openai SDK의 OpenAI 클라이언트와 chat.completions.create 사용
   - 모델은 get_secret("OPENAI_MODEL", "gpt-4o-mini")
   - messages에 system 프롬프트 + user(text + image_url, detail="high") 전달
   - max_tokens 약 1500, temperature 0.8
5. 결과 표시 (F5)
   - st.spinner("관상을 보는 중입니다...") 동안 호출
   - 결과를 st.session_state에 저장해서 rerun 이후에도 유지
   - 새 이미지를 업로드하면 이전 결과 초기화 (파일 이름+크기 등으로 변경 감지)
   - st.markdown으로 결과 출력
6. 예외 처리 (F6, F7) – PRD 13장 표 기준
   - openai.AuthenticationError → "API 키를 확인해 주세요"
   - openai.RateLimitError → "잠시 후 다시 시도해 주세요"
   - openai.APIConnectionError, APIError, 기타 Exception → 일반 오류 메시지 (상세 내용은 logging으로만 기록하고 화면에는 노출하지 않음)
   - Pillow가 열 수 없는 파일(UnidentifiedImageError) 처리
7. 면책 문구 (F8)
   - 결과 아래에 "재미로 보는 결과이며 과학적 근거가 없습니다" 항상 표시
8. 결과 다운로드 (O3)
   - st.download_button으로 결과를 .txt로 저장

[조건]
- API 키나 민감 정보가 로그나 화면에 출력되지 않게 해줘.
- 함수마다 짧은 docstring을 달아줘.
- 끝나면 python -m py_compile로 문법을 확인하고, 앱을 실행해 오류 없이 뜨는지 확인해줘.
```

---

## 3단계: UI 디자인

```
PRD.md 11장 "화면 구성"을 기준으로 app.py의 UI를 보기 좋게 다듬어줘. 기능 로직은 바꾸지 마.

[디자인 요구사항]
1. 테마 (.streamlit/config.toml)
   - 신비롭고 동양적인 느낌: 짙은 남색이나 먹색 배경, 금색 포인트 컬러
   - primaryColor, backgroundColor, secondaryBackgroundColor, textColor, font 지정
2. 헤더
   - 🔮 아이콘과 "AI 관상가" 큰 타이틀, "사진 한 장으로 보는 나의 관상" 부제
   - st.markdown + 간단한 CSS(unsafe_allow_html)로 가운데 정렬과 그라데이션 텍스트
3. 사이드바
   - 📖 사용 방법 (3단계 안내)
   - 🔒 개인정보 안내 ("업로드한 사진은 저장되지 않고 분석 후 바로 사라집니다")
   - ⚠️ 면책 문구
   - 현재 사용 중인 모델 이름 표시
4. 업로드 영역
   - 좋은 사진 가이드: 정면, 밝은 조명, 한 명만, 안경·모자 없이
   - 미리보기는 적당한 크기로 가운데 정렬 (st.columns 활용)
   - "관상 보기" 버튼은 use_container_width=True로 크게, type="primary"
   - 이미지를 올리기 전에는 버튼 비활성화
5. 결과 영역
   - st.container(border=True) 카드 안에 결과 표시
   - 결과 위에 "📜 관상 풀이 결과" 소제목
   - 다운로드 버튼과 "다시 보기" 버튼을 나란히 배치
   - 면책 문구는 st.caption 또는 st.info로 눈에 띄지만 과하지 않게
6. 모바일 대응
   - 좁은 화면에서도 가로 스크롤이 생기지 않게 (columns 비율, 이미지 width 확인)
7. (선택) PRD O1 카메라 촬영
   - st.tabs로 "📤 사진 업로드" / "📷 카메라 촬영" 탭을 나누고, 둘 다 같은 분석 함수 사용

[조건]
- CSS는 꼭 필요한 만큼만 쓰고, Streamlit 버전이 바뀌어도 쉽게 깨지지 않는 선택자를 써줘.
- 끝나면 앱을 실행해서 화면이 깨지지 않는지 확인해줘.
```

---

## 4단계: PRD 기준 검토 및 버그 점검 (Playwright 활용)

```
지금까지 만든 앱이 PRD.md대로 개발됐는지, 문제나 버그가 없는지 자세히 검토해줘.
코드 리뷰와 Playwright 브라우저 테스트를 둘 다 해줘.

[A. 코드 정적 검토]
1. PRD 5.1 F1~F8, 6장, 7장, 9장, 13장 항목별로 구현 여부를 하나씩 확인
2. 보안
   - .env가 .gitignore에 있는지
   - API 키가 코드, 로그, 화면에 노출되는 곳이 없는지
   - `git status`나 파일 목록 기준으로 커밋하면 안 되는 파일이 있는지
3. 버그 가능성
   - session_state 초기화 누락, rerun 때 결과가 사라지거나 중복 호출되는 문제
   - 새 이미지 업로드 시 이전 결과가 남는 문제
   - PNG 투명도, 세로 사진 EXIF 회전, 아주 큰 이미지나 아주 작은 이미지 처리
   - 예외 처리에서 빠진 경우
4. Streamlit Cloud 배포 문제
   - requirements.txt 누락 패키지
   - st.secrets 접근 시 secrets.toml이 없을 때 에러 나는지
   - 한글 경로나 파일명 문제

[B. Playwright 브라우저 테스트]
1. 백그라운드에서 `streamlit run app.py --server.headless true --server.port 8501` 실행
2. Playwright로 http://localhost:8501 접속 후 스크린샷
3. 테스트용 이미지 준비 (scratchpad 폴더에 Pillow로 생성)
   - 얼굴이 없는 단색 또는 풍경 이미지 (PNG)
   - 투명 배경 PNG
   - 10MB가 넘는 이미지
   - 확장자만 jpg인 텍스트 파일 (손상 파일)
   - (내가 얼굴 사진을 주면 그것도 사용)
4. 시나리오별 테스트 (각 단계 스크린샷 + 콘솔 에러 확인)
   - 첫 화면: 타이틀, 사이드바, 면책 문구, 개인정보 안내가 보이는지
   - 이미지 업로드 전 버튼 비활성화 여부
   - 업로드 → 미리보기 → 관상 보기 → 결과 표시까지 정상 동작 (실제 API 호출)
   - 결과가 PRD 6장 구조(전체 인상, 부위별 관상, 운세, 종합 평가)를 따르는지
   - 얼굴 없는 이미지에 안내가 제대로 나오는지
   - 용량 초과 파일, 손상 파일 처리
   - 다른 이미지로 교체 시 이전 결과가 초기화되는지
   - 다운로드 버튼 동작
   - 모바일 화면(390x844)으로 리사이즈해서 레이아웃 깨짐이나 가로 스크롤 확인
   - API 키가 없을 때의 안내 화면 (환경변수를 비우고 별도 포트로 실행해서 확인)
5. 응답 시간 측정: PRD 7장 기준(15초 이내) 충족 여부

[C. 결과 보고]
- PRD 항목별 체크리스트 표 (✅ 충족 / ⚠️ 부분 충족 / ❌ 미충족 + 근거)
- 발견한 버그와 문제점: 심각도(높음/중간/낮음), 재현 방법, 원인, 수정 방안
- 주요 화면 스크린샷 경로
- 검토가 끝나면 바로 고치지 말고 목록부터 보여줘. 내가 확인한 뒤 수정을 진행할게.
- 테스트가 끝나면 Streamlit 서버와 브라우저를 종료해줘.
```
