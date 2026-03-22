import json
import logging
from datetime import datetime
import os

import openai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from asgiref.sync import sync_to_async
from dotenv import load_dotenv

from db_model.models import Project, Task, TaskManager, User, ProjectMember
from gptapi.utils import call_gpt_with_json_retry

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = openai.AsyncOpenAI(api_key=api_key)  # Async Client 사용

logger = logging.getLogger(__name__)

@sync_to_async(thread_sensitive=True)
def get_users_info(user_ids):
    # 비동기 환경에서 DB 조회를 위해 sync_to_async로 래핑
    users = list(User.objects.filter(user_id__in=user_ids))
    return [
        {"id": user.user_id, "name": user.name, "skills": user.skill.split(",") if user.skill else []}
        for user in users
    ]

@csrf_exempt
async def generate_high_level_tasks(request):
    # API Latency 해결을 위한 Async View 전환
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        project_topic = data.get("project_topic", "")
        project_description = data.get("project_description", "")
        project_goal = data.get("project_goal", "")
        tech_stack = data.get("tech_stack", [])
        start_date = data.get("project_start_date", "")
        end_date = data.get("project_end_date", "")
        selected_users = data.get("selected_users", [])

        user_data = await get_users_info(selected_users)

        prompt = f"""
        이 프로젝트는 컴퓨터공학과 대학생 팀이 수행하는 협업 프로젝트입니다.
        현실적이고 교육적인 목표와, 제한된 시간 내에 수행할 수 있는 업무 구조가 필요합니다.

        프로젝트 주제: {project_topic}
        프로젝트 설명: {project_description}
        프로젝트 목표 및 산출물: {project_goal}
        사용 기술 스택: {", ".join(tech_stack) if tech_stack else "지정되지 않음"}
        시작일: {start_date}
        종료일: {end_date}

        이 프로젝트에 참여할 팀원 정보:
        {json.dumps(user_data, ensure_ascii=False)}

        프로젝트 '{project_topic}'에 대한 주요 업무를 생성하세요.
        상위 업무는 최소 4개, 최대 6개를 제공해야 합니다.
        각 상위 업무마다 최소 3개, 최대 6개의 하위 업무를 포함해야 합니다.
        필요할 경우, 1개씩 초과해서 제안할 수 있습니다.
        반드시 JSON 형식만 출력하고, 불필요한 설명이나 텍스트는 포함하지 마세요.

        📌 **출력 조건**
        - 프로젝트 이름은 짧고 간결하게 만들 것. 단, 어떤 프로젝트인지 한번에 알아볼 수 있어야 함.
        - 상위 업무에는 '배정된 사용자'와 업무명이 포함됨
        - 하위 업무에는 '요구 스킬'이 포함됨 (배정된 사용자 포함)
        - 상위 업무와 하위 업무에는 업무별 적절한 '시작일'과 '종료일'이 포함되어야 함
        - 첫번째 상위업무 시작일은 {start_date}+1여야 하며, 마지막 상위업무 종료일은 {end_date}+1여야 함.
        - 이외의 시작일과 종료일은 전체 시작일과 종료일을 안에서 각 업무별로 적절하게 부여할 것
        - 조금씩은 겹칠 수 있으나, 완벽하게 겹치는 경우는 지양할 것
        - 반드시 JSON 형식으로 반환
        - 업무가 제일 많이 할당된 사람과 제일 적게 할당된 사람의 업무 개수 차이는 2개를 넘길 수 없음
        - 상위 업무에 배정된 사용자는 하위 업무에 배정된 사용자 중 한명이어야 함
        - 반드시 "프로젝트 이름"을 포함할 것
        - 발표를 **언급할 경우에만**, "발표자료"라는 상위 업무를 추가하고, 배정된 사용자와 요구 스킬을 포함할 것
        - 하위 업무는 최대한 상세하고 구체적으로 작성할 것.
        - 발표를 "제외한" 하위 업무의 경우 3개 이상으로 작성할 것. 발표 하위업무는 2개.
        - 아래 항목 중 단 하나라도 불명확하거나, 부실하거나, 컴퓨터공학과 대학생 팀 프로젝트의 범위로 부적절한 경우 전체 프로젝트를 무효로 판단해야 합니다.
            ① 프로젝트 이름
            ② 프로젝트 설명
            ③ 프로젝트 목표 및 산출물
        - 이 중 하나라도 조건을 충족하지 않으면 "프로젝트 이름": null 로 출력하고, "주요 업무"는 생략할 것.

        📌 유효성 검사
        - 프로젝트 입력 항목 중 하나라도 부적절한 경우, 전체 프로젝트를 무효로 판단해야 합니다.
        - 다음과 같이 "유효성" 키를 포함한 JSON을 출력하세요:

            예시:
            {{
            "유효성": {{
                "프로젝트 이름": true,
                "설명": true,
                "목표": false
            }},
            "프로젝트 이름": null
            }}

        조건:
        - 하나라도 false면 "프로젝트 이름"은 null 로 처리하세요.
        - "유효성" 키는 항상 포함하세요.
        - "주요 업무"는 유효성 검사를 통과한 경우에만 포함하세요.


        예시 출력:
        {{
        "프로젝트 이름": "파이썬으로 챗봇 개발",
        "주요 업무": [
            {{
            "업무명": "고객 응대 관리 시스템 개발",
            "배정된 사용자": "김철수",
            "시작일": "2025-04-10",
            "종료일": "2025-04-15",
            "하위업무": [
                {{
                "업무명": "챗봇 인터페이스 개발",
                "배정된 사용자": "김철수",
                "요구 스킬": ["Python", "Django"],
                "시작일": "2025-04-10",
                "종료일": "2025-04-12"
                }},
                {{
                "업무명": "고객 데이터 분석 기능 구현",
                "배정된 사용자": "박지훈",
                "요구 스킬": ["데이터 분석", "SQL"],
                "시작일": "2025-04-10",
                "종료일": "2025-04-12"
                }},
                {{
                "업무명": "챗봇 API 개발",
                "배정된 사용자": "김은비",
                "요구 스킬": ["FastAPI", "Python"],
                "시작일": "2025-04-12",
                "종료일": "2025-04-15"
                }}
            ]
            }},
            {{
            "업무명": "데이터베이스 설계 및 구축",
            "배정된 사용자": "박지훈",
            "시작일": "2025-04-16",
            "종료일": "2025-04-20",
            "하위업무": [
                {{
                "업무명": "ERD 설계 및 데이터 모델링",
                "배정된 사용자": "김은비",
                "요구 스킬": ["MySQL", "ERD"],
                "시작일": "2025-04-16",
                "종료일": "2025-04-17"
                }},
                {{
                "업무명": "테이블 생성",
                "배정된 사용자": "박지훈",
                "요구 스킬": ["쿼리 최적화", "인덱싱"],
                "시작일": "2025-04-17",
                "종료일": "2025-04-19"
                }},
                {{
                "업무명": "DB 성능 최적화",
                "배정된 사용자": "김은비",
                "요구 스킬": ["데이터 분석", "SQL"],
                "시작일": "2025-04-19",
                "종료일": "2025-04-20"
                }}
            ]
            }}
        ]
        }}
        """

        messages = [
            {"role": "system", "content": "당신은 프로젝트 관리 전문가입니다."},
            {"role": "user", "content": prompt}
        ]

        try:
            tasks_data = await call_gpt_with_json_retry(
                client, messages, temperature=0.1, max_tokens=3500
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "JSON 파싱 실패 (3회 재시도 후 최종 실패)"},
                status=500
            )

        validity = tasks_data.get("유효성", {})
        failed_fields = [field for field, valid in validity.items() if not valid]
        if failed_fields:
            return JsonResponse({
                "error": "입력 항목이 부적절합니다.",
                "invalid_fields": failed_fields
            }, status=400)

        return JsonResponse({
            "project_name": tasks_data.get("프로젝트 이름"),
            "tasks": tasks_data.get("주요 업무", [])
        })

    except Exception as e:
        logger.error(f"Generate Tasks Error: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def confirm_tasks(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        project_name = data.get("project_name")
        tasks = data.get("tasks", [])
        selected_users = data.get("selected_users", [])

        if not project_name or not tasks:
            return JsonResponse({"error": "필수 정보 누락"}, status=400)

        with transaction.atomic():
            project = Project.objects.create(project_name=project_name)
            
            user_ids = [int(uid) for uid in selected_users]
            users_map = {u.name: u for u in User.objects.filter(pk__in=user_ids)}
            
            for idx, uid in enumerate(user_ids):
                role = 1 if idx == 0 else 0
                try:
                    user_obj = User.objects.get(pk=uid)
                    ProjectMember.objects.create(
                        user=user_obj,
                        project=project,
                        role=role
                    )
                except User.DoesNotExist:
                    continue

            def save_task_recursive(task_data, parent=None):
                def _parse_date(ds):
                    if not ds: return None
                    try: return datetime.strptime(ds, "%Y-%m-%d")
                    except ValueError: return None

                start = _parse_date(task_data.get("시작일"))
                end = _parse_date(task_data.get("종료일"))
                
                new_task = Task.objects.create(
                    project=project,
                    task_name=task_data.get("업무명"),
                    description=json.dumps(task_data),
                    start_date=start,
                    end_date=end,
                    status='0', 
                    parent_task=parent
                )
                
                assignee_name = task_data.get("배정된 사용자")
                assignee = users_map.get(assignee_name)
                
                if assignee:
                    TaskManager.objects.create(
                        user=assignee,
                        project=project,
                        task=new_task
                    )
                
                for sub in task_data.get("하위업무", []):
                    save_task_recursive(sub, parent=new_task)

            for t in tasks:
                save_task_recursive(t)

        return JsonResponse({
            "message": "프로젝트 및 업무가 생성되었습니다.",
            "project_id": project.project_id
        }, status=201)

    except Exception as e:
        logger.error(f"Confirm Tasks Error: {e}")
        return JsonResponse({"error": str(e)}, status=500)