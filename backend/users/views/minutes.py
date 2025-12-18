import json
import io
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from html2docx import html2docx
from docx import Document
from docx.oxml.ns import qn
from db_model.models import Minutes

@csrf_exempt
def save_minutes(request):
    """회의록 저장"""
    if request.method != "POST": return JsonResponse({}, status=405)
    try:
        data = json.loads(request.body)
        Minutes.objects.create(
            title=data.get("title"),
            content=data.get("content"),
            user_id=data.get("user_id"),
            project_id=data.get("project_id", 1)
        )
        return JsonResponse({"message": "Saved"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def update_minutes(request, minutes_id):
    """회의록 수정"""
    if request.method != "POST": return JsonResponse({}, status=405)
    try:
        data = json.loads(request.body)
        Minutes.objects.filter(pk=minutes_id).update(
            title=data.get("title"),
            content=data.get("content")
        )
        return JsonResponse({"message": "Updated"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def delete_minutes(request, minutes_id):
    """회의록 삭제"""
    if request.method != "DELETE": return JsonResponse({}, status=405)
    try:
        Minutes.objects.filter(pk=minutes_id).delete()
        return JsonResponse({"message": "Deleted"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_minutes_by_project(request, project_id):
    """특정 프로젝트의 회의록 목록 조회"""
    minutes = Minutes.objects.filter(project_id=project_id).order_by('-created_date')
    data = [{
        "minutes_id": m.minutes_id,
        "title": m.title,
        "content": m.content,
        "created_date": m.created_date.strftime("%Y-%m-%d %H:%M")
    } for m in minutes]
    return JsonResponse({"minutes": data}, safe=False, json_dumps_params={'ensure_ascii': False})

@csrf_exempt
def export_minutes_docx(request, minutes_id):
    """회의록을 docx 파일로 변환하여 다운로드"""
    m = get_object_or_404(Minutes, pk=minutes_id)
    
    base_io = html2docx(m.content, m.title)
    base_io.seek(0)
    
    doc = Document(base_io)
    style = doc.styles['Normal']
    style.font.name = 'Malgun Gothic'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Malgun Gothic')
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{m.title}.docx"'
    return response