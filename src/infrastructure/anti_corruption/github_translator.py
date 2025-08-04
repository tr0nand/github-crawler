from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ...domain.entities import Repository


@dataclass(frozen=True)
class GitHubRateLimit:
    """Internal representation of rate limit"""
    remaining: int
    cost: int
    reset_at: str


@dataclass(frozen=True)
class GitHubSearchResult:
    """Internal representation of search results"""
    repositories: List[Repository]
    has_next_page: bool
    end_cursor: Optional[str]
    rate_limit: GitHubRateLimit


class GitHubTranslator:
    """Translates GitHub API responses to domain objects"""
    
    @staticmethod
    def translate_search_response(raw_data: Dict) -> GitHubSearchResult:
        """Translate raw GitHub search response to internal model"""
        # Extract repositories
        repos = []
        nodes = raw_data.get("search", {}).get("nodes", [])
        
        for node in nodes:
            if node and node.get("databaseId"):
                repo = GitHubTranslator._translate_repository(node)
                if repo:
                    repos.append(repo)
        
        # Extract pagination
        page_info = raw_data.get("search", {}).get("pageInfo", {})
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor")
        
        # Extract rate limit
        rate_limit_data = raw_data.get("rateLimit", {})
        rate_limit = GitHubRateLimit(
            remaining=rate_limit_data.get("remaining", 0),
            cost=rate_limit_data.get("cost", 0),
            reset_at=rate_limit_data.get("resetAt", "")
        )
        
        return GitHubSearchResult(
            repositories=repos,
            has_next_page=has_next_page,
            end_cursor=end_cursor,
            rate_limit=rate_limit
        )
    
    @staticmethod
    def _translate_repository(node: Dict) -> Optional[Repository]:
        """Translate a single repository node"""
        try:
            return Repository(
                id=node["databaseId"],
                full_name=node["nameWithOwner"],
                stars=node["stargazerCount"]
            )
        except (KeyError, TypeError):
            return None
    
    @staticmethod
    def is_access_error(error_message: str) -> bool:
        """Check if error is due to access restrictions"""
        error_patterns = [
            "ip allow list enabled",
            "must have push access",
            "resource not accessible",
            "rate limit exceeded",
            "forbidden",
            "saml sso",
            "blocked",
            "private repository",
            "requires authentication"
        ]
        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in error_patterns)
