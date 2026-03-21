"""
회의록 관련 뷰
- 음성 파일 STT 변환 (Faster-Whisper 로컬 모델 + Pyannote 화자 분리)
- 회의록 요약 및 포맷팅 (Async GPT-4o)
"""
import os
import asyncio
import tempfile
import json
import logging

import torch
import openai
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
hf_token = os.getenv("HF_TOKEN")

logger = logging.getLogger(__name__)

# API 키 확인
if not api_key:
    logger.error("OPENAI_API_KEY is missing in .env file")
if not hf_token:
    logger.warning("HF_TOKEN is missing — 화자 분리(Pyannote) 비활성화")

# GPT-4o 요약용 클라이언트 (유지)
client = openai.AsyncOpenAI(api_key=api_key)

# ── 로컬 STT/화자분리 모델 (지연 초기화) ──────────────────────────────────
_whisper_model = None
_diarization_pipeline = None

def _get_whisper() -> WhisperModel:
    """Faster-Whisper 모델 싱글턴 반환 (최초 1회만 로드)"""
    global _whisper_model
    if _whisper_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        model_size = "large-v3" if device == "cuda" else "small"
        logger.info(f"Faster-Whisper 로드: {model_size} / {device} / {compute_type}")
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _whisper_model

def _get_diarization():
    """Pyannote 파이프라인 싱글턴 반환 (HF_TOKEN 없으면 None)"""
    global _diarization_pipeline
    if _diarization_pipeline is None and hf_token:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Pyannote speaker-diarization-3.1 로드 중...")
        _diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )
        _diarization_pipeline.to(torch.device(device))
    return _diarization_pipeline

# ── 헬퍼 함수 ──────────────────────────────────────────────────────────────
def _assign_speaker(seg_start, seg_end, diar_result) -> str:
    """STT 세그먼트 시간 구간에 가장 많이 겹치는 화자를 반환"""
    speaker_times: dict[str, float] = {}
    for turn, _, speaker in diar_result.itertracks(yield_label=True):
        overlap = max(0, min(seg_end, turn.end) - max(seg_start, turn.start))
        if overlap > 0:
            speaker_times[speaker] = speaker_times.get(speaker, 0) + overlap
    return max(speaker_times, key=speaker_times.get) if speaker_times else "Unknown"


