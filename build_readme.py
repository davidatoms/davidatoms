from python_graphql_client import GraphqlClient
import pathlib
import re
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")


def load_header_config():
    """Load header configuration and generate HTML"""
    config_path = root / "config" / "header.js"

    # Use Node.js to execute the JavaScript file and get the output
    import subprocess
    result = subprocess.run(
        ['node', '-e', f'''
        const header = require("{config_path}");
        console.log(JSON.stringify({
        'name': header.getNameHeader(),
            'subtitle': header.getSubtitleHeader()
        }));
        '''],
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)


def build_header():
    """Build the header section of the README"""
    header_config = load_header_config()

    return f"""<div align="left">
  <h1>
    {header_config['name']}
  </h1>

  <p>
    {header_config['subtitle']}
  </p>
</div>"""


def replace_chunk(content, marker, chunk):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    chunk = f"<!-- {marker} starts -->\n{chunk}\n<!-- {marker} ends -->"
    return r.sub(chunk, content)


if __name__ == "__main__":
    readme = root / "README.md"
    readme_contents = readme.open().read()

    # Update header
    header_html = build_header()
    rewritten = replace_chunk(readme_contents, "header", header_html)

    # Write updated README
    readme.open("w").write(rewritten)