import json
import io
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from html2docx import html2docx
from docx import Document
from docx.oxml.ns import qn
# from db_model.models import Report  # Report 모델이 필요합니다.

# Report 모델이 아직 없으므로, 에러 방지를 위해 임시 처리
# 추후 Report 모델 생성 후 주석 해제 및 로직 활성화 필요
class ReportStub:
    objects = None

Report = ReportStub

@csrf_exempt
def save_report(request):
    if request.method != "POST": return JsonResponse({}, status=405)
    # 로직 생략 (모델 없음)
    return JsonResponse({"message": "Report logic pending"})

@csrf_exempt
def update_report(request, report_id):
    if request.method != "POST": return JsonResponse({}, status=405)
    return JsonResponse({"message": "Report logic pending"})

@csrf_exempt
def delete_report(request, report_id):
    if request.method != "DELETE": return JsonResponse({}, status=405)
    return JsonResponse({"message": "Report logic pending"})

def get_reports_by_project(request, project_id):
    return JsonResponse({"reports": []})

@csrf_exempt
def export_report_docx(request, report_id):
    return JsonResponse({"error": "Report logic pending"}, status=404)