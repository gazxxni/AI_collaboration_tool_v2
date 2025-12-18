"""
GPT API 관련 뷰 모듈
"""
from .minutes_views import transcribe_audio, summarize_meeting
from .task_views import generate_high_level_tasks, confirm_tasks
from .meeting_task_views import extract_tasks_from_minutes, bulk_create_tasks_from_minutes

# ✅ report_views에 있는 모든 함수(AI 생성 + CRUD)를 import 합니다.
from .report_views import (
    summarize_report,
    summarize_finalreport,
    save_report,
    get_reports_by_project,
    update_report,
    delete_report,
    export_report_docx
)

__all__ = [
    # 회의록
    'transcribe_audio',
    'summarize_meeting',
    
    # 업무 생성
    'generate_high_level_tasks',
    'confirm_tasks',
    
    # 회의록 -> 업무
    'extract_tasks_from_minutes',
    'bulk_create_tasks_from_minutes',

    # 보고서 (AI + CRUD)
    'summarize_report',
    'summarize_finalreport',
    'save_report',
    'get_reports_by_project',
    'update_report',
    'delete_report',
    'export_report_docx',
]