from unittest import TestCase

from webapi.session import Session


class TestSession(TestCase):
    def test_constructor(self):
        session = Session("1.2.3.4", 1234)
        self.assertEqual("1.2.3.4", session.host)
        self.assertEqual(1234, session.port)
