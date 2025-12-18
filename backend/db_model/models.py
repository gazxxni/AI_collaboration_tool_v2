from django.db import models
from django.utils import timezone

# ==============================================================================
# 1. 기초 정보 (Subject, User, Project)
# ==============================================================================

class Subject(models.Model):
    """학교 교과목 정보 관리"""
    subject_code = models.CharField(max_length=10, primary_key=True, db_column='subject_code')
    subject_name = models.CharField(max_length=100, db_column='subject_name')

    class Meta:
        db_table = 'Subject'

    def __str__(self):
        return self.subject_name


class User(models.Model):
    """사용자 정보 (기본 프로필, 기술 스택, 수강 과목)"""
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=5, unique=True)
    email = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=20)
    skill = models.CharField(max_length=255, blank=True, null=True)
    profile_image = models.CharField(max_length=500, blank=True, null=True)

    # 기존 DB 구조 유지를 위한 과목 컬럼 (최대 6개)
    subject1 = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subject1', related_name='users_subject1')
    subject2 = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subject2', related_name='users_subject2')
    subject3 = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subject3', related_name='users_subject3')
    subject4 = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subject4', related_name='users_subject4')
    subject5 = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subject5', related_name='users_subject5')
    subject6 = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, db_column='subject6', related_name='users_subject6')

    # Django ORM 활용을 위한 다대다 필드 (UserSubject 테이블 참조)
    subjects = models.ManyToManyField(Subject, through='UserSubject', related_name='users', blank=True, verbose_name='수강 과목들')

    class Meta:
        db_table = "User"

    def __str__(self):
        return self.name


class Project(models.Model):
    """프로젝트 기본 정보"""
    project_id = models.AutoField(primary_key=True)
    project_name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "Project"

    def __str__(self):
        return self.project_name


# ==============================================================================
# 2. 관계 테이블 (매핑 테이블)
# ==============================================================================

class UserSubject(models.Model):
    """사용자와 수강 과목 간의 다대다 연결"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='user_subject_links')
    subject = models.ForeignKey(Subject, on_delete=models.RESTRICT, db_column='subject_code', related_name='user_subject_links')

    class Meta:
        db_table = 'UserSubject'
        unique_together = (('user', 'subject'),)


class ProjectMember(models.Model):
    """프로젝트 참여 멤버 및 역할 관리"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column="project_id", null=True)
    role = models.IntegerField(default=0)  # 0: 일반 멤버, 1: 팀장/관리자

    class Meta:
        db_table = "ProjectMember"


class FavoriteProject(models.Model):
    """사용자의 즐겨찾기 프로젝트"""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id", related_name='favorite_projects')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column="project_id", related_name='favorited_by')

    class Meta:
        db_table = "FavoriteProject"
        unique_together = (("user", "project"),)


# ==============================================================================
# 3. 프로젝트 핵심 기능 (Task, Schedule, File, Post)
# ==============================================================================

class Task(models.Model):
    """프로젝트 업무(Task) 및 칸반 보드 아이템"""
    task_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column="project_id", null=True, blank=True)
    task_name = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)  # To Do, In Progress, Done 등
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(default=timezone.now)
    created_date = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    required_skills = models.TextField(null=True, blank=True)
    
    # 상위/하위 업무 관계 (Self Reference)
    parent_task = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_tasks", db_column="parent_task_id")

    class Meta:
        db_table = "Task"


class TaskManager(models.Model):
    """특정 업무(Task)의 담당자 배정"""
    tm_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column="project_id")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, db_column="task_id")

    class Meta:
        db_table = "TaskManager"
        unique_together = (('user', 'project', 'task'),)


class Schedule(models.Model):
    """개인 및 프로젝트 일정 (간트 차트용)"""
    schedule_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column="project_id", null=True, blank=True)
    title = models.CharField(max_length=255)
    start_time = models.DateField()
    end_time = models.DateField()
    location = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "Schedule"

    def __str__(self):
        return f"{self.title} ({self.start_time} ~ {self.end_time})"


