from helga_jenkins import get_jenkins_url
import helga_jenkins
import pytest


class FakeSettings(object):
    pass


class TestSettings(object):
    def test_missing_jenkins_url(self):
        settings = FakeSettings()
        with pytest.raises(RuntimeError):
            get_jenkins_url(settings)

    def test_jenkins_url(self):
        settings = FakeSettings()
        settings.JENKINS_URL = 'http://jenkins.example.com/'
        result = get_jenkins_url(settings)
        assert result == 'http://jenkins.example.com/'


class TestParseCredentialsForInstance(object):

    def setup(self):
        helga_jenkins.settings = FakeSettings()

    def teardown(self):
        helga_jenkins.settings = FakeSettings()

    def set_conf(self, setting):
        helga_jenkins.settings.MULTI_JENKINS = setting

    def test_name_collision(self):
        self.set_conf({'status': {'url': 'jenkins.example.com'}})
        with pytest.raises(RuntimeError) as error:
            helga_jenkins.parse_credentials('foo', ['create', 'job'], None)
        assert 'has the same name' in str(error.value)
        assert "'status'" in str(error.value)

    def test_url_is_not_defined(self):
        self.set_conf({'prod': {'username': 'alfredo'}})
        with pytest.raises(RuntimeError) as error:
            helga_jenkins.parse_credentials('alfredo', ['prod', 'status', 'job'], None)
        assert '"url" is a required key' in str(error.value)
        assert 'for Jenkins instance "prod"' in str(error.value)

    def test_regular_user_creds(self):
        self.set_conf(
            {
                'prod': {
                    'username': 'alfredo',
                    'password': 'secret',
                    'url': 'http://ci.example.com'}
            }
        )
        result = helga_jenkins.parse_credentials('alfredo', ['prod', 'status', 'job'])
        assert result['username'] == 'alfredo'
        assert result['password'] == 'secret'
        assert result['url'] == 'http://ci.example.com'

    def test_unable_to_connect_missing_username(self):
        self.set_conf(
            {
                'prod': {
                    'url': 'http://ci.example.com',
                    'credentials': {
                        'ktdreyer': {
                            'username': 'kdreyer',
                            'token': 'lkjh234hjasdf00'}
                        }
                }
            }
        )
        # this fails because the nick 'alfredo' doesn't have a matching
        # configured username for "prod"
        with pytest.raises(RuntimeError) as error:
            helga_jenkins.parse_credentials('alfredo', ['prod', 'status', 'job'])

        assert "config key: 'username'" in str(error.value)

    def test_per_nick_credentials(self):
        self.set_conf(
            {
                'prod': {
                    'username': 'admin',
                    'password': 'secret',
                    'url': 'http://ci.example.com',
                    'credentials': {
                        'ktdreyer': {
                            'username': 'kdreyer',
                            'token': 'lkjh234hjasdf00'}
                    }
                }
            }
        )
        result = helga_jenkins.parse_credentials('ktdreyer', ['prod', 'status', 'job'])
        assert result['username'] == 'kdreyer'
        assert result['password'] == 'lkjh234hjasdf00'
        assert result['url'] == 'http://ci.example.com'


class TestParseCredentials(object):

    def setup(self):
        helga_jenkins.settings = FakeSettings()

    def teardown(self):
        helga_jenkins.settings = FakeSettings()

    def set_conf(self, **kw):
        for k, v in kw.items():
            setattr(helga_jenkins.settings, k, v)

    def test_match_credentials_over_regular_creds(self):
        self.set_conf(
            JENKINS_USERNAME='admin',
            JENKINS_PASSWORD='secret',
            JENKINS_URL='jenkins.example.com',
            JENKINS_CREDENTIALS={
                'alfredodeza': {
                    'username': 'alfredo',
                    'token': 'asdf1234',
                }
            }
        )
        result = helga_jenkins.parse_credentials('alfredodeza', ['status', 'job'], None)
        assert result['username'] == 'alfredo'
        assert result['password'] == 'asdf1234'

    def test_match_user_creds(self):
        self.set_conf(
            JENKINS_USERNAME='admin',
            JENKINS_PASSWORD='secret',
            JENKINS_URL='jenkins.example.com',
        )
        result = helga_jenkins.parse_credentials('alfredodeza', ['status', 'job'], None)
        assert result['username'] == 'admin'
        assert result['password'] == 'secret'

    def test_match_regular_creds_over_user_creds(self):
        self.set_conf(
            JENKINS_USERNAME='admin',
            JENKINS_PASSWORD='secret',
            JENKINS_URL='jenkins.example.com',
            JENKINS_CREDENTIALS={
                'alfredodeza': {
                    'username': 'alfredo',
                    'token': 'asdf1234',
                }
            }
        )
        result = helga_jenkins.parse_credentials('ktdreyer', ['status', 'job'], None)
        assert result['username'] == 'admin'
        assert result['password'] == 'secret'


class TestJobIsParametrized(object):

    def test_no_actions(self):
        job_config = {}
        assert helga_jenkins.job_is_parametrized(job_config) is False

    def test_has_parameter_definitions(self):
        job_config = {'actions': [{}, {u'parameterDefinitions': [{u'defaultParameterValue': {u'value': u''},
               u'description': u'The git branch (or tag) to build',
                  u'name': u'BRANCH',
                     u'type': u'StringParameterDefinition'}]}, {}]}

        assert helga_jenkins.job_is_parametrized(job_config) is True
