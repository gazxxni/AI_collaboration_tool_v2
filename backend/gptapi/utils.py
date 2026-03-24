"""
GPT API 공통 유틸리티
- response_format으로 JSON 출력 강제
- JSON 파싱 실패 시 재시도 로직 (안전장치)
"""
import json
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def strip_markdown_codeblock(text: str) -> str:
    """GPT가 ```json ... ``` 으로 감싸는 경우 제거"""
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


async def call_gpt_with_json_retry(client, messages, *, model="gpt-4o",
                                    temperature=0.3, max_tokens=4000,
                                    max_retries=MAX_RETRIES):
    """
    GPT API를 호출하고 JSON 파싱을 시도합니다.
    - response_format=json_object로 JSON 출력을 API 레벨에서 강제
    - 그래도 파싱 실패 시 최대 max_retries회 재시도 (안전장치)

    Returns:
        dict: 파싱된 JSON 객체

    Raises:
        json.JSONDecodeError: max_retries회 모두 실패 시
    """
    last_raw = ""

    for attempt in range(1, max_retries + 1):
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        raw = strip_markdown_codeblock(raw)
        last_raw = raw

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if attempt < max_retries:
                logger.warning(
                    f"JSON 파싱 실패 (시도 {attempt}/{max_retries}), 재시도..."
                )
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content":
                     "출력이 유효한 JSON 형식이 아닙니다. "
                     "반드시 JSON 형식으로만 다시 출력해주세요. "
                     "불필요한 텍스트나 설명 없이 JSON만 출력하세요."},
                ]
            else:
                logger.error(
                    f"JSON 파싱 최종 실패 ({max_retries}회 시도). Raw: {raw}"
                )
                raise

    # 도달 불가하지만 안전장치
    raise json.JSONDecodeError("Max retries exceeded", last_raw, 0)
