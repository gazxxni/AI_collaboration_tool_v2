from django.urls import path
from .views import (
    transcribe_audio,
    summarize_meeting,
    generate_high_level_tasks,
    confirm_tasks,
    extract_tasks_from_minutes,
    # report_views에 통합된 함수들 import
    summarize_report,
    summarize_finalreport,
    save_report,
    get_reports_by_project,
    update_report,
    delete_report,
    export_report_docx,
)
from .views.meeting_task_views import bulk_create_tasks_from_minutes

urlpatterns = [
    # 회의록 관련
    path('transcribe/', transcribe_audio, name='transcribe_audio'),
    path('summarize/', summarize_meeting, name='summarize_meeting'),
    path('extract-tasks-from-minutes/', extract_tasks_from_minutes, name='extract_tasks_from_minutes'),
    path('bulk-create-tasks-from-minutes/', bulk_create_tasks_from_minutes, name='bulk_create_tasks_from_minutes'),

    # 업무 생성
    path('generate-tasks/', generate_high_level_tasks, name='generate_high_level_tasks'),
    path('confirm-tasks/', confirm_tasks, name='confirm_tasks'),

    # ==========================================
    # ✅ 보고서 관련 URL 통합 (모두 gptapi/ 경로 사용)
    # ==========================================
    # 1. AI 생성
    path('summarize-report/', summarize_report, name='summarize_report'),
    path('summarize-finalreport/', summarize_finalreport, name='summarize_finalreport'),
    
    # 2. CRUD 기능
    path('report/save/', save_report, name='save_report'),
    path('report/<int:project_id>/', get_reports_by_project, name='get_reports_by_project'),
    path('report/update/<int:report_id>/', update_report, name='update_report'),
    path('report/delete/<int:report_id>/', delete_report, name='delete_report'),
    path('report/html2docx/<int:report_id>/', export_report_docx, name='export_report_docx'),
]