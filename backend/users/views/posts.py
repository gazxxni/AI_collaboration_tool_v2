import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from db_model.models import Post

def get_posts(request):
    """전체 게시글 목록 조회"""
    try:
        # select_related로 JOIN 최적화
        posts = Post.objects.select_related('subject', 'author').order_by('-created_date')
        
        data = []
        for p in posts:
            # 날짜 데이터 안전 처리
            created = p.created_date.strftime("%Y-%m-%d %H:%M:%S") if p.created_date else ""
            
            # User 정보 안전 처리
            author_id = p.author.user_id if p.author else None
            
            data.append({
                "id": p.post_id,
                "subject_code": p.subject.subject_code if p.subject else "",
                "subject_name": p.subject.subject_name if p.subject else "Unknown",
                "title": p.title,
                "content": p.content,
                "author_id": author_id,
                "created_date": created
            })
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Post List Error: {e}")
        # 에러 메시지를 JSON으로 반환하여 프론트에서 확인 가능하게 함
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def save_post(request):
    """새 게시글 작성"""
    if request.method != "POST": return JsonResponse({}, status=405)
    try:
        data = json.loads(request.body)
        Post.objects.create(
            subject_id=data.get("subject_code"),
            title=data.get("title"),
            content=data.get("content"),
            author_id=data.get("user_id")
        )
        return JsonResponse({"message": "Saved"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def update_post(request, post_id):
    """게시글 수정"""
    if request.method != "POST": return JsonResponse({}, status=405)
    try:
        data = json.loads(request.body)
        Post.objects.filter(pk=post_id).update(
            title=data.get("title"), 
            content=data.get("content")
        )
        return JsonResponse({"message": "Updated"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def delete_post(request, post_id):
    """게시글 삭제"""
    if request.method != "DELETE": return JsonResponse({}, status=405)
    try:
        Post.objects.filter(pk=post_id).delete()
        return JsonResponse({"message": "Deleted"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)