"""AI 관상가: 얼굴 사진을 업로드하면 관상을 풀이해 주는 Streamlit 앱."""

import base64
import hashlib
import io
import logging
import os
import re

import openai
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageOps, UnidentifiedImageError

from prompts import RESULT_MARKER, SYSTEM_PROMPT, USER_PROMPT

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("face_reading")

ALLOWED_TYPES = ["jpg", "jpeg", "png", "webp"]
DEFAULT_MODEL = "gpt-4o-mini"
MAX_FILE_SIZE_MB = 10  # .streamlit/config.toml의 server.maxUploadSize와 같게 유지
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_PIXELS = 40_000_000  # 픽셀 데이터를 읽기 전에 검사해 메모리 폭주와 크래시를 막는다
MAX_IMAGE_SIDE = 1024
PREVIEW_WIDTH = 260
DISCLAIMER = "⚠️ 재미로 보는 결과이며 과학적 근거가 없습니다."
PRIVACY_NOTICE = (
    "이 앱은 사진을 **저장하지 않습니다.** "
    "사진은 관상 분석을 위해 **OpenAI로 전송**되며, 화면을 닫으면 앱에서 사라집니다."
)


class ImageProcessingError(Exception):
    """업로드한 파일을 이미지로 처리할 수 없을 때 발생한다. 메시지는 사용자에게 그대로 보여준다."""


def get_secret(key, default=None):
    """설정값을 읽는다. 1순위: 환경변수(.env), 2순위: st.secrets(Streamlit Cloud)."""
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except Exception:
        return default


def check_api_key():
    """OPENAI_API_KEY가 없으면 설정 방법을 안내하고 앱 실행을 멈춘다."""
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        st.error(
            "OpenAI API 키가 설정되지 않았습니다.\n\n"
            "- **로컬 실행:** 프로젝트 폴더의 `.env` 파일에 "
            "`OPENAI_API_KEY=sk-...`를 추가하세요. (`.env.example` 참고)\n"
            "- **Streamlit Cloud:** 앱의 Settings → Secrets에 "
            '`OPENAI_API_KEY = "sk-..."`를 추가하세요.'
        )
        st.stop()
    return api_key


def init_session_state():
    """세션 상태 키를 초기화한다."""
    st.session_state.setdefault("result", None)  # 마지막 분석 결과 텍스트
    st.session_state.setdefault("error", None)  # 마지막 분석 오류 메시지
    st.session_state.setdefault("image_key", None)  # 현재 이미지의 sha256
    st.session_state.setdefault("source", "upload")  # 마지막으로 쓴 입력 방식
    st.session_state.setdefault("run_requested", False)  # 버튼 콜백이 세우는 분석 요청 플래그


# ---------------------------------------------------------------------------
# 이미지 처리 & 분석
# ---------------------------------------------------------------------------


def preprocess_image(file_bytes):
    """이미지를 검증·회전 보정·RGB 변환·축소한 뒤 JPEG base64 data URL로 반환한다."""
    unreadable = "이미지 파일을 열 수 없습니다. 손상되지 않은 JPG, PNG, WEBP 사진을 올려 주세요."
    too_large = "사진 해상도가 너무 큽니다. 더 작은 사진을 올려 주세요."
    try:
        image = Image.open(io.BytesIO(file_bytes))
    except Image.DecompressionBombError as exc:
        raise ImageProcessingError(too_large) from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageProcessingError(unreadable) from exc

    # Image.open은 헤더만 읽는다. 픽셀을 디코딩하기 전에 해상도를 검사한다.
    width, height = image.size
    if width * height > MAX_PIXELS:
        raise ImageProcessingError(too_large)

    try:
        image = ImageOps.exif_transpose(image)
        # 투명도가 있는 이미지는 흰 배경에 합성한다.
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageProcessingError(unreadable) from exc

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def analyze_face(api_key, model, image_data_url):
    """OpenAI 이미지 분석 모델에 사진을 보내 관상 풀이 텍스트를 받는다."""
    client = OpenAI(api_key=api_key)
    # temperature는 지정하지 않는다. 일부 모델(추론형 등)이 기본값 외의 값을 거부한다.
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url, "detail": "high"},
                    },
                ],
            },
        ],
        max_completion_tokens=1500,
    )
    message = response.choices[0].message
    if getattr(message, "refusal", None):
        return f"죄송합니다. 이 사진은 분석할 수 없습니다.\n\n{message.refusal}"
    return (message.content or "").strip()


