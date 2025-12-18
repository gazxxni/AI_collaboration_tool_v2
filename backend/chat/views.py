import json
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import localtime, make_aware, is_naive
from django.db.models import Q, Subquery, OuterRef
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt

from db_model.models import (
    User, Project, ProjectMember, Message, 
    DirectMessageRoom, DirectMessage
)

# 날짜 포맷팅 유틸리티 (USE_TZ 설정에 따라 안전하게 처리)
def safe_localtime(dt):
    if not dt:
        return None
    
    # USE_TZ = False(로컬 시간 사용)일 경우, 변환 없이 그대로 반환
    if not getattr(settings, 'USE_TZ', True):
        return dt

    # USE_TZ = True일 경우, Aware로 변환 후 Localtime 적용
    if is_naive(dt):
        try:
            dt = make_aware(dt)
        except Exception:
            return dt 
            
    return localtime(dt)

def format_dt(dt):
    ldt = safe_localtime(dt)
    return ldt.strftime('%m/%d %H:%M') if ldt else ""

def format_iso(dt):
    ldt = safe_localtime(dt)
    return ldt.isoformat() if ldt else ""

@api_view(['GET'])
def get_user_projects(request, user_id):
    """사용자가 참여 중인 프로젝트 목록 (최신 메시지 시간 포함)"""
    print(f"📡 API 요청됨: user_id={user_id}")
    
    # Subquery로 각 프로젝트의 최신 메시지 시간 가져오기
    latest_msg = Message.objects.filter(
        project=OuterRef('project_id')
    ).order_by('-created_date').values('created_date')[:1]
    
    projects = Project.objects.filter(
        projectmember__user_id=user_id
    ).annotate(
        latest_message_time=Subquery(latest_msg)
    ).values('project_id', 'project_name', 'latest_message_time')
    
    result = []
    for p in projects:
        # latest_message_time 포맷팅 (안전하게 처리)
        lmt = p['latest_message_time']
        formatted_time = None
        
        if lmt:
            ldt = safe_localtime(lmt)
            # ldt가 문자열일 수도 있고 datetime일 수도 있음 (USE_TZ=False인 경우)
            if isinstance(ldt, str):
                 formatted_time = ldt
            else:
                 formatted_time = ldt.strftime('%Y-%m-%d %H:%M:%S')
        
        result.append({
            "project_id": p['project_id'],
            "project_name": p['project_name'],
            "latest_message_time": formatted_time
        })
        
    if not result:
        return Response({"projects": []}, status=status.HTTP_200_OK)
        
    return Response({"projects": result})

@api_view(['GET'])
def get_project_messages(request, project_id):
    """프로젝트 채팅 메시지 조회"""
    messages = Message.objects.filter(project_id=project_id).select_related('user').order_by('created_date')
    
    data = []
    for m in messages:
        data.append({
            "message_id": m.message_id,
            "message": m.content,
            "timestamp": format_dt(m.created_date),
            "timestamp_iso": format_iso(m.created_date),
            "username": m.user.name,
            "user_id": m.user.user_id,
        })
        
    return Response({"messages": data})

@api_view(['GET'])
def get_project_name(request, project_id):
    """프로젝트 이름 조회"""
    project = get_object_or_404(Project, pk=project_id)
    return Response({"project_name": project.project_name})

# ===========================================
# DM (Direct Message)
# ===========================================

@api_view(['GET'])
def get_dm_rooms(request, user_id):
    """1:1 DM 방 목록 조회 (상대방 이름, 마지막 메시지 포함)"""
    
    # 내가 속한 방 찾기
    rooms = DirectMessageRoom.objects.filter(Q(user1_id=user_id) | Q(user2_id=user_id))
    
    data = []
    for room in rooms:
        # 상대방 ID 찾기
        partner_id = room.user2_id if room.user1_id == int(user_id) else room.user1_id
        partner = User.objects.filter(pk=partner_id).first()
        partner_name = partner.name if partner else "알 수 없음"
        
        # 마지막 메시지 가져오기
        last_msg = DirectMessage.objects.filter(room=room).order_by('-created_date').first()
        
        last_content = last_msg.content if last_msg else None
        
        # 날짜 포맷팅 (안전하게 처리)
        last_time_display = None
        last_time_iso = None
        
        if last_msg and last_msg.created_date:
            ldt = safe_localtime(last_msg.created_date)
            if isinstance(ldt, str):
                last_time_display = ldt
                last_time_iso = ldt
            else:
                last_time_display = ldt.strftime('%Y-%m-%d %H:%M:%S')
                last_time_iso = ldt.isoformat()
        
        data.append({
            "room_id": room.room_id,
            "partner_id": partner_id,
            "partner_name": partner_name,
            "last_message_id": last_msg.message_id if last_msg else None,
            "last_message": last_content,
            "latest_message_time": last_time_display,
            "latest_message_time_iso": last_time_iso
        })
        
    return Response({"dm_rooms": data})

@api_view(['POST'])
@csrf_exempt
def create_dm_room(request):
    """DM 방 생성 (이미 있으면 기존 방 ID 반환)"""
    try:
        me = int(request.data.get("user_id"))
        them = int(request.data.get("target_id"))
    except (TypeError, ValueError):
        return Response({"error": "Invalid user IDs"}, status=status.HTTP_400_BAD_REQUEST)

    if me == them:
        return Response({"error": "Cannot DM yourself"}, status=status.HTTP_400_BAD_REQUEST)

    # 작은 ID가 user1, 큰 ID가 user2가 되도록 정렬
    u1, u2 = sorted([me, them])
    
    room, created = DirectMessageRoom.objects.get_or_create(
        user1_id=u1, 
        user2_id=u2
    )
    
    return Response({"room_id": room.room_id}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_dm_messages(request, room_id):
    """DM 방 메시지 내역 조회"""
    messages = DirectMessage.objects.filter(room_id=room_id).select_related('user').order_by('created_date')
    
    data = []
    for m in messages:
        data.append({
            "message_id": m.message_id,
            "message": m.content,
            "timestamp": format_dt(m.created_date),
            "timestamp_iso": format_iso(m.created_date),
            "username": m.user.name,
            "user_id": m.user.user_id,
        })
        
    return Response({"messages": data})