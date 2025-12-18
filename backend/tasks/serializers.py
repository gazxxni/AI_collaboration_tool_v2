# tasks/serializers.py
from rest_framework import serializers
from db_model.models import Task, TaskManager

class TaskSerializer(serializers.ModelSerializer):
    """
    업무(Task) Serializer
    - assignee: TaskManager를 통해 단일 담당자 이름 반환 (프론트엔드 호환)
    - assignees: TaskManager를 통해 모든 담당자 이름 리스트 반환
    """
    assignee = serializers.SerializerMethodField()
    assignees = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = '__all__'

    def get_assignee(self, obj):
        """
        단일 담당자 반환 (프론트엔드에서 task.assignee로 접근)
        TaskManager에서 첫 번째 담당자를 반환하거나 "미정" 반환
        """
        manager = TaskManager.objects.filter(task=obj).select_related('user').first()
        if manager and manager.user:
            return manager.user.name
        return "미정"

    def get_assignees(self, obj):
        """
        모든 담당자 리스트 반환 (다중 담당자 지원)
        """
        managers = TaskManager.objects.filter(task=obj).select_related('user')
        return [tm.user.name for tm in managers if tm.user]


class TaskNameSerializer(serializers.ModelSerializer):
    """업무명 업데이트용 간소화 Serializer"""
    class Meta:
        model = Task
        fields = '__all__'


class TaskManagerSerializer(serializers.ModelSerializer):
    """TaskManager (담당자 배정) Serializer"""
    class Meta:
        model = TaskManager
        fields = '__all__'