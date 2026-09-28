import unittest
import sys
import os

# Add the parent directory to the path to allow imports from 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a test client for each test."""
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        """Test the home page loads correctly."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Project Alpha Chatbot', response.data)

    def test_api_status(self):
        """Test the API status endpoint."""
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok", "service": "Project Alpha"})

if __name__ == '__main__':
    unittest.main()
