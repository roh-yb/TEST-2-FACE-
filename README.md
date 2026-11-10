# 🔮 AI 관상가

얼굴 사진을 업로드하거나 카메라로 촬영하면 OpenAI 이미지 분석 모델이 관상을 풀이해 주는 Streamlit 웹앱입니다.

> ⚠️ 재미로 보는 결과이며 과학적 근거가 없습니다.
> 🔒 이 앱은 사진을 저장하지 않습니다. 사진은 관상 분석을 위해 OpenAI로 전송됩니다.

## 주요 기능

- 📤 사진 업로드(JPG·PNG·WEBP, 최대 10MB) 또는 📷 카메라 촬영
- 📜 부위별 관상(이마·눈썹·눈·코·입·귀·턱), 운세(재물·애정·직업·건강), 종합 평가
- 얼굴이 없거나 여러 명이면 다시 올려 달라는 안내
- 📥 결과 저장(.txt), 🔄 같은 사진으로 다시 보기

## 파일 구성

| 파일 | 내용 |
|---|---|
| `app.py` | Streamlit 앱 (이미지 처리, OpenAI 호출, 화면) |
| `prompts.py` | 관상 풀이 프롬프트 |
| `.streamlit/config.toml` | 테마, 업로드 용량 제한, 오류 상세 숨김 |
| `.env.example` | 환경변수 예시 |
| `PRD.md` | 제품 요구사항 문서 |

## 로컬 실행

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

`.env.example`을 복사해 `.env`를 만들고 API 키를 넣습니다.

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini   # 생략하면 gpt-4o-mini
```

```bash
streamlit run app.py
```

## Streamlit Cloud 배포

1. `.env`가 `.gitignore`에 들어 있는지 확인한 뒤 GitHub 저장소에 push합니다. 저장소 이름은 영문을 권장합니다.
2. [share.streamlit.io](https://share.streamlit.io)에 GitHub 계정으로 로그인합니다.
3. **New app**에서 저장소, 브랜치(`main`), 메인 파일(`app.py`)을 선택합니다.
4. **Advanced settings → Secrets**에 아래 내용을 입력합니다.
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   ```
5. **Deploy**를 누릅니다.

`OPENAI_MODEL`을 바꿀 때는 이미지 입력을 지원하는 모델을 쓰세요. 지원하지 않는 모델이면 앱이 설정을 확인하라고 안내합니다.
