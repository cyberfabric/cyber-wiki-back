"""
Unit tests for ServiceTokenViewSet.validate_token (POST /service-tokens/<id>/validate/).

Covers happy/sad paths for each service type. The actual HTTP calls to GitHub /
Bitbucket / JIRA are mocked; we only verify the wiring between the view, the
checker helpers, and the persisted validation fields on ServiceToken.
"""
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from service_tokens.models import ServiceToken, ServiceType


@pytest.fixture
def api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _validate_url(token_id) -> str:
    return f'/api/service-tokens/v1/tokens/{token_id}/validate/'


@pytest.mark.django_db
class TestValidateGithubToken:
    @patch('service_tokens.views.http_requests.get')
    def test_valid_token(self, mock_get, api_client, user):
        token = ServiceToken.objects.create(
            user=user,
            service_type=ServiceType.GITHUB,
            base_url='https://api.github.com',
        )
        token.set_token('ghp_xxx')
        token.save()

        mock_resp = mock_get.return_value
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'login': 'octocat'}

        resp = api_client.post(_validate_url(token.id))

        assert resp.status_code == 200
        assert resp.data['valid'] is True
        assert 'octocat' in resp.data['message']

        token.refresh_from_db()
        assert token.last_validation_valid is True
        assert token.last_validated_at is not None

    @patch('service_tokens.views.http_requests.get')
    def test_invalid_token_persists_failure(self, mock_get, api_client, user):
        token = ServiceToken.objects.create(
            user=user,
            service_type=ServiceType.GITHUB,
            base_url='https://api.github.com',
        )
        token.set_token('ghp_bad')
        token.save()

        mock_resp = mock_get.return_value
        mock_resp.status_code = 401

        resp = api_client.post(_validate_url(token.id))

        assert resp.status_code == 200
        assert resp.data['valid'] is False
        assert '401' in resp.data['message']

        token.refresh_from_db()
        assert token.last_validation_valid is False

    @patch('service_tokens.views.http_requests.get')
    def test_request_exception_records_invalid(self, mock_get, api_client, user):
        import requests as http_requests
        token = ServiceToken.objects.create(
            user=user,
            service_type=ServiceType.GITHUB,
            base_url='https://api.github.com',
        )
        token.set_token('ghp_xxx')
        token.save()

        mock_get.side_effect = http_requests.ConnectionError('refused')

        resp = api_client.post(_validate_url(token.id))

        assert resp.status_code == 200
        assert resp.data['valid'] is False
        assert 'refused' in resp.data['message']

        token.refresh_from_db()
        assert token.last_validation_valid is False


@pytest.mark.django_db
class TestValidateMissingToken:
    def test_returns_404(self, api_client):
        import uuid
        resp = api_client.post(_validate_url(uuid.uuid4()))
        assert resp.status_code == 404
        assert resp.data['code'] == 'NOT_FOUND'


@pytest.mark.django_db
class TestValidateCustomHeaderJWT:
    def test_jwt_with_future_expiry_is_valid(self, api_client, user):
        # Build a minimal JWT with exp in the future. We don't sign it —
        # _check_custom_header only decodes the payload.
        import base64
        import json
        future = int(timezone.now().timestamp()) + 3600
        header = base64.urlsafe_b64encode(b'{}').rstrip(b'=').decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({'exp': future}).encode()
        ).rstrip(b'=').decode()
        jwt = f'{header}.{payload}.signature'

        token = ServiceToken.objects.create(
            user=user,
            service_type=ServiceType.CUSTOM_HEADER,
            base_url='https://example.com',
            header_name='X-ZTA',
        )
        token.set_token(jwt)
        token.save()

        resp = api_client.post(_validate_url(token.id))
        assert resp.status_code == 200
        assert resp.data['valid'] is True
        assert 'expires in' in resp.data['message']

    def test_expired_jwt_is_invalid(self, api_client, user):
        import base64
        import json
        past = int(timezone.now().timestamp()) - 3600
        header = base64.urlsafe_b64encode(b'{}').rstrip(b'=').decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({'exp': past}).encode()
        ).rstrip(b'=').decode()
        jwt = f'{header}.{payload}.signature'

        token = ServiceToken.objects.create(
            user=user,
            service_type=ServiceType.CUSTOM_HEADER,
            base_url='https://example.com',
            header_name='X-ZTA',
        )
        token.set_token(jwt)
        token.save()

        resp = api_client.post(_validate_url(token.id))
        assert resp.status_code == 200
        assert resp.data['valid'] is False
        assert 'expired' in resp.data['message']