def prepare_image(image_file):
    """입력 파일을 검증·전처리한다. 문제가 있으면 안내를 표시하고 None을 반환한다."""
    if image_file.size > MAX_FILE_SIZE:
        st.warning(f"파일이 너무 큽니다. {MAX_FILE_SIZE_MB}MB 이하의 사진을 올려 주세요.")
        return None
    try:
        return preprocess_image(image_file.getvalue())
    except ImageProcessingError as exc:
        st.error(str(exc))
    except Exception:
        logger.exception("이미지 전처리 중 알 수 없는 오류")
        st.error("사진을 처리하지 못했습니다. 다른 사진을 올려 주세요.")
    return None


def run_analysis(api_key, model, image_data_url):
    """분석을 실행해 (결과, 오류 메시지) 튜플을 반환한다. 상세 오류는 로그에만 남긴다."""
    try:
        result = analyze_face(api_key, model, image_data_url)
    except openai.AuthenticationError:
        logger.exception("OpenAI 인증 실패")
        return None, "API 키를 확인해 주세요. 키가 올바르지 않거나 만료되었습니다."
    except openai.RateLimitError:
        logger.exception("OpenAI 사용량 제한")
        return None, "요청이 많거나 사용 한도를 넘었습니다. 잠시 후 다시 시도해 주세요."
    except openai.APIConnectionError:
        logger.exception("OpenAI 연결 실패")
        return None, "AI 서버에 연결하지 못했습니다. 네트워크 상태를 확인하고 다시 시도해 주세요."
    except (openai.NotFoundError, openai.PermissionDeniedError, openai.BadRequestError):
        logger.exception("OpenAI 요청 거부 (모델 설정 확인 필요)")
        return None, (
            "AI 모델이 요청을 처리하지 못했습니다. 관리자는 OPENAI_MODEL 설정이 "
            "이미지 분석을 지원하는 모델인지 확인해 주세요."
        )
    except Exception:
        logger.exception("관상 분석 중 알 수 없는 오류")
        return None, "분석 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

    if not result:
        return None, "결과를 받지 못했습니다. 다시 시도해 주세요."
    return strip_preamble(result), None


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
.app-header { text-align: center; padding: 0.5rem 0 1.5rem; }
.app-header .app-icon { font-size: 3rem; line-height: 1; }
.app-header .app-title {
    font-size: clamp(2rem, 8vw, 2.8rem);
    font-weight: 700;
    margin: 0.3rem 0 0.2rem;
    background: linear-gradient(90deg, #F5D78E, #D4A84B, #B07A2A);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}
.app-header .app-subtitle { opacity: 0.75; font-size: 1.05rem; margin: 0; }
.photo-guide { opacity: 0.85; font-size: 0.92rem; margin-bottom: 0.5rem; }
</style>
"""

PHOTO_GUIDE = (
    '<p class="photo-guide">📸 <b>좋은 사진 가이드</b> · 정면 얼굴 · 밝은 조명 · '
    "한 명만 · 안경·모자 없이</p>"
)


def request_analysis():
    """버튼 콜백: 이번 실행에서 분석하도록 표시한다."""
    st.session_state.run_requested = True


def set_source(source):
    """입력 위젯 콜백: 가장 최근에 사용한 입력 방식(업로드/카메라)을 기억한다."""
    st.session_state.source = source


def render_header():
    """타이틀과 부제를 표시한다."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="app-header">'
        '<div class="app-icon">🔮</div>'
        '<h1 class="app-title">AI 관상가</h1>'
        '<p class="app-subtitle">사진 한 장으로 보는 나의 관상</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_sidebar(model):
    """사용 방법, 개인정보 안내, 면책 문구, 사용 모델을 사이드바에 표시한다."""
    with st.sidebar:
        st.header("📖 사용 방법")
        st.markdown(
            "1. 얼굴 사진을 **업로드**하거나 **카메라로 촬영**하세요.\n"
            "2. 미리보기를 확인하고 **관상 보기**를 누르세요.\n"
            "3. 잠시 기다리면 **관상 풀이**가 나옵니다."
        )
        st.header("🔒 개인정보 안내")
        st.markdown(PRIVACY_NOTICE)
        st.header("⚠️ 안내")
        st.markdown("재미로 보는 결과이며 **과학적 근거가 없습니다.**")
        st.divider()
        st.caption(f"🤖 사용 모델: `{model}`")


def render_inputs():
    """업로드/카메라 탭을 표시하고, 마지막으로 사용한 입력의 파일을 반환한다."""
    st.markdown(PHOTO_GUIDE, unsafe_allow_html=True)
    upload_tab, camera_tab = st.tabs(["📤 사진 업로드", "📷 카메라 촬영"])
    with upload_tab:
        uploaded = st.file_uploader(
            f"얼굴 사진을 올려 주세요 (JPG·PNG·WEBP, 최대 {MAX_FILE_SIZE_MB}MB)",
            type=ALLOWED_TYPES,
            key="upload_input",
            on_change=set_source,
            args=("upload",),
        )
    with camera_tab:
        captured = st.camera_input(
            "정면을 보고 촬영해 주세요",
            key="camera_input",
            on_change=set_source,
            args=("camera",),
        )

    # 탭은 둘 다 매번 렌더링되므로, 마지막에 쓴 입력을 우선하고 비어 있으면 다른 쪽을 쓴다.
    if st.session_state.source == "camera":
        return captured or uploaded
    return uploaded or captured


def reset_result_if_new_image(image_file):
    """입력 이미지가 바뀌면 이전 결과와 오류를 지운다."""
    image_key = None
    if image_file is not None:
        image_key = hashlib.sha256(image_file.getvalue()).hexdigest()
    if image_key != st.session_state.image_key:
        st.session_state.image_key = image_key
        st.session_state.result = None
        st.session_state.error = None


def render_preview(image_data_url):
    """전처리된 이미지를 가운데 정렬로 미리보기한다.

    st.columns는 모바일에서 세로로 쌓여 이미지가 화면 전체 폭으로 커지므로,
    가운데 정렬 컨테이너와 고정 폭을 쓴다.
    """
    with st.container(horizontal_alignment="center"):
        st.image(image_data_url, caption="미리보기", width=PREVIEW_WIDTH)


def is_reading(result):
    """응답이 관상 풀이인지(=전체 인상 제목이 있는지) 판단한다.

    안내 문장에도 '전체 인상'이라는 단어가 나올 수 있으므로 Markdown 제목 줄만 본다.
    """
    return _reading_heading(result) is not None


def _reading_heading(result):
    """'전체 인상' Markdown 제목 줄의 match 객체를 반환한다(없으면 None)."""
    pattern = rf"^[ \t]*#{{1,6}}\s.*{re.escape(RESULT_MARKER)}"
    return re.search(pattern, result, re.MULTILINE)


def strip_preamble(result):
    """관상 풀이 앞에 모델이 붙인 서두("사진 속 인물이 한 명…" 등)를 잘라낸다."""
    match = _reading_heading(result)
    return result[match.start():] if match else result


def render_result(busy):
    """결과(또는 안내), 다운로드·다시 보기 버튼, 면책 문구를 표시한다.

    busy가 True면 분석 중이므로 버튼을 비활성화해 중복 요청을 막는다.
    """
    if st.session_state.error:
        st.error(st.session_state.error)

    result = st.session_state.result
    if result and not is_reading(result):
        # 얼굴 없음·여러 명 등 풀이가 아닌 안내 응답
        st.info(result)
    elif result:
        st.header("📜 관상 풀이 결과")
        with st.container(border=True):
            st.markdown(result)
        download_col, retry_col = st.columns(2)
        with download_col:
            st.download_button(
                "📥 결과 저장 (.txt)",
                data=f"{result}\n\n{DISCLAIMER}\n",
                file_name="관상_결과.txt",
                mime="text/plain",
                width="stretch",
                disabled=busy,
            )
        with retry_col:
            st.button(
                "🔄 다시 보기",
                on_click=request_analysis,
                width="stretch",
                disabled=busy,
            )
    st.caption(DISCLAIMER)


def main():
    """앱 진입점."""
    st.set_page_config(page_title="AI 관상가", page_icon="🔮", layout="centered")
    init_session_state()
    model = get_secret("OPENAI_MODEL", DEFAULT_MODEL)
    render_header()
    render_sidebar(model)
    api_key = check_api_key()

    image_file = render_inputs()
    reset_result_if_new_image(image_file)

    image_data_url = None
    if image_file is not None:
        image_data_url = prepare_image(image_file)
        if image_data_url:
            render_preview(image_data_url)

    # 요청 플래그는 즉시 내린다. 분석 도중 사진을 바꿔 실행이 중단돼도 새 사진이 자동 분석되지 않게 한다.
    busy = bool(st.session_state.run_requested and image_data_url)
    st.session_state.run_requested = False

    st.button(
        "🔍 관상 보기",
        type="primary",
        width="stretch",
        disabled=image_data_url is None or busy,
        on_click=request_analysis,
    )
    status_area = st.container()
    render_result(busy)

    if busy:
        with status_area, st.spinner("관상을 보는 중입니다..."):
            result, error = run_analysis(api_key, model, image_data_url)
        st.session_state.error = error
        if result:  # 다시 보기가 실패해도 이전 결과는 남긴다.
            st.session_state.result = result
        # 비활성화했던 버튼을 되살리고 새 결과를 그리기 위해 다시 실행한다.
        st.rerun()


if __name__ == "__main__":
    main()
