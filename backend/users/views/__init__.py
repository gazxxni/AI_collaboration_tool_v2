# users/views/__init__.py

from .auth import (
    LoginView, ChangePasswordView, get_user_name, get_users_list, 
    get_user_profile, upload_profile_image, update_skill, UserSubjectsAPIView
)
from .posts import (
    get_posts, save_post, update_post, delete_post
)
from .minutes import (
    save_minutes, update_minutes, delete_minutes, get_minutes_by_project, export_minutes_docx
)
from .reports import (
    save_report, update_report, delete_report, get_reports_by_project, export_report_docx
)
from .dashboard import DashboardView, TaskDetailsView
from .notifications import NotificationsView
from .project import (
    ProjectLogsView, FavoriteToggleView, CurrentProjectGetView, CurrentProjectSetView,
    receive_project_data, get_latest_project_id
)