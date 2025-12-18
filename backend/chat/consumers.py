import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from django.utils.timezone import localtime, make_aware, is_naive
from channels.db import database_sync_to_async
from db_model.models import User, Project, Message, DirectMessage, DirectMessageRoom

# ── 공용 직렬화 유틸 ─────────────────────────────────────────
def serialize_message_obj(obj):
    """메시지 객체를 JSON 전송용 딕셔너리로 변환"""
    dt = obj.created_date
    if is_naive(dt):
        dt = make_aware(dt)
    ldt = localtime(dt)
    
    # obj.user는 ForeignKey이므로 User 객체임. User의 PK는 user_id
    user_id = obj.user.user_id if obj.user else None
    username = obj.user.name if obj.user else "알 수 없음"

    return {
        "message_id": obj.message_id if hasattr(obj, "message_id") else obj.id,
        "message": obj.content,
        "user_id": user_id,
        "username": username,
        "timestamp": f"{ldt.month}/{ldt.day} {ldt.strftime('%H:%M')}",  # 표시용
        "timestamp_iso": ldt.isoformat(),  # 정렬용
    }


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        kwargs = self.scope["url_route"]["kwargs"]
        
        # URL 파라미터에 따라 방 타입 결정
        if "project_id" in kwargs:
            self.room_type = "project"
            self.room_id = kwargs["project_id"]
            self.room_group_name = f"chat_{self.room_id}"
        else:
            self.room_type = "dm"
            self.room_id = kwargs["room_id"]
            self.room_group_name = f"dm_{self.room_id}"

        # 그룹 추가 및 접속 허용
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # 그룹에서 제거
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        temp_id = data.get("temp_id")  # 낙관적 업데이트용 임시 ID
        
        user_id = int(data.get("user_id"))
        message_content = (data.get("message") or "").strip()
        
        if not message_content:
            return

        # 사용자 조회
        user = await self.get_user(user_id)
        if not user:
            return

        # 메시지 저장 (DB)
        if self.room_type == "project":
            project = await self.get_project(self.room_id)
            if not project: return
            chat_obj = await self.save_message(user, project, message_content)
        else:
            dm_room = await self.get_dm_room(self.room_id)
            if not dm_room: return
            chat_obj = await self.save_dm_message(user, dm_room, message_content)

        # 저장된 메시지 직렬화
        payload = serialize_message_obj(chat_obj)
        if temp_id:
            payload["temp_id"] = temp_id

        # 그룹 내 모든 클라이언트에게 전송
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", **payload},
        )

    async def chat_message(self, event):
        # 이벤트 핸들러: 그룹에서 보낸 메시지를 WebSocket으로 전송
        # event에는 type 키가 포함되어 있으므로 제거하지 않고 전체를 보내거나 필요한 필드만 보냄
        # 여기서는 event 딕셔너리를 그대로 JSON으로 변환
        await self.send(text_data=json.dumps(event))

    # ── DB Async Helpers ─────────────────────────────────────
    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_project(self, project_id):
        return Project.objects.filter(pk=project_id).first()

    @database_sync_to_async
    def save_message(self, user, project, content):
        return Message.objects.create(
            user=user, 
            project=project, 
            content=content,
            created_date=timezone.now()
        )

    @database_sync_to_async
    def get_dm_room(self, room_id):
        return DirectMessageRoom.objects.filter(pk=room_id).first()

    @database_sync_to_async
    def save_dm_message(self, user, room, content):
        return DirectMessage.objects.create(
            user=user, 
            room=room, 
            content=content,
            created_date=timezone.now()
        )