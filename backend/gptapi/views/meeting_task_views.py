"""
회의록에서 업무 추출 (비동기 AI + 동기 DB 처리)
- AI가 회의록을 분석하여 액션 아이템 추출 (Async)
- 추출된 업무를 DB에 일괄 생성 (Sync)
"""
import json
import logging
from datetime import datetime
import os
import traceback

import openai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from asgiref.sync import sync_to_async
from dotenv import load_dotenv

from db_model.models import Task, TaskManager, User, Project, Minutes
from log.views import create_log

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# 비동기 클라이언트 (AI 호출용)
client = openai.AsyncOpenAI(api_key=api_key)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Helper Functions (DB 조회용 - 비동기 래핑)
# -------------------------------------------------------------------------

@sync_to_async(thread_sensitive=True)
def get_minutes_content(minutes_id):
    try:
        minutes = Minutes.objects.get(pk=minutes_id)
        return minutes.content or minutes.script_text
    except Minutes.DoesNotExist:
        return None

@sync_to_async(thread_sensitive=True)
def get_team_members(project_id):
    try:
        project = Project.objects.get(pk=project_id)
        members = User.objects.filter(projectmember__project=project)
        return [{"name": m.name, "skills": m.skill.split(",") if m.skill else []} for m in members]
    except Project.DoesNotExist:
        return []

# -------------------------------------------------------------------------
# Views
# -------------------------------------------------------------------------

