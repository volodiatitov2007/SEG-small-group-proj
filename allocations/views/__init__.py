"""The views of the application.

The views are grouped into modules. They are all imported here, so that
other code can keep using them as views.home, views.user_list, and so on.
"""

from .session_views import dashboard, home, log_in, log_out
from .user_management_views import (
    password,
    profile,
    superuser_required,
    user_create,
    user_delete,
    user_detail,
    user_list,
    user_update,
)
