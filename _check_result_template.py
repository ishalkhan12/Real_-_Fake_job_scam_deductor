import os
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

tpl = env.get_template("result.html")
ctx = {
    "result": "✅ Legitimate Job",
    "confidence": 50.0,
    "risk_score": 10,
    "website": "https://example.com",
    "website_title": "Example",
}

rendered = tpl.render(**ctx)
assert "Job Analysis Report" in rendered
print("result.html render OK, length:", len(rendered))

