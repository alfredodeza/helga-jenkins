from helga_jenkins import get_jenkins_url
import pytest

class FakeSettings(object):
    pass

class TestSettings(object):
    def test_missing_jenkins_url(self):
        settings = FakeSettings()
        with pytest.raises(RuntimeError):
            result = get_jenkins_url(settings)

    def test_jenkins_url(self):
        settings = FakeSettings()
        settings.JENKINS_URL = 'http://jenkins.example.com/'
        result = get_jenkins_url(settings)
        assert result == 'http://jenkins.example.com/'
