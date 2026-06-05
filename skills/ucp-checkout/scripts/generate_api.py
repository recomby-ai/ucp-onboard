#!/usr/bin/env python3
"""Generate a sandbox FastAPI UCP checkout server from profile and catalog JSON."""

import argparse
import json
import shutil
from pathlib import Path


MAIN_PY = r'''from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException


def json_load(path):
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


DATA_DIR = Path(__file__).resolve().parent / "data"
PROFILE = json_load(DATA_DIR / "ucp-profile.json")
CATALOG = json_load(DATA_DIR / "catalog.json")
SESSIONS = {}


app = FastAPI(title="UCP Sandbox Checkout Server", version="0.1.0")


def all_products():
    return CATALOG.get("products", [])


def find_product(product_id):
    for product in all_products():
        if str(product.get("id")) == str(product_id):
            return product
    return None


def find_variant(product, variant_id):
    for variant in product.get("variants", []):
        if str(variant.get("id")) == str(variant_id):
            return variant
    return None


def catalog_response(products):
    return {"products": products, "metadata": {"count": len(products)}}


def build_line_item(raw_item):
    product = find_product(raw_item.get("product_id"))
    if not product:
        raise HTTPException(status_code=400, detail=f"Unknown product_id {raw_item.get('product_id')}")
    variant = find_variant(product, raw_item.get("variant_id"))
    if not variant:
        raise HTTPException(status_code=400, detail=f"Unknown variant_id {raw_item.get('variant_id')}")
    quantity = int(raw_item.get("quantity", 1))
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    price = variant.get("price", {})
    amount = int(price.get("amount", 0))
    currency = price.get("currency", "USD")
    subtotal = amount * quantity
    return {
        "id": f"li_{variant.get('id')}",
        "product_id": product.get("id"),
        "variant_id": variant.get("id"),
        "item": {
            "id": variant.get("id"),
            "title": variant.get("title"),
            "description": variant.get("description", product.get("description", {})),
            "price": {"amount": amount, "currency": currency},
        },
        "quantity": quantity,
        "totals": [
            {"type": "subtotal", "amount": subtotal},
            {"type": "total", "amount": subtotal},
        ],
    }


def calculate_totals(line_items):
    subtotal = sum(item["item"]["price"]["amount"] * item["quantity"] for item in line_items)
    return [
        {"type": "subtotal", "amount": subtotal},
        {"type": "total", "amount": subtotal},
    ]


def session_currency(line_items):
    for item in line_items:
        currency = item.get("item", {}).get("price", {}).get("currency")
        if currency:
            return currency
    return "USD"


def public_session(session):
    result = deepcopy(session)
    result["ucp"] = PROFILE.get("ucp", {})
    return result


@app.get("/.well-known/ucp")
def well_known_ucp():
    return PROFILE


@app.post("/ucp/v1/catalog/search")
def catalog_search(payload: dict):
    query = str(payload.get("query", "")).lower()
    limit = int(payload.get("limit", 20))
    products = all_products()
    if query:
        products = [
            product for product in products
            if query in str(product.get("title", "")).lower()
            or query in str(product.get("description", {})).lower()
        ]
    return catalog_response(products[:limit])


@app.post("/ucp/v1/catalog/lookup")
def catalog_lookup(payload: dict):
    ids = payload.get("ids") or payload.get("product_ids") or []
    products = [product for product in all_products() if str(product.get("id")) in {str(i) for i in ids}]
    return catalog_response(products)


@app.post("/ucp/v1/checkout")
def checkout_create(payload: dict):
    line_items = [build_line_item(item) for item in payload.get("line_items", [])]
    if not line_items:
        raise HTTPException(status_code=400, detail="line_items is required")
    session_id = f"session_{uuid4().hex}"
    session = {
        "id": session_id,
        "status": "incomplete",
        "currency": session_currency(line_items),
        "line_items": line_items,
        "totals": calculate_totals(line_items),
        "links": [
            {"type": "privacy_policy", "url": "/privacy"},
            {"type": "terms_of_service", "url": "/terms"},
        ],
    }
    SESSIONS[session_id] = session
    return public_session(session)


@app.get("/ucp/v1/checkout/{session_id}")
def checkout_retrieve(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return public_session(session)


@app.post("/ucp/v1/checkout/{session_id}")
def checkout_update(session_id: str, payload: dict):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if session["status"] != "incomplete":
        raise HTTPException(status_code=400, detail="only incomplete sessions can be updated")
    line_items = [build_line_item(item) for item in payload.get("line_items", [])]
    if not line_items:
        raise HTTPException(status_code=400, detail="line_items is required")
    session["line_items"] = line_items
    session["currency"] = session_currency(line_items)
    session["totals"] = calculate_totals(line_items)
    return public_session(session)


@app.post("/ucp/v1/checkout/{session_id}/cancel")
def checkout_cancel(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    session["status"] = "canceled"
    return public_session(session)
'''


README = """# UCP Sandbox Checkout Server

Generated FastAPI server for local UCP checkout preflight.

## Run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /.well-known/ucp`
- `POST /ucp/v1/catalog/search`
- `POST /ucp/v1/catalog/lookup`
- `POST /ucp/v1/checkout`
- `GET /ucp/v1/checkout/{id}`
- `POST /ucp/v1/checkout/{id}`
- `POST /ucp/v1/checkout/{id}/cancel`

This server is sandbox-only. It does not implement real payment capture.
"""


ENV_EXAMPLE = """PORT=8000
MERCHANT_DOMAIN=example.com
SESSION_STORAGE=memory
# Add payment provider secrets only after production security review.
"""


def validate_input(profile, catalog):
    errors = []
    if not isinstance(profile.get("ucp"), dict):
        errors.append("profile missing ucp object")
    products = catalog.get("products")
    if not isinstance(products, list) or not products:
        errors.append("catalog missing non-empty products array")
    return errors


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate FastAPI UCP checkout server")
    parser.add_argument("--profile", required=True, help="ucp-profile.json path")
    parser.add_argument("--catalog", required=True, help="catalog.json path")
    parser.add_argument("--output-dir", required=True, help="Directory to write generated server")
    parser.add_argument("--force", action="store_true", help="Overwrite output directory if it exists")
    args = parser.parse_args()

    profile_path = Path(args.profile)
    catalog_path = Path(args.catalog)
    output_dir = Path(args.output_dir)
    if output_dir.exists() and any(output_dir.iterdir()) and not args.force:
        raise SystemExit(f"Output directory {output_dir} is not empty; use --force")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    errors = validate_input(profile, catalog)
    if errors:
        raise SystemExit("Invalid input: " + "; ".join(errors))

    (output_dir / "app" / "data").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(profile_path, output_dir / "app" / "data" / "ucp-profile.json")
    shutil.copyfile(catalog_path, output_dir / "app" / "data" / "catalog.json")
    write(output_dir / "app" / "__init__.py", "")
    write(output_dir / "app" / "main.py", MAIN_PY)
    write(output_dir / "requirements.txt", "fastapi>=0.110\nuvicorn[standard]>=0.27\n")
    write(output_dir / ".env.example", ENV_EXAMPLE)
    write(output_dir / "README.md", README)
    print(f"FastAPI UCP server generated at {output_dir}")


if __name__ == "__main__":
    main()
