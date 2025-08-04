from gql import gql, Client
from gql.transport.httpx import HTTPXTransport
import os, json

LIST_REPOS = """
query ($cursor: String){
  rateLimit {
    cost remaining resetAt
  }
  search(type: REPOSITORY, query: "stars:>0 is:public", first: 100, after: $cursor) {
    pageInfo { endCursor hasNextPage }
    nodes { ... on Repository { databaseId nameWithOwner stargazerCount } }
  }
}
"""

transport = HTTPXTransport(
    url="https://api.github.com/graphql",
    headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}
)
client = Client(transport=transport, fetch_schema_from_transport=False)

page = client.execute(gql(LIST_REPOS), variable_values={"cursor": None})
print(json.dumps(page, indent=2))
