import boto3
import urllib.parse
import logging
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from db_model.models import File
from comments.serializers import FileSerializer
from log.views import create_log

logger = logging.getLogger(__name__)

def get_s3_client():
    """S3 Client 생성 헬퍼 함수"""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

@api_view(["GET"])
def take_files(request):
    """프로젝트 내 파일 목록 조회"""
    project_id = request.GET.get("project_id")
    if not project_id:
        return Response({"error": "project_id required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # TaskManager를 통해 프로젝트와 연결된 파일들 조회 (중복 제거)
        files = File.objects.filter(
            task__taskmanager__project_id=project_id
        ).select_related('user', 'task').distinct().order_by("-created_date")
        
        return Response(FileSerializer(files, many=True).data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Take Files Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def download_files(request):
    """파일 다운로드용 Presigned URL 생성"""
    file_id = request.GET.get("file_id")
    if not file_id:
        return Response({"error": "file_id required"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        file_obj = get_object_or_404(File, pk=file_id)
        s3 = get_s3_client()
        
        # DB에 저장된 파일명(S3 Key) 사용
        # file_path가 있으면 그것을, 없으면 file_name 사용 (모델 구조에 따라 조정)
        key = file_obj.file_path if file_obj.file_path else file_obj.file_name
        
        # 한글 파일명 다운로드 처리 (RFC5987)
        quoted_name = urllib.parse.quote(file_obj.file_name, safe="")
        disposition = f"attachment; filename*=UTF-8''{quoted_name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
                "ResponseContentDisposition": disposition,
            },
            ExpiresIn=3600,
        )
        return Response({"url": url}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Download Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def file_upload(request):
    """업로드용 Presigned URL 생성 (comments 앱에서 이동됨)"""
    file_name = request.GET.get('file_name')
    file_type = request.GET.get('file_type')

    if not file_name or not file_type:
        return Response({"error": "file_name & file_type required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        s3 = get_s3_client()
        presigned_post = s3.generate_presigned_post(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_name,
            Fields={"Content-Type": file_type},
            Conditions=[{"Content-Type": file_type}],
            ExpiresIn=3600
        )
        return Response({'data': presigned_post}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Presigned Post Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def save_file_meta(request):
    """파일 메타데이터 DB 저장 (comments 앱에서 이동됨)"""
    serializer = FileSerializer(data=request.data)
    if serializer.is_valid():
        file_obj = serializer.save()
        
        # 로그 기록
        create_log(
            action="파일 업로드",
            content=file_obj.file_name,
            user=file_obj.user,
            task=file_obj.task
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def get_task_files(request):
    """특정 업무의 파일 목록 조회"""
    task_id = request.GET.get("task_id")
    if not task_id:
        return Response({"error": "task_id required"}, status=status.HTTP_400_BAD_REQUEST)

    files = File.objects.filter(task_id=task_id).select_related('user').order_by("created_date")
    return Response(FileSerializer(files, many=True).data)