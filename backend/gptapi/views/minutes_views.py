"""
회의록 관련 뷰
- 음성 파일 STT 변환 (Async Whisper)
- 회의록 요약 및 포맷팅 (Async GPT-4o)
"""
import os
import tempfile
import json
import logging

import openai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# API 키 확인
if not api_key:
    logger = logging.getLogger(__name__)
    logger.error("OPENAI_API_KEY is missing in .env file")

client = openai.AsyncOpenAI(api_key=api_key)

logger = logging.getLogger(__name__)


@csrf_exempt
async def transcribe_audio(request):
    """음성 파일 STT 변환 (Whisper API - Async)"""
    if request.method != "POST" or "audio" not in request.FILES:
        return JsonResponse({"error": "audio 파일이 필요합니다."}, status=400)

    uploaded = request.FILES["audio"]
    audio_path = None
    
    try:
        if hasattr(uploaded, "temporary_file_path"):
            audio_path = uploaded.temporary_file_path()
        else:
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in uploaded.chunks():
                    tmp.write(chunk)
            audio_path = tmp.name

        # Whisper 모델 호출
        with open(audio_path, "rb") as af:
            resp = await client.audio.transcriptions.create(
                model="whisper-1",
                file=af,
                response_format="text",
                language="ko"
            )
        
        transcript = resp if isinstance(resp, str) else getattr(resp, "text", "")
        return JsonResponse({"transcript": transcript})
        
    except Exception as e:
        logger.error(f"Transcribe Error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if audio_path and not hasattr(uploaded, "temporary_file_path") and os.path.exists(audio_path):
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