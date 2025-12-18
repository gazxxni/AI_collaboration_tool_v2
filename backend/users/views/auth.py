import json
import os
import boto3
from botocore.exceptions import NoCredentialsError

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response

from db_model.models import User
from users.serializers import UserSubjectSerializer

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    """사용자 로그인 처리 (세션 방식)"""
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            password = data.get('password')

            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                user = None

            if user and password == user.password:
                request.session['user_id'] = user.user_id
                request.session['name'] = user.name
                request.session.save()
                return JsonResponse({"message": f"환영합니다, {user.name}님!"}, status=200)
            
            return JsonResponse({"message": "아이디 혹은 비밀번호가 틀렸습니다."}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ChangePasswordView(View):
    """비밀번호 변경"""
    def patch(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

        try:
            data = json.loads(request.body)
            current_password = data.get("current_password")
            new_password = data.get("new_password")

            user = User.objects.get(pk=user_id)

            if user.password != current_password:
                 return JsonResponse({"error": "현재 비밀번호가 올바르지 않습니다."}, status=400)

            user.password = new_password 
            user.save()

            return JsonResponse({"message": "비밀번호가 변경되었습니다."}, status=200)
        except User.DoesNotExist:
            return JsonResponse({"error": "사용자를 찾을 수 없습니다."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

def get_user_name(request):
    """세션에 저장된 사용자 이름 반환"""
    name = request.session.get('name')
    user_id = request.session.get("user_id")
    if name:
        return JsonResponse({"name": name, "user_id": user_id}, status=200, json_dumps_params={'ensure_ascii': False})
    return JsonResponse({"message": "No session data"}, status=401)

@csrf_exempt
def get_users_list(request):
    """전체 사용자 목록 조회"""
    users = User.objects.all().values('user_id', 'name', 'profile_image')
    return JsonResponse(list(users), safe=False, json_dumps_params={'ensure_ascii': False})

@csrf_exempt
def get_user_profile(request):
    """현재 로그인한 사용자의 프로필 조회"""
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"message": "로그인이 필요합니다."}, status=401)

    try:
        user = User.objects.get(pk=user_id)
        data = {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "skill": user.skill if user.skill else "기술스택을 입력해주세요.",
            "profile_image": user.profile_image
        }
        return JsonResponse(data, json_dumps_params={'ensure_ascii': False})
    except User.DoesNotExist:
        return JsonResponse({"message": "사용자를 찾을 수 없습니다."}, status=404)

@csrf_exempt
def upload_profile_image(request):
    """프로필 이미지 S3 업로드"""
    if request.method != "POST":
        return JsonResponse({"message": "POST only"}, status=405)

    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"message": "로그인이 필요합니다."}, status=401)

    profile_image = request.FILES.get("profile_image")
    if not profile_image:
        return JsonResponse({"message": "이미지 파일 없음"}, status=400)

    try:
        file_extension = os.path.splitext(profile_image.name)[1]
        file_name = f"profile_images/user_{user_id}{file_extension}"

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        s3_client.upload_fileobj(
            profile_image,
            settings.AWS_STORAGE_BUCKET_NAME,
            file_name,
            ExtraArgs={'ContentType': profile_image.content_type}
        )

        image_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{file_name}"

        user = User.objects.get(pk=user_id)
        user.profile_image = image_url
        user.save()

        return JsonResponse({"message": "업로드 성공", "profile_image": image_url}, status=200)

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)

@csrf_exempt
def update_skill(request):
    """사용자 기술 스택 수정"""
    if request.method != "PATCH":
        return JsonResponse({"message": "PATCH only"}, status=405)
    
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"message": "Login required"}, status=401)

    try:
        data = json.loads(request.body)
        new_skill = data.get("skill")
        
        user = User.objects.get(pk=user_id)
        user.skill = new_skill
        user.save()
        
        return JsonResponse({"message": "기술 스택 업데이트 완료"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

class UserSubjectsAPIView(APIView):
    """사용자가 수강 중인 과목 조회"""
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        serializer = UserSubjectSerializer(user)
        return Response(serializer.data)