def _run_transcribe(audio_path: str, num_speakers: int | None) -> str:
    """
    동기 함수 — asyncio.to_thread()로 호출됨.
    Faster-Whisper STT + Pyannote 화자 분리를 결합해 타임스탬프 포함 텍스트 반환.
    """
    whisper = _get_whisper()
    segments, _ = whisper.transcribe(audio_path, language="ko")
    segments = list(segments)

    diarization = _get_diarization()
    if diarization:
        kwargs = {"num_speakers": num_speakers} if num_speakers else {}
        diar_result = diarization(audio_path, **kwargs)

        lines = []
        for seg in segments:
            speaker = _assign_speaker(seg.start, seg.end, diar_result)
            mm, ss = int(seg.start // 60), int(seg.start % 60)
            lines.append(f"[{mm:02d}:{ss:02d}] {speaker}: {seg.text.strip()}")
        return "\n".join(lines)
    else:
        # Pyannote 미설정 시 텍스트만 반환
        return " ".join(seg.text.strip() for seg in segments)

# ── [이전 코드] OpenAI Whisper API 방식 (주석 처리) ─────────────────────────
# client_old = openai.AsyncOpenAI(api_key=api_key)
#
# async def transcribe_audio_openai(request):
#     uploaded = request.FILES["audio"]
#     with open(audio_path, "rb") as af:
#         resp = await client_old.audio.transcriptions.create(
#             model="whisper-1",
#             file=af,
#             response_format="text",
#             language="ko"
#         )
#     transcript = resp if isinstance(resp, str) else getattr(resp, "text", "")
# ─────────────────────────────────────────────────────────────────────────────


@csrf_exempt
async def transcribe_audio(request):
    """음성 파일 STT 변환 (Faster-Whisper 로컬 모델 + Pyannote 화자 분리)"""
    if request.method != "POST" or "audio" not in request.FILES:
        return JsonResponse({"error": "audio 파일이 필요합니다."}, status=400)

    uploaded = request.FILES["audio"]
    audio_path = None
    tmp_created = False

    try:
        if hasattr(uploaded, "temporary_file_path"):
            audio_path = uploaded.temporary_file_path()
        else:
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in uploaded.chunks():
                    tmp.write(chunk)
            audio_path = tmp.name
            tmp_created = True

        # 화자 수 파라미터 (선택, 알 때만 전달)
        num_speakers_raw = request.POST.get("num_speakers")
        num_speakers = int(num_speakers_raw) if num_speakers_raw else None

        # 동기 STT 함수를 별도 스레드에서 실행 (비동기 뷰와 호환)
        transcript = await asyncio.to_thread(_run_transcribe, audio_path, num_speakers)

        return JsonResponse({"transcript": transcript})

    except Exception as e:
        logger.error(f"Transcribe Error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if tmp_created and audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


@csrf_exempt
async def summarize_meeting(request):
    """회의록 요약 및 HTML 포맷팅 (GPT-4o - Async)"""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        meeting_notes = data.get("notes", "")
        
        if not meeting_notes:
            return JsonResponse({"error": "회의록 내용이 없습니다."}, status=400)

        prompt = f"""
        이 프로젝트는 컴퓨터공학과 대학생 팀이 수행하는 협업 프로젝트입니다.

        1. 회의 대화 내용을 읽고, 아래 예시 회의록 형식에 맞춰 회의록을 작성할 것.
        2. 참석자 이름은 "참석자 1", "참석자 2" 등으로 고정.
        3. 회의 내용이 아닌 경우, 형식만 제공할 것.
        4. 일부만 제공되지 않은 경우 [예시]를 제공한 후, [예시]라고 표시할 것.
        5. 안건은 3개가 넘을 수 있음.
        6. 참석자 이름은 가나다 순으로 적을 것.
        7. html 문법 사용 필수. (h2, h3, p, ul, li 태그 등) 불필요한 줄바꿈 금지.

        <h1>회의 기본 정보</h1>
        <p><strong>회의명:</strong> [회의 제목]</p>
        <p><strong>일시:</strong> [회의 날짜와 시간]</p>
        <p><strong>장소:</strong> [회의 장소 또는 온라인 플랫폼]</p>
        <p><strong>참석자:</strong> [참석자 명단]</p>
        <p><strong>결석자:</strong> [결석자 명단]</p>

        <br>

        <h2>회의 목적 및 안건</h2>
        <p><strong>목적:</strong> [회의 목적]</p>
        <p>&bull; 안건 1</p>
        <p>&bull; 안건 2</p>
        <p>&bull; 안건 3</p>

        <br>

        <h2>회의 진행 내용</h2>
        <article>
            <h3>안건 1</h3>
            <p><strong>논의 내용:</strong> [논의 내용]</p>
            <p><strong>결정 사항:</strong> [결정 사항]</p>
        </article>
        <article>
            <h3>안건 2</h3>
            <p><strong>논의 내용:</strong> [논의 내용]</p>
            <p><strong>결정 사항:</strong> [결정 사항]</p>
        </article>
        <article>
            <h3>안건 3</h3>
            <p><strong>논의 내용:</strong> [논의 내용]</p>
            <p><strong>결정 사항:</strong> [결정 사항]</p>
        </article>

        <br>

        <h2>업무 할당</h2>
        <p>&bull; <strong>[담당자]:</strong> [기한]</p>

        <br>

        <h2>기타 참고 사항</h2>
        <p>[기타 추가 사항]</p>

        ## 회의록 내용:
        {meeting_notes}

        ## 출력 형식 (반드시 JSON)
        {{
        "유효성": {{
            "회의록 형식": true|false
            "회의록 내용": true|false
        }},
        "summary_html": "<h1>…</h1>…"
        }}

        📌 유효성 검사
        - "회의록 형식"은 최소한 질문·답변 형태가 담겨 있는지 확인합니다.
        - 회의록 내용이 불명확하거나, 컴퓨터공학과 대학생 팀 프로젝트의 범위로 부적절한 경우 전체 프로젝트를 무효로 판단해야 합니다.
        - false 면 user 가 수정할 수 있도록 유효성 결과만 돌려주세요.
        """

        # [수정] 모델명을 'gpt-4o'로 변경하여 호환성 문제 해결
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "너는 회의록 작성 전문가야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000,
        )
        
        raw = response.choices[0].message.content
        
        # 마크다운 코드 블록 제거
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines and lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            result = json.loads(raw)
            # 유효성 검사 (선택 사항)
            validity = result.get("유효성", {})
            if validity.get("회의록 형식") is False or validity.get("회의록 내용") is False:
                 return JsonResponse({"invalid": validity}, status=400)

            return JsonResponse({"summary_html": result.get("summary_html", "")}, status=200)
            
        except json.JSONDecodeError:
            logger.error(f"JSON Parse Error. Raw response: {raw}")
            return JsonResponse({"error": "GPT 응답 파싱 실패", "raw": raw}, status=500)

    except Exception as e:
        logger.error(f"Summarize Error: {e}")
        return JsonResponse({"error": str(e)}, status=500)