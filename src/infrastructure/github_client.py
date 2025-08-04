from typing import Optional
from gql import gql, Client
from .anti_corruption.github_translator import GitHubTranslator, GitHubSearchResult

SEARCH_REPOS_QUERY = gql("""
query ($query: String!, $cursor: String){
  rateLimit {
    cost remaining resetAt
  }
  search(type: REPOSITORY, query: $query, first: 100, after: $cursor) {
    pageInfo { endCursor hasNextPage }
    nodes { ... on Repository { databaseId nameWithOwner stargazerCount } }
  }
}
""")

class GitHubClient:
    """GitHub API client with anti-corruption layer"""
    
    def __init__(self, session: Client):
        self.session = session
        self.translator = GitHubTranslator()
    
    async def search_repositories(self, query: str, cursor: Optional[str] = None) -> GitHubSearchResult:
        """Execute repository search query and return translated result"""
        raw_data = await self.session.execute(
            SEARCH_REPOS_QUERY,
            variable_values={"query": query, "cursor": cursor}
        )
        return self.translator.translate_search_response(raw_data)
