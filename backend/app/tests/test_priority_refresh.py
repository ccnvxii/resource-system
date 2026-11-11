from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from app import priority_refresh
from app.models import UserRequest, Resource, RequestPurpose
from app.utils import calculate_request_priority


class PriorityRefreshTests(TestCase):
    def setUp(self):
        priority_refresh._last_refresh_date = None
        self.user = User.objects.create_user('p_user', email='p@example.com', password='x')
        self.resource = Resource.objects.first()
        self.purpose = RequestPurpose.objects.first()
        self.today = timezone.now().date()

    def _make(self, days):
        return UserRequest.objects.create(
            user=self.user, resource=self.resource, quantity_requested=5, purpose=self.purpose,
            due_date=self.today + timedelta(days=days), status='new',
        )

    def _expected(self, req):
        return calculate_request_priority(
            self.purpose.weight,
            self.resource.category.criticality if self.resource.category else 0.5,
            req.latitude, req.longitude, req.due_date, req.extension_count,
        )

    def test_stale_priority_is_refreshed_in_bulk(self):
        near = self._make(3)
        # імітуємо «вчорашній» пріоритет (дедлайн наблизився, а значення лишилось старим)
        UserRequest.objects.filter(pk=near.pk).update(priority=0.01)
        changed = priority_refresh.refresh_stale_priorities()
        near.refresh_from_db()
        self.assertEqual(changed, 1)
        self.assertAlmostEqual(near.priority, self._expected(near), places=3)

    def test_runs_once_per_day(self):
        near = self._make(2)
        UserRequest.objects.filter(pk=near.pk).update(priority=0.01)
        self.assertEqual(priority_refresh.refresh_stale_priorities(), 1)
        UserRequest.objects.filter(pk=near.pk).update(priority=0.01)
        self.assertEqual(priority_refresh.refresh_stale_priorities(), 0)        # вже було сьогодні
        self.assertEqual(priority_refresh.refresh_stale_priorities(force=True), 1)  # примусово

    def test_far_deadlines_are_skipped(self):
        far = self._make(30)
        UserRequest.objects.filter(pk=far.pk).update(priority=0.01)
        self.assertEqual(priority_refresh.refresh_stale_priorities(), 0)
        far.refresh_from_db()
        self.assertEqual(far.priority, 0.01)

    def test_finished_requests_are_skipped(self):
        done = self._make(1)
        UserRequest.objects.filter(pk=done.pk).update(priority=0.01, status='done')
        self.assertEqual(priority_refresh.refresh_stale_priorities(), 0)
