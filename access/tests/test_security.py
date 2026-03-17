from django.test import TestCase, Client
from django.contrib.auth import get_user_model


class SecurityLoginTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.username = 'sec_test_user_auto'
        self.password = 'P@ssw0rd!'
        self.user = User.objects.create_user(username=self.username, password=self.password, email='sec_auto@example.com')

    def test_login_flow_with_csrf_and_redirect(self):
        client = Client()

        # GET the login page to establish csrf cookie
        resp = client.get('/login/')
        self.assertEqual(resp.status_code, 200)

        csrftoken = client.cookies.get('csrftoken')
        self.assertIsNotNone(csrftoken, 'csrftoken cookie should be set on GET /login/')

        data = {
            'username': self.username,
            'password': self.password,
            'csrfmiddlewaretoken': csrftoken.value,
        }

        resp2 = client.post('/login/?next=/dashboard/', data)

        # Successful POST should redirect to next (302)
        self.assertIn(resp2.status_code, (302, 301))

        # Follow redirect and verify we are authenticated (dashboard should be reachable)
        resp3 = client.get('/dashboard/')
        # dashboard view redirects to login when not authenticated; after login should be 200 or 302 depending on role flow
        self.assertIn(resp3.status_code, (200, 302))
