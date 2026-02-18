# ==========================================
# File: task_instance_service.py
# Updated in iteration: 4
# Author: Karl Concha
#
# Service layer for managing TaskInstance lifecycle during runtime.
#
# Date: January 2026
# ==========================================

from datetime import datetime, timedelta

from dao.task_instance_dao import TaskInstanceDAO
from model.task_instance import TaskInstance


DEFAULT_TTL_SECONDS = 15 * 60


class TaskInstanceService:
    """Service layer for managing TaskInstance runtime execution."""

    def __init__(self):
        self.dao = TaskInstanceDAO()

    def create_task_instance(self, process_id_fk, taskdef_id_fk, status, run_folder):
        """Creates a new TaskInstance entry."""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=DEFAULT_TTL_SECONDS)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        new_instance = TaskInstance(
            TaskInstance_ID=None,
            Process_ID_FK=process_id_fk,
            TaskDef_ID_FK=taskdef_id_fk,
            Status=status,
            Run_Folder=run_folder,
            Last_Accessed_At=now_str,
            Expires_At=expires_str,
            Deleted_At=None,
            Downloaded_At=None,
            Created_At=None,
            Updated_At=None
        )
        return self.dao.create_task_instance(new_instance)

    def get_task_instance(self, task_instance_id):
        """Retrieves a TaskInstance by ID."""
        return self.dao.get_task_instance_by_id(task_instance_id)

    def list_task_instances(self):
        """Returns all TaskInstances (newest first)."""
        return self.dao.get_all_task_instances()

    def update_run_folder(self, task_instance_id, run_folder):
        """Updates the on-disk run folder path."""
        return self.dao.update_run_folder(task_instance_id, run_folder)

    def update_status(self, task_instance_id, status):
        """Updates execution status."""
        return self.dao.update_status(task_instance_id, status)

    def touch_task_instance(self, task_instance_id, ttl_seconds=DEFAULT_TTL_SECONDS):
        """Updates last_accessed_at and extends expiry."""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        return self.dao.touch_access(task_instance_id, now_str, expires_str)

    def mark_downloaded(self, task_instance_id, ttl_seconds=DEFAULT_TTL_SECONDS):
        """Marks a run as downloaded and extends expiry."""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        return self.dao.mark_downloaded(task_instance_id, now_str, expires_str)

    def mark_deleted(self, task_instance_id):
        """Marks a run as deleted."""
        now = datetime.utcnow()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        return self.dao.mark_deleted(task_instance_id, now_str)

    def get_expired_task_instances(self):
        """Returns task instances that have expired and are not deleted."""
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return self.dao.get_expired_task_instances(now_str)

    def get_deleted_before(self, seconds_ago):
        """Returns task instances deleted before a cutoff."""
        cutoff = datetime.utcnow() - timedelta(seconds=seconds_ago)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        return self.dao.get_deleted_task_instances_before(cutoff_str)

    def hard_delete(self, task_instance_id):
        """Hard deletes a TaskInstance row."""
        return self.dao.delete_task_instance(task_instance_id)

    def is_active(self, task_instance):
        """Returns True if a task instance is not deleted and not expired."""
        if not task_instance:
            return False
        if task_instance.Deleted_At:
            return False
        if not task_instance.Expires_At:
            return True
        expires_at = self._parse_dt(task_instance.Expires_At)
        if not expires_at:
            return True
        return datetime.utcnow() < expires_at

    @staticmethod
    def _parse_dt(value):
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
