from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt

from .serializers import ScheduleSerializer, TaskSerializer
from db_model.models import Schedule, Task, Project

@api_view(['POST'])
@csrf_exempt
def create_user_schedule(request):
    """개인 일정 생성"""
    user_id = request.session.get('user_id')
    if not user_id:
        return Response({"error": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

    # user_id를 serializer 저장 시점에 주입
    serializer = ScheduleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user_id=user_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@csrf_exempt
def get_user_schedules(request):
    """특정 사용자의 개인 일정 리스트 조회"""
    user_id = request.session.get('user_id')
    if not user_id:
        return Response({"error": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

    schedules = Schedule.objects.filter(user_id=user_id).order_by('start_time')
    serializer = ScheduleSerializer(schedules, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@csrf_exempt
def get_schedule_detail(request, schedule_id):
    """특정 일정 상세 조회"""
    schedule = get_object_or_404(Schedule, schedule_id=schedule_id)
    serializer = ScheduleSerializer(schedule)
    return Response(serializer.data)


@api_view(['DELETE'])
@csrf_exempt
def delete_schedule(request, schedule_id):
    """특정 일정 삭제"""
    schedule = get_object_or_404(Schedule, schedule_id=schedule_id)
    schedule.delete()
    return Response({"message": "Schedule deleted successfully"}, status=status.HTTP_200_OK)


@api_view(['PUT'])
@csrf_exempt
def update_schedule(request, schedule_id):
    """특정 일정 수정"""
    schedule = get_object_or_404(Schedule, schedule_id=schedule_id)
    serializer = ScheduleSerializer(schedule, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def task_list(request):
    """팀(프로젝트)별 업무 리스트 조회"""
    team_id = request.query_params.get('team_id')
    
    # team_id가 없거나 문자열 'null'인 경우 처리
    if not team_id or team_id == 'null':
        return Response([], status=status.HTTP_200_OK)
        # 또는 에러 메시지를 보내고 싶다면:
        # return Response({"error": "Invalid team_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # TaskManager를 통해 team_id와 연결된 Task들을 조회
        tasks = Task.objects.filter(taskmanager__project_id=team_id).distinct()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    except ValueError:
        # team_id가 숫자가 아닌 이상한 값일 경우
        return Response([], status=status.HTTP_200_OK)


@api_view(['GET'])
def tasks_for_user(request):
    """사용자가 속한 유효한 프로젝트의 모든 업무 조회"""
    user_id = request.session.get('user_id')
    if not user_id:
        return Response({"error": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
    
    # 유효한 프로젝트(이름이 있는) ID 목록
    valid_project_ids = Project.objects.exclude(project_name__isnull=True).values_list('project_id', flat=True)
    
    # 해당 프로젝트들에 포함된 업무 조회
    tasks = Task.objects.filter(
        taskmanager__project_id__in=valid_project_ids
    ).distinct()
    
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)