@csrf_exempt
async def extract_tasks_from_minutes(request):
    """
    회의록에서 업무 추출 (AI Async)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    
    try:
        data = json.loads(request.body)
        minutes_id = data.get('minutes_id')
        content = data.get('content')
        project_id = data.get('project_id')
        
        # 1. 회의록 내용 가져오기 (DB 조회)
        if minutes_id:
            db_content = await get_minutes_content(minutes_id)
            if db_content:
                content = db_content
            else:
                return JsonResponse({"error": "회의록을 찾을 수 없습니다."}, status=404)
        
        if not content or not content.strip():
            return JsonResponse({"error": "회의록 내용이 없습니다."}, status=400)
        
        # 2. 프로젝트 팀원 정보 가져오기 (DB 조회)
        team_members = []
        if project_id:
            team_members = await get_team_members(project_id)
        
        # 3. AI 프롬프트 구성
        prompt = f"""
        다음 회의록을 분석하여 실행 가능한 업무(Action Items)를 추출하세요.

        회의록:
        {content}

        프로젝트 팀원:
        {json.dumps(team_members, ensure_ascii=False)}

        출력 형식 (JSON):
        {{
            "tasks": [
                {{
                    "task_name": "업무명 (20자 이내, 명확하고 간결하게)", 
                    "description": "상세 설명 (2-3문장)",
                    "assignee": "담당자명 (회의록에 명시된 경우만, 없으면 null)",
                    "start_date": "시작일 (YYYY-MM-DD, 오늘 기준 합리적 추정)",
                    "end_date": "마감일 (YYYY-MM-DD, 시작일 + 3~7일 추정)",
                    "priority": "high/medium/low",
                    "subtasks": [
                        {{
                            "task_name": "하위 업무명 (20자 이내)", 
                            "description": "하위 업무 설명",
                            "assignee": "담당자명 또는 null",
                            "start_date": "YYYY-MM-DD",
                            "end_date": "YYYY-MM-DD",
                            "priority": "high/medium/low"
                        }}
                    ]
                }}
            ]
        }}

        추출 규칙:
        1. 명확한 액션 아이템만 추출 (토론 내용, 의견 교환은 제외)
        2. "~하기로 결정", "~를 진행", "~를 개발" 등 실행 동사가 있는 항목
        3. 담당자가 명시되지 않았으면 assignee: null
        4. 날짜가 없으면 오늘({datetime.now().strftime("%Y-%m-%d")}) 기준으로 합리적 추정
        5. 하나의 큰 업무는 2-4개의 하위 업무로 분해
        6. 우선순위는 긴급도와 중요도 기준으로 판단
        7. 최소 3개, 최대 8개의 상위 업무 추출
        8. ✅ **중요: 업무명은 반드시 20자 이내로 간결하게 작성**
        9. ✅ **긴 설명은 description에만 작성**

        JSON만 출력하고 다른 설명은 포함하지 마세요.
        """
        
        # 4. AI 호출 (Async)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 회의록 분석 및 업무 관리 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )
        
        result = response.choices[0].message.content
        
        # JSON 파싱 전처리
        if result.startswith("```"):
            lines = result.splitlines()
            if lines and lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            result = "\n".join(lines).strip()
        
        try:
            tasks_data = json.loads(result)
            return JsonResponse(tasks_data, status=200)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return JsonResponse({"error": "AI 응답 파싱 실패", "raw": result}, status=500)
    
    except Exception as e:
        logger.error(f"Extract Tasks Error: {e}")
        return JsonResponse({"error": str(e), "trace": traceback.format_exc()}, status=500)


@csrf_exempt
def bulk_create_tasks_from_minutes(request):
    """
    회의록에서 추출한 업무들을 DB에 일괄 생성 (Sync)
    - AI 호출이 없으므로 일반 동기 함수로 처리하여 트랜잭션 안전성 보장
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        tasks_data = data.get('tasks', [])
        user_id = data.get('user_id')
        # minutes_id = data.get('minutes_id') # 필요 시 사용
        
        if not project_id or not tasks_data:
            return JsonResponse({"error": "필수 정보 누락"}, status=400)
        
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return JsonResponse({"error": "프로젝트를 찾을 수 없습니다."}, status=404)
        
        # 로그인 사용자 확인
        log_user = None
        if user_id:
            try:
                log_user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                pass
        
        # 프로젝트 팀원 목록 캐싱
        project_members = {
            member.user.name: member.user 
            for member in TaskManager.objects.filter(project=project).select_related('user')
        }
        
        created_tasks = []
        
        # 트랜잭션 내에서 일괄 생성
        with transaction.atomic():
            for task_data in tasks_data:
                # task_name 길이 제한
                task_name = task_data['task_name'][:50] if len(task_data['task_name']) > 50 else task_data['task_name']
                
                # 상위 업무 생성
                task = Task.objects.create(
                    project=project,
                    task_name=task_name,
                    description=task_data.get('description'),
                    start_date=task_data.get('start_date'),
                    end_date=task_data.get('end_date'),
                    status='0',
                    parent_task=None
                )
                
                # 담당자 배정
                assignee_name = task_data.get('assignee')
                assignee = project_members.get(assignee_name)
                
                # 담당자 없으면 로그인 사용자로 배정 (옵션)
                if not assignee and log_user:
                    assignee = log_user
                
                if assignee:
                    TaskManager.objects.create(
                        task=task,
                        project=project,
                        user=assignee
                    )
                
                # 하위 업무 생성
                for subtask_data in task_data.get('subtasks', []):
                    subtask_name = subtask_data['task_name'][:50] if len(subtask_data['task_name']) > 50 else subtask_data['task_name']
                    
                    subtask = Task.objects.create(
                        project=project,
                        parent_task=task,
                        task_name=subtask_name,
                        description=subtask_data.get('description'),
                        start_date=subtask_data.get('start_date'),
                        end_date=subtask_data.get('end_date'),
                        status='0'
                    )
                    
                    sub_assignee_name = subtask_data.get('assignee')
                    sub_assignee = project_members.get(sub_assignee_name)
                    
                    if not sub_assignee and log_user:
                        sub_assignee = log_user
                    
                    if sub_assignee:
                        TaskManager.objects.create(
                            task=subtask,
                            project=project,
                            user=sub_assignee
                        )
                
                created_tasks.append(task)
                
                # 로그 기록 (로그 함수가 동기라면 여기서 호출 가능)
                if log_user:
                    create_log(
                        action="AI 업무 생성",
                        content=f"회의록에서 자동 생성: {task.task_name}",
                        user=log_user,
                        task=task
                    )
        
        return JsonResponse({
            "message": f"{len(created_tasks)}개 업무 생성 완료",
            "task_ids": [t.task_id for t in created_tasks]
        }, status=201)
    
    except Exception as e:
        logger.error(f"Bulk Create Tasks Error: {e}")
        return JsonResponse({"error": str(e), "trace": traceback.format_exc()}, status=500)