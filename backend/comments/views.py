import logging
from django.utils.timezone import now
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from db_model.models import Comment
from .serializers import CommentSerializer
from log.views import create_log

logger = logging.getLogger(__name__)

@api_view(['GET', 'POST'])
def comment_list_or_create(request):
    """댓글 조회 및 생성 API"""
    try:
        if request.method == 'GET':
            task_id = request.query_params.get('task_id')
            queryset = Comment.objects.all().select_related('user').order_by('-created_date')
            
            if task_id:
                queryset = queryset.filter(task_id=task_id)
            
            serializer = CommentSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == 'POST':
            # 데이터 준비
            data = request.data.copy()
            # data["created_date"] = now() # auto_now_add가 모델에 있다면 생략 가능

            # 사용자 정보 주입
            if request.user.is_authenticated:
                data["user"] = request.user.user_id
            elif not data.get("user"):
                return Response({"error": "Login required"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = CommentSerializer(data=data)
            if serializer.is_valid():
                comment = serializer.save()

                # 로그 기록
                create_log(
                    action="댓글 등록",
                    content=comment.content,
                    user=comment.user,
                    task=comment.task,
                    comment=comment
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Comment Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)