from allocations.tests.helpers import log_in_url_for


class SuperuserOnlyViewTests:
    """Tests that every user management view must pass.

    Add this class to the parents of a TestCase whose setUp() defines
    self.url, self.user (a normal user) and self.superuser.
    """

    def test_get_requires_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_post_requires_log_in(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertRedirects(response, log_in_url_for(self.url))

    def test_get_is_forbidden_for_normal_users(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_post_is_forbidden_for_normal_users(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_is_allowed_for_superusers(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
