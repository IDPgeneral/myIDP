from __future__ import annotations

import time
from typing import Any

import httpx
import jwt

from app.core.config import Settings
from app.integrations.base import ExternalProviderError, classify_http_error, safe_json


class GitHubClient:
    base_url = "https://api.github.com"

    def __init__(self, settings: Settings, installation_id: str):
        self.settings = settings
        self.installation_id = installation_id

    def _app_jwt(self) -> str:
        if not self.settings.github_app_id or not self.settings.normalized_github_private_key:
            raise ExternalProviderError("GitHub App não configurado.", category="not_configured")
        now = int(time.time())
        return jwt.encode(
            {"iat": now - 60, "exp": now + 540, "iss": self.settings.github_app_id},
            self.settings.normalized_github_private_key,
            algorithm="RS256",
        )

    def _installation_token(self) -> str:
        url = f"{self.base_url}/app/installations/{self.installation_id}/access_tokens"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._app_jwt()}",
            "X-GitHub-Api-Version": self.settings.github_api_version,
        }
        try:
            response = httpx.post(url, headers=headers, timeout=self.settings.http_timeout_seconds)
        except httpx.RequestError as exc:
            raise ExternalProviderError("GitHub indisponível.", category="provider_unavailable") from exc
        if response.status_code != 201:
            raise classify_http_error(response, "GitHub")
        return str(response.json()["token"])

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        token = self._installation_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": self.settings.github_api_version,
        }
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=self.settings.http_timeout_seconds,
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise ExternalProviderError("GitHub indisponível.", category="provider_unavailable") from exc
        if response.status_code >= 400:
            raise classify_http_error(response, "GitHub")
        return safe_json(response)

    def test_connection(self) -> dict[str, Any]:
        data = self._request("GET", "/installation/repositories", params={"per_page": 1})
        assert isinstance(data, dict)
        return {"total_count": data.get("total_count", 0)}

    def repository_snapshot(self, full_name: str) -> dict[str, Any]:
        repo = self._request("GET", f"/repos/{full_name}")
        assert isinstance(repo, dict)
        branch = repo.get("default_branch") or "main"
        commits = self._request("GET", f"/repos/{full_name}/commits", params={"sha": branch, "per_page": 1})
        workflows = self._request("GET", f"/repos/{full_name}/actions/runs", params={"branch": branch, "per_page": 5})
        pulls = self._request("GET", f"/repos/{full_name}/pulls", params={"state": "open", "per_page": 100})
        issues = self._request("GET", f"/repos/{full_name}/issues", params={"state": "open", "per_page": 100})
        commit = commits[0] if isinstance(commits, list) and commits else {}
        workflow_runs = workflows.get("workflow_runs", []) if isinstance(workflows, dict) else []
        pure_issues = [item for item in issues if isinstance(item, dict) and "pull_request" not in item] if isinstance(issues, list) else []
        return {
            "repository": {
                "name": repo.get("name"),
                "owner": (repo.get("owner") or {}).get("login"),
                "url": repo.get("html_url"),
                "default_branch": branch,
            },
            "last_commit": {
                "sha": commit.get("sha"),
                "author": ((commit.get("commit") or {}).get("author") or {}).get("name"),
                "date": ((commit.get("commit") or {}).get("author") or {}).get("date"),
                "message": (commit.get("commit") or {}).get("message"),
                "url": commit.get("html_url"),
            },
            "open_pull_requests": len(pulls) if isinstance(pulls, list) else 0,
            "open_issues": len(pure_issues),
            "workflow_runs": [
                {
                    "id": run.get("id"),
                    "name": run.get("name"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "head_sha": run.get("head_sha"),
                    "head_branch": run.get("head_branch"),
                    "created_at": run.get("created_at"),
                    "updated_at": run.get("updated_at"),
                    "url": run.get("html_url"),
                }
                for run in workflow_runs
            ],
        }
