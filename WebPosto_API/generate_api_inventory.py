import json
import os

openapi = json.load(open('openapi_specs.json', 'r', encoding='utf-8'))
md = ['# Inventario de Endpoints (OpenAPI)\n']

for path, obj in openapi['paths'].items():
    for method, details in obj.items():
        if method == 'parameters':
            continue
        md.append(f'## {method.upper()} {path}')
        tags = ", ".join(details.get("tags", []))
        md.append(f'- **Tags:** {tags}')
        md.append(f'- **Summary:** {details.get("summary", "")}')
        params = details.get('parameters', [])
        
        req_body = details.get('requestBody')
        if params or req_body:
            md.append('- **Request:**')
            if params:
                for p in params:
                    md.append(f'  - `{p["name"]}` ({p["in"]}, required: {p.get("required", False)})')
            if req_body:
                md.append(f'  - Body: JSON')
        else:
            md.append('- **Request:** None')

        resps = details.get('responses', {})
        if resps:
            md.append('- **Responses:**')
            for status, resp in resps.items():
                md.append(f'  - `{status}`: {resp.get("description", "")}')
        md.append('')

os.makedirs('docs', exist_ok=True)
with open('docs/api_inventory.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md))
