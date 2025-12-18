import json
import logging
from datetime import datetime
import os

import openai
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async
from django.utils import timezone
from dotenv import load_dotenv

from db_model.models import Project, Task, TaskManager, User, Report

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = openai.AsyncOpenAI(api_key=api_key)
logger = logging.getLogger(__name__)

# ==========================================
# 1. AI 보고서 생성 (비동기)
# ==========================================

@sync_to_async(thread_sensitive=True)
def get_project_data(project_id):
    try:
        project = Project.objects.get(pk=project_id)
        return project, project.project_name
    except Project.DoesNotExist:
        return None, None

@sync_to_async(thread_sensitive=True)
def get_task_info_str(project):
    """프로젝트의 모든 업무 정보를 문자열로 변환"""
    tasks = Task.objects.filter(taskmanager__project=project).distinct()
    
    info = ""
    if tasks.exists():
        info += "=== 업무 목록 ===\n"
        for task in tasks:
            tm = TaskManager.objects.filter(task=task, project=project).first()
            user_name = tm.user.name if tm and tm.user else "미배정"
            status_map = {'0': '요청', '1': '진행중', '2': '이슈/피드백', '3': '완료'}
            status = status_map.get(task.status, task.status)

            info += f"- 업무명: {task.task_name}\n"
            info += f"  담당자: {user_name} | 상태: {status}\n"
            info += f"  내용: {task.description}\n"
            info += "------------------------\n"
    else:
        info = "등록된 업무가 없습니다.\n"
    return info

@csrf_exempt
async def summarize_report(request):
    """주간 보고서 생성"""
    return await _generate_report(request, report_type="weekly")

@csrf_exempt
async def summarize_finalreport(request):
    """최종 보고서 생성"""
    return await _generate_report(request, report_type="final")

async def _generate_report(request, report_type="weekly"):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        today = data.get("today", datetime.now().strftime("%Y-%m-%d"))
        
        project, db_project_name = await get_project_data(project_id)
        if not project:
            return JsonResponse({"error": "Project not found"}, status=404)

        task_info_str = await get_task_info_str(project)

        if report_type == "weekly":
            prompt = f"""
            당신은 IT 프로젝트 매니저입니다. 아래 업무 데이터를 바탕으로 '주간 업무 보고서'를 작성하세요.
            [프로젝트]: {db_project_name}
            [작성일]: {today}
            [규칙]
            1. HTML 태그(<h2>, <h3>, <ul>, <li>, <b> 등)를 사용하여 가독성 있게 작성.
            2. '금주 진행 현황', '이슈 사항', '차주 계획', '종합 의견' 4가지 항목으로 구성.
            3. 없는 내용은 지어내지 말고 '특이사항 없음'으로 표기.
            [업무 데이터]
            {task_info_str}
            """
        else:
            prompt = f"""
            이 프로젝트는 컴퓨터공학과 캡스톤 디자인 프로젝트입니다.
            아래 업무 데이터를 분석하여 '최종 완료 보고서'를 HTML 형식으로 작성하세요.
            [프로젝트]: {db_project_name}
            [규칙]
            1. 서론(개요), 본론(설계 및 구현), 결론(성과) 구조로 작성.
            2. <h2>, <h3>, <p> 태그 필수 사용.
            3. 문체는 '~하였다' 체 사용.
            [업무 데이터]
            {task_info_str}
            """

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "너는 기술 문서 작성 전문가야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        summary = response.choices[0].message.content
        if summary.startswith("```"):
            summary = summary.replace("```html", "").replace("```", "").strip()

        return JsonResponse({"summary": summary})

    except Exception as e:
        logger.error(f"Report Gen Error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


# ==========================================
# 2. 보고서 CRUD (저장, 조회, 수정, 삭제)
# ==========================================
@csrf_exempt
def save_report(request):
    """보고서 저장"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requests only'}, status=405)

    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        title = data.get('title')
        content = data.get('content')

        # [디버깅 로그] 요청 데이터 확인
        print(f"🔴 [SAVE DEBUG] 요청 받음 - Project: {project_id}, User: {user_id}, Title: {title}")

        if not all([project_id, user_id, title, content]):
            print("🔴 [SAVE ERROR] 필수 데이터 누락")
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # DB 저장 시도
        report = Report.objects.create(
            project_id=project_id,
            user_id=user_id,
            title=title,
            content=content,
            created_date=timezone.now()
        )
        
        print(f"🟢 [SAVE SUCCESS] 보고서 저장 완료! ID: {report.report_id}")

        return JsonResponse({
            'message': 'Report saved successfully', 
            'report_id': report.report_id
        }, status=201)

    except Exception as e:
        print(f"❌ [SAVE EXCEPTION] 에러 발생: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def get_reports_by_project(request, project_id):
    """프로젝트별 보고서 목록 조회"""
    try:
        print(f"🔵 [GET DEBUG] 목록 조회 요청 - Project ID: {project_id}")
        
        # 프로젝트 ID로 필터링
        reports = Report.objects.filter(project_id=project_id).order_by('-created_date')
        count = reports.count()
        print(f"🔵 [GET DEBUG] 검색된 보고서 개수: {count}개")
        
        report_list = []
        for r in reports:
            report_list.append({
                'report_id': r.report_id,
                'title': r.title,
                'content': r.content,
                'created_date': r.created_date.isoformat() if r.created_date else None,
                'user_name': r.user.name if r.user else "Unknown"
            })
            
        return JsonResponse({'reports': report_list}, status=200)
    except Exception as e:
        print(f"❌ [GET EXCEPTION] 목록 조회 에러: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def update_report(request, report_id):
    """보고서 수정"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requests only'}, status=405)
    try:
        data = json.loads(request.body)
        report = Report.objects.get(pk=report_id)
        report.title = data.get('title', report.title)
        report.content = data.get('content', report.content)
        report.save()
        return JsonResponse({'message': 'Updated successfully'})
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_report(request, report_id):
    """보고서 삭제"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE requests only'}, status=405)
    try:
        report = Report.objects.get(pk=report_id)
        report.delete()
        return JsonResponse({'message': 'Deleted successfully'})
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def export_report_docx(request, report_id):
    """Word 다운로드"""
    try:
        from html2docx import html2docx
        report = Report.objects.get(pk=report_id)
        
        buf = html2docx(report.content, title=report.title)
        
        response = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{report.title}.docx"'
        return response
    except Exception as e:
        logger.error(f"Export Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)