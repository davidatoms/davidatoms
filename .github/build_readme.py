from python_graphql_client import GraphqlClient
import pathlib
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")

# Get token from environment variables
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def replace_chunk(content, marker, chunk):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    chunk = "<!-- {} starts -->\n{}\n<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)


def make_query(after_cursor=None):
    return """
query {
  viewer {
    repositories(first: 100, privacy: PUBLIC, after:AFTER) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        releases(last:1) {
          totalCount
          nodes {
            name
            publishedAt
            url
          }
        }
      }
    }
  }
}
""".replace(
        "AFTER", '"{}"'.format(after_cursor) if after_cursor else "null"
    )


def fetch_releases(oauth_token):
    repos = []
    releases = []
    repo_names = set()
    has_next_page = True
    after_cursor = None

    while has_next_page:
        data = client.execute(
            query=make_query(after_cursor),
            headers={"Authorization": "Bearer {}".format(oauth_token)},
        )
        for repo in data["data"]["viewer"]["repositories"]["nodes"]:
            if repo["releases"]["totalCount"] and repo["name"] not in repo_names:
                repos.append(repo)
                repo_names.add(repo["name"])
                releases.append(
                    {
                        "repo": repo["name"],
                        "release": repo["releases"]["nodes"][0]["name"]
                        .replace(repo["name"], "")
                        .strip(),
                        "published_at": repo["releases"]["nodes"][0][
                            "publishedAt"
                        ].split("T")[0],
                        "url": repo["releases"]["nodes"][0]["url"],
                    }
                )
        has_next_page = data["data"]["viewer"]["repositories"]["pageInfo"][
            "hasNextPage"
        ]
        after_cursor = data["data"]["viewer"]["repositories"]["pageInfo"]["endCursor"]
    return releases


# Example of how to add your own custom section
def fetch_my_custom_section():
    """
    Template for adding your own section.
    Replace this with your own logic to fetch and format your data.
    """
    return [
        {
            "title": "Example Item 1",
            "url": "https://example.com/1",
            "date": "2024-03-08"
        },
        {
            "title": "Example Item 2",
            "url": "https://example.com/2",
            "date": "2024-03-07"
        }
    ]


if __name__ == "__main__":
    readme = root / "README.md"

    # Update recent releases
    releases = fetch_releases(TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    releases_md = "\n".join(
        [
            "* [{repo} {release}]({url}) - {published_at}".format(**release)
            for release in releases[:5]
        ]
    )
    readme_contents = readme.open().read()
    rewritten = replace_chunk(readme_contents, "recent_releases", releases_md)

    # Example of adding your custom section
    custom_items = fetch_my_custom_section()
    custom_md = "\n".join(
        [
            f"* [{item['title']}]({item['url']}) - {item['date']}"
            for item in custom_items
        ]
    )
    rewritten = replace_chunk(rewritten, "custom_section", custom_md)

    readme.open("w").write(rewritten)