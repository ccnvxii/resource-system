import re
from django.core import mail
from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework.test import APITestCase


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('vol', email='vol@example.com', password='OldPassw0rd!')

    def _request_code(self, email='vol@example.com'):
        return self.client.post('/api/password-reset/', {'email': email}, format='json')

    def _code_from_mail(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def test_invalid_email_format_rejected(self):
        r = self._request_code('not-an-email')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_unknown_email_gets_same_response_and_no_mail(self):
        r = self._request_code('nobody@example.com')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_full_flow(self):
        self.assertEqual(self._request_code().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['vol@example.com'])
        code = self._code_from_mail()
        r = self.client.post('/api/password-reset/confirm/',
                             {'email': 'vol@example.com', 'code': code, 'new_password': 'BrandNewPass123'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPass123'))
        # код одноразовий
        r2 = self.client.post('/api/password-reset/confirm/',
                              {'email': 'vol@example.com', 'code': code, 'new_password': 'AnotherPass123'}, format='json')
        self.assertEqual(r2.status_code, 400)

    def test_wrong_code_and_attempt_limit(self):
        self._request_code()
        code = self._code_from_mail()
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(5):
            r = self.client.post('/api/password-reset/confirm/',
                                 {'email': 'vol@example.com', 'code': wrong, 'new_password': 'BrandNewPass123'}, format='json')
            self.assertEqual(r.status_code, 400)
        # навіть правильний код після 5 невдалих спроб не діє
        r = self.client.post('/api/password-reset/confirm/',
                             {'email': 'vol@example.com', 'code': code, 'new_password': 'BrandNewPass123'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPassw0rd!'))

    def test_resend_cooldown(self):
        self.assertEqual(self._request_code().status_code, 200)
        self.assertEqual(self._request_code().status_code, 429)
        self.assertEqual(len(mail.outbox), 1)

    def test_weak_password_rejected(self):
        self._request_code()
        code = self._code_from_mail()
        r = self.client.post('/api/password-reset/confirm/',
                             {'email': 'vol@example.com', 'code': code, 'new_password': '123'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPassw0rd!'))

    def test_mail_failure_returns_clear_error(self):
        from unittest.mock import patch
        with patch('django.core.mail.send_mail', side_effect=OSError('smtp down')):
            r = self._request_code()
        self.assertEqual(r.status_code, 503)
        self.assertIn('Не вдалося надіслати лист', r.data['error'])
        # після збою можна одразу повторити (кулдаун не застосовується)
        self.assertEqual(self._request_code().status_code, 200)

    def test_verify_checks_code_without_consuming_it(self):
        self._request_code()
        code = self._code_from_mail()
        wrong = '000000' if code != '000000' else '111111'
        bad = self.client.post('/api/password-reset/verify/', {'email': 'vol@example.com', 'code': wrong}, format='json')
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post('/api/password-reset/verify/', {'email': 'vol@example.com', 'code': code}, format='json')
        self.assertEqual(ok.status_code, 200)
        # код ще дійсний для фінального кроку
        done = self.client.post('/api/password-reset/confirm/',
                                {'email': 'vol@example.com', 'code': code, 'new_password': 'BrandNewPass123'}, format='json')
        self.assertEqual(done.status_code, 200)