class Post(models.Model):
    """커뮤니티/과목별 게시판 게시글"""
    post_id = models.AutoField(primary_key=True, db_column='post_id')
    subject = models.ForeignKey(Subject, to_field='subject_code', db_column='subject_code', on_delete=models.RESTRICT, related_name='posts')
    title = models.CharField(max_length=255, db_column='title')
    content = models.TextField(db_column='content')
    author = models.ForeignKey(User, to_field='user_id', db_column='user_id', on_delete=models.CASCADE, related_name='posts')
    created_date = models.DateTimeField(auto_now_add=True, db_column='created_date')

    class Meta:
        db_table = 'Post'
        verbose_name = '게시글'
        verbose_name_plural = '게시글 목록'
        indexes = [
            models.Index(fields=['subject'], name='idx_post_subject'),
            models.Index(fields=['author'],  name='idx_post_author'),
        ]

    def __str__(self):
        return f"[{self.subject.subject_code}] {self.title}"


class File(models.Model):
    """업무 또는 프로젝트 관련 파일 첨부"""
    file_id = models.AutoField(primary_key=True, db_column='file_id')
    file_name = models.CharField(max_length=255, db_column='file_name', null=True, blank=True)
    file_path = models.CharField(max_length=500, null=True)  # S3 파일 경로
    task = models.ForeignKey(Task, on_delete=models.CASCADE, db_column='task_id', null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='project_id', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    created_date = models.DateTimeField(db_column='created_date', auto_now_add=True)

    class Meta:
        db_table = 'File'


# ==============================================================================
# 4. 커뮤니케이션 (Chat, Comment, DM)
# ==============================================================================

class Message(models.Model):
    """프로젝트 내 전체 채팅 메시지"""
    message_id = models.AutoField(primary_key=True)
    content = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, to_field="user_id", on_delete=models.CASCADE)
    project = models.ForeignKey(Project, to_field="project_id", on_delete=models.CASCADE)

    class Meta:
        db_table = "Message"


class DirectMessageRoom(models.Model):
    """1:1 다이렉트 메시지 방"""
    room_id = models.AutoField(primary_key=True)
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dm_user1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dm_user2")

    class Meta:
        db_table = "DirectMessageRoom"
        unique_together = (("user1", "user2"),)


class DirectMessage(models.Model):
    """1:1 다이렉트 메시지 내용"""
    message_id = models.AutoField(primary_key=True)
    room = models.ForeignKey(DirectMessageRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.CharField(max_length=200)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "DirectMessage"


class Comment(models.Model):
    """업무(Task)에 대한 댓글"""
    comment_id = models.AutoField(primary_key=True, db_column='comment_id')
    content = models.CharField(max_length=200, db_column='content')
    created_date = models.DateTimeField(db_column='created_date', auto_now_add=True)
    task = models.ForeignKey(Task, db_column='task_id', to_field='task_id', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, to_field="user_id", on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        db_table = 'Comment'


# ==============================================================================
# 5. 로깅 및 AI 기능 (Log, Minutes)
# ==============================================================================

class Log(models.Model):
    """시스템 활동 로그 (업무 생성, 수정, 회의록 생성 등)"""
    log_id = models.AutoField(primary_key=True)
    created_date = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column='user_id')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, db_column='task_id')
    comment = models.ForeignKey(Comment, on_delete=models.SET_NULL, null=True, db_column='comment_id')

    class Meta:
        db_table = 'Log'


class Minutes(models.Model):
    """AI 회의록 (녹음 파일, STT, 요약본 포함)"""
    minutes_id = models.AutoField(primary_key=True)
    
    # 기존 레거시 필드
    title = models.CharField(max_length=20)
    content = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='project_id', related_name='minutes_project_set')
    
    # AI 기능을 위해 새로 추가된 필드
    audio_file = models.CharField(max_length=500, null=True, blank=True)  # 녹음 파일 경로 (S3)
    script_text = models.TextField(null=True, blank=True)                 # STT 변환 텍스트
    summary_text = models.TextField(null=True, blank=True)                # AI 요약 결과

    class Meta:
        db_table = 'minutes'
        
class Report(models.Model):
    report_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_column='project_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    title = models.CharField(max_length=255)
    content = models.TextField()  # HTML 내용 저장
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'report'