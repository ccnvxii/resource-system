from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from app.models import Resource, RequestPurpose, UserProfile, UserRequest
from app.optimizer.distribute import calculate_distribution
from app.tests.mock_services import MockDistanceService


class RequestLimitsAndPermissionsTests(APITestCase):
    def setUp(self):
        self.resource = Resource.objects.filter(is_strategic=False).first()
        self.resource.max_per_request = 100
        self.resource.save()
        self.purpose = RequestPurpose.objects.first()
        self.today = timezone.now().date()

        self.vol = User.objects.create_user('vol_l', email='vol_l@example.com', password='x')
        UserProfile.objects.create(user=self.vol, is_approved=True)
        self.other = User.objects.create_user('oth_l', email='oth_l@example.com', password='x')
        UserProfile.objects.create(user=self.other, is_approved=True)
        self.admin = User.objects.create_user('adm_l', email='adm_l@example.com', password='x', is_staff=True)

    def _payload(self, qty, days=5):
        return {
            'resource': self.resource.id, 'quantity_requested': qty, 'purpose': self.purpose.id,
            'city': 'Київ', 'warehouse_address': 'Відділення 1', 'warehouse_ref': 'ADDRESS_DELIVERY',
            'due_date': str(self.today + timedelta(days=days)),
        }

    def _make(self, owner, qty=10, days=5):
        return UserRequest.objects.create(
            user=owner, resource=self.resource, quantity_requested=qty, purpose=self.purpose,
            due_date=self.today + timedelta(days=days), status='new',
        )

    # --- ліміт кількості ---
    def test_single_request_over_limit_rejected(self):
        self.client.force_authenticate(self.vol)
        r = self.client.post('/api/requests/', self._payload(101), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('quantity_requested', r.data)

    def test_limit_applies_to_sum_of_active_requests(self):
        self.client.force_authenticate(self.vol)
        self.assertEqual(self.client.post('/api/requests/', self._payload(60), format='json').status_code, 201)
        r = self.client.post('/api/requests/', self._payload(50), format='json')
        self.assertEqual(r.status_code, 400)  # 60 + 50 > 100
        self.assertEqual(self.client.post('/api/requests/', self._payload(40), format='json').status_code, 201)

    def test_raising_quantity_on_existing_request_is_checked(self):
        req = self._make(self.vol, qty=50)
        self.client.force_authenticate(self.vol)
        r = self.client.patch(f'/api/requests/{req.id}/', {'quantity_requested': 500}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_admin_is_not_limited(self):
        self.client.force_authenticate(self.admin)
        payload = self._payload(5000)
        payload['user'] = self.vol.id
        self.assertEqual(self.client.post('/api/requests/', payload, format='json').status_code, 201)

    # --- права доступу ---
    def test_user_sees_only_own_requests(self):
        mine, theirs = self._make(self.vol), self._make(self.other)
        self.client.force_authenticate(self.vol)
        ids = [x['id'] for x in self.client.get('/api/requests/').data]
        self.assertIn(mine.id, ids)
        self.assertNotIn(theirs.id, ids)

    def test_user_cannot_modify_or_delete_others_request(self):
        theirs = self._make(self.other)
        self.client.force_authenticate(self.vol)
        self.assertEqual(self.client.patch(f'/api/requests/{theirs.id}/', {'quantity_requested': 5}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/requests/{theirs.id}/').status_code, 404)

    def test_user_cannot_reassign_request_to_someone_else(self):
        mine = self._make(self.vol)
        self.client.force_authenticate(self.vol)
        self.client.patch(f'/api/requests/{mine.id}/', {'user': self.other.id}, format='json')
        mine.refresh_from_db()
        self.assertEqual(mine.user_id, self.vol.id)

    def test_admin_sees_everything(self):
        a, b = self._make(self.vol), self._make(self.other)
        self.client.force_authenticate(self.admin)
        ids = [x['id'] for x in self.client.get('/api/requests/').data]
        self.assertTrue({a.id, b.id} <= set(ids))

    # --- термін лише продовжується ---
    def test_deadline_can_only_be_extended_by_user(self):
        req = self._make(self.vol, days=5)
        self.client.force_authenticate(self.vol)
        shorter = self.client.patch(f'/api/requests/{req.id}/', {'due_date': str(self.today + timedelta(days=1))}, format='json')
        self.assertEqual(shorter.status_code, 400)
        longer = self.client.patch(f'/api/requests/{req.id}/', {'due_date': str(self.today + timedelta(days=9))}, format='json')
        self.assertEqual(longer.status_code, 200)


class FairWeightCapTests(APITestCase):
    @patch('app.optimizer.distribute.DistanceMatrixService', MockDistanceService)
    def test_inflated_demand_does_not_grab_larger_share(self):
        stocks = [{'resource_id': 1, 'warehouse_id': 1, 'amount': 10, 'lat': 50.0, 'lng': 30.0}]
        requests = [
            {'id': 1, 'resource_id': 1, 'priority': 5.0, 'amount_needed': 10, 'lat': 50.1, 'lng': 30.1},
            {'id': 2, 'resource_id': 1, 'priority': 5.0, 'amount_needed': 10000, 'lat': 50.2, 'lng': 30.2},
        ]
        plan = calculate_distribution(requests, stocks)
        got = {}
        for item in plan:
            rid = item.get('request_id') or item.get('id')
            got[rid] = got.get(rid, 0) + item['amount']
        self.assertEqual(sum(got.values()), 10)
        # при однаковому пріоритеті «роздута» заявка не повинна отримати суттєво більше за чесну
        self.assertLessEqual(abs(got.get(1, 0) - got.get(2, 0)), 2)
