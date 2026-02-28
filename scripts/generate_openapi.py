#!/usr/bin/env python3
"""
Generate OpenAPI schema JSON file.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app


def main():
    """Generate OpenAPI schema."""
    app = create_app()
    schema = app.openapi()
    
    output_path = Path(__file__).parent.parent / 'docs' / 'openapi.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print(f"✓ OpenAPI schema generated: {output_path}")
    print(f"  Title: {schema['info']['title']}")
    print(f"  Version: {schema['info']['version']}")
    print(f"  Endpoints: {len(schema['paths'])}")
    
    # Print endpoint summary
    print("\nEndpoints:")
    for path, methods in schema['paths'].items():
        for method in methods.keys():
            if method != 'parameters':
                print(f"  {method.upper():6} {path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
