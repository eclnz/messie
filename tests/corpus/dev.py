"""Developer and technical corpus: source code, config, data, logs, notebooks."""

from __future__ import annotations

TOPICS: dict[str, list[tuple[str, str]]] = {
    "python_web_api": [
        (
            "user_routes",
            "from fastapi import APIRouter, Depends, HTTPException\n"
            "from pydantic import BaseModel\n"
            "router = APIRouter(prefix='/users', tags=['users'])\n"
            "class UserOut(BaseModel):\n"
            "    id: int\n"
            "    email: str\n"
            "@router.get('/{user_id}', response_model=UserOut)\n"
            "async def get_user(user_id: int, session=Depends(get_session)):\n"
            "    user = await session.get(UserRow, user_id)\n"
            "    if user is None:\n"
            "        raise HTTPException(status_code=404, detail='user not found')\n"
            "    return UserOut(id=user.id, email=user.email)\n"
            "@router.post('/', response_model=UserOut, status_code=201)\n"
            "async def create_user(payload: UserOut, session=Depends(get_session)):\n"
            "    row = UserRow(email=payload.email)\n"
            "    session.add(row)\n"
            "    await session.commit()\n"
            "    await session.refresh(row)\n"
            "    return UserOut(id=row.id, email=row.email)\n",
        ),
        (
            "invoice_routes",
            "from fastapi import APIRouter, Depends, Query\n"
            "from pydantic import BaseModel\n"
            "router = APIRouter(prefix='/invoices', tags=['invoices'])\n"
            "class InvoiceOut(BaseModel):\n"
            "    id: int\n"
            "    amount_cents: int\n"
            "    paid: bool\n"
            "@router.get('/', response_model=list[InvoiceOut])\n"
            "async def list_invoices(limit: int = Query(50, le=200), session=Depends(get_session)):\n"
            "    rows = await session.execute(select(InvoiceRow).limit(limit))\n"
            "    return [InvoiceOut(id=r.id, amount_cents=r.amount_cents, paid=r.paid) for r in rows]\n"
            "@router.post('/{invoice_id}/pay', response_model=InvoiceOut)\n"
            "async def pay_invoice(invoice_id: int, session=Depends(get_session)):\n"
            "    row = await session.get(InvoiceRow, invoice_id)\n"
            "    row.paid = True\n"
            "    await session.commit()\n"
            "    return InvoiceOut(id=row.id, amount_cents=row.amount_cents, paid=row.paid)\n",
        ),
        (
            "auth_dependencies",
            "from fastapi import Depends, HTTPException, Header\n"
            "from pydantic import BaseModel\n"
            "class TokenClaims(BaseModel):\n"
            "    subject: str\n"
            "    scopes: list[str]\n"
            "async def get_session():\n"
            "    async with SessionLocal() as session:\n"
            "        yield session\n"
            "async def current_claims(authorization: str = Header(default='')) -> TokenClaims:\n"
            "    if not authorization.startswith('Bearer '):\n"
            "        raise HTTPException(status_code=401, detail='missing bearer token')\n"
            "    raw = authorization.removeprefix('Bearer ')\n"
            "    claims = decode_token(raw)\n"
            "    return TokenClaims(subject=claims['sub'], scopes=claims.get('scopes', []))\n"
            "def require_scope(scope: str):\n"
            "    async def guard(claims: TokenClaims = Depends(current_claims)):\n"
            "        if scope not in claims.scopes:\n"
            "            raise HTTPException(status_code=403, detail='scope required')\n"
            "        return claims\n"
            "    return guard\n",
        ),
        (
            "app_main",
            "from fastapi import FastAPI\n"
            "from fastapi.responses import JSONResponse\n"
            "app = FastAPI(title='Ledger API', version='2.4.0')\n"
            "app.include_router(user_router)\n"
            "app.include_router(invoice_router)\n"
            "@app.get('/healthz')\n"
            "async def healthz():\n"
            "    return {'status': 'ok'}\n"
            "@app.exception_handler(ValueError)\n"
            "async def value_error_handler(request, exc: ValueError):\n"
            "    return JSONResponse(status_code=422, content={'detail': str(exc)})\n"
            "@app.on_event('startup')\n"
            "async def startup():\n"
            "    await engine.connect()\n"
            "@app.on_event('shutdown')\n"
            "async def shutdown():\n"
            "    await engine.dispose()\n",
        ),
        (
            "schemas_billing",
            "from datetime import date\n"
            "from pydantic import BaseModel, Field, field_validator\n"
            "class LineItem(BaseModel):\n"
            "    description: str = Field(min_length=1, max_length=200)\n"
            "    quantity: int = Field(ge=1)\n"
            "    unit_cents: int = Field(ge=0)\n"
            "class BillingRequest(BaseModel):\n"
            "    customer_id: int\n"
            "    due_on: date\n"
            "    items: list[LineItem]\n"
            "    @field_validator('items')\n"
            "    @classmethod\n"
            "    def not_empty(cls, value: list[LineItem]) -> list[LineItem]:\n"
            "        if not value:\n"
            "            raise ValueError('at least one line item is required')\n"
            "        return value\n"
            "class BillingResponse(BaseModel):\n"
            "    invoice_id: int\n"
            "    total_cents: int\n"
            "    def as_dict(self) -> dict:\n"
            "        return self.model_dump()\n",
        ),
        (
            "test_user_routes",
            "import pytest\n"
            "from httpx import AsyncClient\n"
            "@pytest.mark.asyncio\n"
            "async def test_get_user_returns_payload(client: AsyncClient):\n"
            "    response = await client.get('/users/7')\n"
            "    assert response.status_code == 200\n"
            "    assert response.json()['id'] == 7\n"
            "@pytest.mark.asyncio\n"
            "async def test_get_user_missing_is_404(client: AsyncClient):\n"
            "    response = await client.get('/users/999999')\n"
            "    assert response.status_code == 404\n"
            "    assert response.json()['detail'] == 'user not found'\n"
            "@pytest.mark.asyncio\n"
            "async def test_create_user(client: AsyncClient):\n"
            "    response = await client.post('/users/', json={'id': 0, 'email': 'a@example.invalid'})\n"
            "    assert response.status_code == 201\n"
            "    body = response.json()\n"
            "    assert body['email'] == 'a@example.invalid'\n",
        ),
    ],
    "javascript_frontend": [
        (
            "CartDrawer",
            "import { useState, useEffect } from 'react';\n"
            "import { useCartStore } from './cartStore';\n"
            "export function CartDrawer({ open, onClose }) {\n"
            "  const items = useCartStore((s) => s.items);\n"
            "  const [animating, setAnimating] = useState(false);\n"
            "  useEffect(() => {\n"
            "    setAnimating(true);\n"
            "    const handle = window.setTimeout(() => setAnimating(false), 220);\n"
            "    return () => window.clearTimeout(handle);\n"
            "  }, [open]);\n"
            "  const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);\n"
            "  return (\n"
            "    <aside className={open ? 'drawer drawer--open' : 'drawer'} aria-hidden={!open}>\n"
            "      <button className='drawer__close' onClick={onClose}>Close</button>\n"
            "      <ul className='drawer__list'>\n"
            "        {items.map((item) => <li key={item.sku}>{item.title} x {item.qty}</li>)}\n"
            "      </ul>\n"
            "      <footer className={animating ? 'fade' : ''}>Subtotal {subtotal}</footer>\n"
            "    </aside>\n"
            "  );\n"
            "}\n",
        ),
        (
            "cartStore",
            "import { create } from 'zustand';\n"
            "export const useCartStore = create((set, get) => ({\n"
            "  items: [],\n"
            "  addItem: (sku, title, price) =>\n"
            "    set((state) => {\n"
            "      const existing = state.items.find((item) => item.sku === sku);\n"
            "      if (existing) {\n"
            "        return { items: state.items.map((i) => (i.sku === sku ? { ...i, qty: i.qty + 1 } : i)) };\n"
            "      }\n"
            "      return { items: [...state.items, { sku, title, price, qty: 1 }] };\n"
            "    }),\n"
            "  removeItem: (sku) => set((state) => ({ items: state.items.filter((i) => i.sku !== sku) })),\n"
            "  clear: () => set({ items: [] }),\n"
            "  count: () => get().items.reduce((total, item) => total + item.qty, 0),\n"
            "}));\n",
        ),
        (
            "useDebouncedSearch",
            "import { useState, useEffect, useRef } from 'react';\n"
            "export function useDebouncedSearch(query, delayMs = 250) {\n"
            "  const [results, setResults] = useState([]);\n"
            "  const [pending, setPending] = useState(false);\n"
            "  const controllerRef = useRef(null);\n"
            "  useEffect(() => {\n"
            "    if (!query) {\n"
            "      setResults([]);\n"
            "      return undefined;\n"
            "    }\n"
            "    setPending(true);\n"
            "    const handle = window.setTimeout(async () => {\n"
            "      controllerRef.current?.abort();\n"
            "      controllerRef.current = new AbortController();\n"
            "      const res = await fetch(`/search?q=${encodeURIComponent(query)}`);\n"
            "      setResults(await res.json());\n"
            "      setPending(false);\n"
            "    }, delayMs);\n"
            "    return () => window.clearTimeout(handle);\n"
            "  }, [query, delayMs]);\n"
            "  return { results, pending };\n"
            "}\n",
        ),
        (
            "ProductGrid",
            "import { CartDrawer } from './CartDrawer';\n"
            "import { useCartStore } from './cartStore';\n"
            "export function ProductGrid({ products }) {\n"
            "  const addItem = useCartStore((s) => s.addItem);\n"
            "  return (\n"
            "    <section className='grid'>\n"
            "      {products.map((product) => (\n"
            "        <article className='grid__card' key={product.sku}>\n"
            "          <img className='grid__image' src={product.image} alt={product.title} />\n"
            "          <h3 className='grid__title'>{product.title}</h3>\n"
            "          <p className='grid__price'>{product.price}</p>\n"
            "          <button onClick={() => addItem(product.sku, product.title, product.price)}>\n"
            "            Add to cart\n"
            "          </button>\n"
            "        </article>\n"
            "      ))}\n"
            "    </section>\n"
            "  );\n"
            "}\n",
        ),
        (
            "formatters",
            "export function formatPrice(cents, locale = 'en-GB') {\n"
            "  const formatter = new Intl.NumberFormat(locale, { style: 'currency', currency: 'GBP' });\n"
            "  return formatter.format(cents / 100);\n"
            "}\n"
            "export function truncate(text, max = 60) {\n"
            "  if (text.length <= max) return text;\n"
            "  return `${text.slice(0, max - 1)}...`;\n"
            "}\n"
            "export function classNames(...parts) {\n"
            "  return parts.filter(Boolean).join(' ');\n"
            "}\n"
            "export function slugify(title) {\n"
            "  return title\n"
            "    .toLowerCase()\n"
            "    .replace(/[^a-z0-9]+/g, '-')\n"
            "    .replace(/^-|-$/g, '');\n"
            "}\n"
            "export const noop = () => {};\n",
        ),
        (
            "CartDrawer.test",
            "import { render, screen, fireEvent } from '@testing-library/react';\n"
            "import { CartDrawer } from './CartDrawer';\n"
            "describe('CartDrawer', () => {\n"
            "  it('renders each cart item', () => {\n"
            "    render(<CartDrawer open onClose={() => {}} />);\n"
            "    expect(screen.getByRole('complementary')).toBeVisible();\n"
            "  });\n"
            "  it('calls onClose when the close button is clicked', () => {\n"
            "    const onClose = jest.fn();\n"
            "    render(<CartDrawer open onClose={onClose} />);\n"
            "    fireEvent.click(screen.getByText('Close'));\n"
            "    expect(onClose).toHaveBeenCalledTimes(1);\n"
            "  });\n"
            "  it('hides the drawer when closed', () => {\n"
            "    render(<CartDrawer open={false} onClose={() => {}} />);\n"
            "    expect(screen.getByRole('complementary', { hidden: true })).toBeTruthy();\n"
            "  });\n"
            "});\n",
        ),
    ],
    "sql_migrations": [
        (
            "0012_add_orders_table",
            "-- migration 0012: create the orders TABLE\n"
            "BEGIN;\n"
            "CREATE TABLE orders (\n"
            "    order_id BIGSERIAL PRIMARY KEY,\n"
            "    buyer_ref BIGINT NOT NULL,\n"
            "    placed_at TIMESTAMPTZ NOT NULL DEFAULT now(),\n"
            "    total_pence INTEGER NOT NULL CHECK (total_pence >= 0),\n"
            "    state TEXT NOT NULL DEFAULT 'pending'\n"
            ");\n"
            "CREATE INDEX orders_buyer_ref_idx ON orders (buyer_ref);\n"
            "CREATE INDEX orders_placed_at_idx ON orders (placed_at DESC);\n"
            "ALTER TABLE orders ADD CONSTRAINT orders_state_chk\n"
            "    CHECK (state IN ('pending', 'settled', 'voided'));\n"
            "COMMIT;\n"
            "-- rollback for migration 0012\n"
            "-- DROP INDEX orders_placed_at_idx;\n"
            "-- DROP INDEX orders_buyer_ref_idx;\n"
            "-- DROP TABLE orders;\n",
        ),
        (
            "0013_add_shipping_column",
            "-- migration 0013: add a shipping COLUMN to the orders TABLE\n"
            "BEGIN;\n"
            "ALTER TABLE orders ADD COLUMN shipping_pence INTEGER NOT NULL DEFAULT 0;\n"
            "ALTER TABLE orders ADD COLUMN carrier_code TEXT;\n"
            "ALTER TABLE orders ALTER COLUMN state SET DEFAULT 'pending';\n"
            "UPDATE orders SET shipping_pence = 495 WHERE carrier_code IS NULL;\n"
            "CREATE INDEX orders_carrier_code_idx ON orders (carrier_code)\n"
            "    WHERE carrier_code IS NOT NULL;\n"
            "COMMIT;\n"
            "-- rollback for migration 0013\n"
            "-- BEGIN;\n"
            "-- DROP INDEX orders_carrier_code_idx;\n"
            "-- ALTER TABLE orders DROP COLUMN carrier_code;\n"
            "-- ALTER TABLE orders DROP COLUMN shipping_pence;\n"
            "-- COMMIT;\n",
        ),
        (
            "0014_backfill_buyer_index",
            "-- migration 0014: rebuild the buyers TABLE INDEX set\n"
            "BEGIN;\n"
            "CREATE TABLE buyers (\n"
            "    buyer_id BIGSERIAL PRIMARY KEY,\n"
            "    display_name TEXT NOT NULL,\n"
            "    contact_ref TEXT NOT NULL UNIQUE,\n"
            "    created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n"
            ");\n"
            "CREATE UNIQUE INDEX buyers_contact_ref_idx ON buyers (lower(contact_ref));\n"
            "ALTER TABLE orders\n"
            "    ADD CONSTRAINT orders_buyer_ref_fkey\n"
            "    FOREIGN KEY (buyer_ref) REFERENCES buyers (buyer_id) ON DELETE RESTRICT;\n"
            "COMMIT;\n"
            "-- rollback for migration 0014\n"
            "-- ALTER TABLE orders DROP CONSTRAINT orders_buyer_ref_fkey;\n"
            "-- DROP TABLE buyers;\n",
        ),
        (
            "0015_drop_legacy_column",
            "-- migration 0015: drop the legacy COLUMN from the orders TABLE\n"
            "BEGIN;\n"
            "ALTER TABLE orders DROP COLUMN IF EXISTS legacy_basket_blob;\n"
            "ALTER TABLE orders DROP COLUMN IF EXISTS legacy_channel;\n"
            "DROP INDEX IF EXISTS orders_legacy_channel_idx;\n"
            "ALTER TABLE orders RENAME COLUMN total_pence TO gross_pence;\n"
            "CREATE INDEX orders_gross_pence_idx ON orders (gross_pence);\n"
            "ANALYZE orders;\n"
            "COMMIT;\n"
            "-- rollback for migration 0015\n"
            "-- ALTER TABLE orders RENAME COLUMN gross_pence TO total_pence;\n"
            "-- DROP INDEX orders_gross_pence_idx;\n",
        ),
        (
            "0016_create_refunds_table",
            "-- migration 0016: create the refunds TABLE with an INDEX per order\n"
            "BEGIN;\n"
            "CREATE TABLE refunds (\n"
            "    refund_id BIGSERIAL PRIMARY KEY,\n"
            "    order_ref BIGINT NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,\n"
            "    amount_pence INTEGER NOT NULL CHECK (amount_pence > 0),\n"
            "    reason_code TEXT NOT NULL,\n"
            "    issued_at TIMESTAMPTZ NOT NULL DEFAULT now()\n"
            ");\n"
            "CREATE INDEX refunds_order_ref_idx ON refunds (order_ref);\n"
            "CREATE INDEX refunds_reason_code_idx ON refunds (reason_code);\n"
            "ALTER TABLE refunds ADD CONSTRAINT refunds_reason_chk\n"
            "    CHECK (reason_code IN ('damaged', 'late', 'duplicate', 'other'));\n"
            "COMMIT;\n",
        ),
        (
            "0017_alter_orders_state",
            "-- migration 0017: ALTER the orders TABLE state COLUMN\n"
            "BEGIN;\n"
            "ALTER TABLE orders DROP CONSTRAINT orders_state_chk;\n"
            "ALTER TABLE orders ADD CONSTRAINT orders_state_chk\n"
            "    CHECK (state IN ('pending', 'settled', 'voided', 'refunded'));\n"
            "UPDATE orders SET state = 'refunded'\n"
            "    WHERE order_id IN (SELECT order_ref FROM refunds);\n"
            "CREATE INDEX orders_state_idx ON orders (state);\n"
            "VACUUM ANALYZE orders;\n"
            "COMMIT;\n"
            "-- rollback for migration 0017\n"
            "-- DROP INDEX orders_state_idx;\n"
            "-- ALTER TABLE orders DROP CONSTRAINT orders_state_chk;\n",
        ),
    ],
    "shell_deploy_scripts": [
        (
            "deploy_staging",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "TARGET=${1:-staging}\n"
            "RELEASE_DIR=/srv/releases/$(date +%Y%m%d%H%M%S)\n"
            "echo 'deploy: preparing release directory'\n"
            "ssh deploy@$TARGET.internal.invalid \"mkdir -p $RELEASE_DIR\"\n"
            "rsync -az --delete --exclude '.git' ./build/ deploy@$TARGET.internal.invalid:$RELEASE_DIR/\n"
            "ssh deploy@$TARGET.internal.invalid \"ln -sfn $RELEASE_DIR /srv/current\"\n"
            "echo 'deploy: restarting service units'\n"
            "ssh deploy@$TARGET.internal.invalid 'sudo systemctl daemon-reload'\n"
            "ssh deploy@$TARGET.internal.invalid 'sudo systemctl restart ledger-web.service'\n"
            "ssh deploy@$TARGET.internal.invalid 'sudo systemctl status ledger-web.service --no-pager'\n"
            "echo \"deploy: finished for $TARGET\"\n",
        ),
        (
            "rollback_release",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "TARGET=${1:?usage: rollback_release TARGET}\n"
            "echo 'deploy: rolling back to the previous release'\n"
            "PREVIOUS=$(ssh deploy@$TARGET.internal.invalid 'ls -1dt /srv/releases/* | sed -n 2p')\n"
            "if [ -z \"$PREVIOUS\" ]; then\n"
            "  echo 'deploy: no previous release to restore' >&2\n"
            "  exit 1\n"
            "fi\n"
            "ssh deploy@$TARGET.internal.invalid \"ln -sfn $PREVIOUS /srv/current\"\n"
            "ssh deploy@$TARGET.internal.invalid 'sudo systemctl restart ledger-web.service'\n"
            "ssh deploy@$TARGET.internal.invalid 'sudo systemctl restart ledger-worker.service'\n"
            "echo \"deploy: rollback complete, now serving $PREVIOUS\"\n",
        ),
        (
            "sync_static_assets",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "SOURCE_DIR=${SOURCE_DIR:-./public}\n"
            "TARGET=${1:-edge}\n"
            "echo 'deploy: syncing static assets'\n"
            "rsync -avz --checksum --delete-after \\\n"
            "  --chmod=D755,F644 \\\n"
            "  \"$SOURCE_DIR/\" deploy@$TARGET.internal.invalid:/srv/static/\n"
            "rsync -avz --dry-run \"$SOURCE_DIR/\" deploy@$TARGET.internal.invalid:/srv/static/ | tail -n 5\n"
            "ssh deploy@$TARGET.internal.invalid 'sudo systemctl reload ledger-edge.service'\n"
            "echo 'deploy: asset sync done'\n",
        ),
        (
            "restart_workers",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "UNITS='ledger-worker@1.service ledger-worker@2.service ledger-worker@3.service'\n"
            "for unit in $UNITS; do\n"
            "  echo \"deploy: draining $unit\"\n"
            "  sudo systemctl stop \"$unit\"\n"
            "  sleep 2\n"
            "  sudo systemctl start \"$unit\"\n"
            "  if ! sudo systemctl is-active --quiet \"$unit\"; then\n"
            "    echo \"deploy: $unit failed to restart\" >&2\n"
            "    exit 1\n"
            "  fi\n"
            "done\n"
            "sudo systemctl restart ledger-scheduler.service\n"
            "echo 'deploy: all worker units restarted'\n",
        ),
        (
            "provision_host",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "TARGET=${1:?usage: provision_host TARGET}\n"
            "echo 'deploy: provisioning host'\n"
            "ssh root@$TARGET.internal.invalid 'apt-get update -qq && apt-get install -y rsync'\n"
            "ssh root@$TARGET.internal.invalid 'id deploy || useradd -m -s /bin/bash deploy'\n"
            "rsync -az ./systemd/ root@$TARGET.internal.invalid:/etc/systemd/system/\n"
            "ssh root@$TARGET.internal.invalid 'systemctl daemon-reload'\n"
            "ssh root@$TARGET.internal.invalid 'systemctl enable --now ledger-web.service'\n"
            "ssh root@$TARGET.internal.invalid 'systemctl enable --now ledger-worker@1.service'\n"
            "echo 'deploy: host ready'\n",
        ),
        (
            "backup_before_deploy",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "TARGET=${1:-staging}\n"
            "STAMP=$(date +%Y%m%d-%H%M)\n"
            "echo 'deploy: taking a pre-release snapshot'\n"
            "ssh deploy@$TARGET.internal.invalid \"tar czf /tmp/current-$STAMP.tgz -C /srv current\"\n"
            "rsync -az deploy@$TARGET.internal.invalid:/tmp/current-$STAMP.tgz ./backups/\n"
            "ssh deploy@$TARGET.internal.invalid \"rm -f /tmp/current-$STAMP.tgz\"\n"
            "find ./backups -name 'current-*.tgz' -mtime +14 -delete\n"
            "ssh deploy@$TARGET.internal.invalid 'sudo systemctl restart ledger-web.service'\n"
            "echo \"deploy: snapshot stored as current-$STAMP.tgz\"\n",
        ),
    ],
    "docker_k8s_config": [
        (
            "docker-compose.override",
            "services:\n"
            "  ledger-web:\n"
            "    image: registry.invalid/ledger-web:2.4.0\n"
            "    container_name: ledger-web\n"
            "    ports:\n"
            "      - '8080:8080'\n"
            "    volumes:\n"
            "      - ./data:/var/lib/ledger\n"
            "    environment:\n"
            "      LEDGER_MODE: container\n"
            "    healthcheck:\n"
            "      test: ['CMD', 'curl', '-f', 'http://localhost:8080/healthz']\n"
            "      interval: 30s\n"
            "  ledger-cache:\n"
            "    image: registry.invalid/cache:7\n"
            "    volumes:\n"
            "      - cache-volume:/data\n"
            "volumes:\n"
            "  cache-volume: {}\n",
        ),
        (
            "Dockerfile.runtime",
            "FROM registry.invalid/base-python:3.12-slim AS builder\n"
            "WORKDIR /build\n"
            "COPY requirements.lock ./\n"
            "RUN pip install --no-cache-dir --target /build/vendor -r requirements.lock\n"
            "FROM registry.invalid/base-python:3.12-slim AS runtime\n"
            "WORKDIR /app\n"
            "COPY --from=builder /build/vendor /app/vendor\n"
            "COPY ./src /app/src\n"
            "ENV PYTHONPATH=/app/vendor\n"
            "EXPOSE 8080\n"
            "VOLUME /var/lib/ledger\n"
            "USER 10001\n"
            "HEALTHCHECK --interval=30s CMD ['/app/healthcheck']\n"
            "ENTRYPOINT ['/app/vendor/bin/serve']\n"
            "CMD ['--bind', '0.0.0.0:8080']\n",
        ),
        (
            "web-deployment",
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: ledger-web\n"
            "  namespace: ledger\n"
            "spec:\n"
            "  replicas: 3\n"
            "  selector:\n"
            "    matchLabels:\n"
            "      app.kubernetes.io/name: ledger-web\n"
            "  template:\n"
            "    metadata:\n"
            "      labels:\n"
            "        app.kubernetes.io/name: ledger-web\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: ledger-web\n"
            "          image: registry.invalid/ledger-web:2.4.0\n"
            "          resources:\n"
            "            limits:\n"
            "              cpu: '1'\n"
            "              memory: 512Mi\n"
            "          livenessProbe:\n"
            "            httpGet:\n"
            "              path: /healthz\n"
            "              port: 8080\n",
        ),
        (
            "web-service",
            "apiVersion: v1\n"
            "kind: Service\n"
            "metadata:\n"
            "  name: ledger-web\n"
            "  namespace: ledger\n"
            "spec:\n"
            "  type: ClusterIP\n"
            "  selector:\n"
            "    app.kubernetes.io/name: ledger-web\n"
            "  ports:\n"
            "    - name: http\n"
            "      port: 80\n"
            "      targetPort: 8080\n"
            "---\n"
            "apiVersion: v1\n"
            "kind: Namespace\n"
            "metadata:\n"
            "  name: ledger\n"
            "  labels:\n"
            "    app.kubernetes.io/part-of: ledger\n",
        ),
        (
            "worker-statefulset",
            "apiVersion: apps/v1\n"
            "kind: StatefulSet\n"
            "metadata:\n"
            "  name: ledger-worker\n"
            "  namespace: ledger\n"
            "spec:\n"
            "  serviceName: ledger-worker\n"
            "  replicas: 2\n"
            "  selector:\n"
            "    matchLabels:\n"
            "      app.kubernetes.io/name: ledger-worker\n"
            "  template:\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: ledger-worker\n"
            "          image: registry.invalid/ledger-worker:2.4.0\n"
            "          volumeMounts:\n"
            "            - name: spool\n"
            "              mountPath: /var/spool/ledger\n"
            "  volumeClaimTemplates:\n"
            "    - metadata:\n"
            "        name: spool\n"
            "      spec:\n"
            "        accessModes: ['ReadWriteOnce']\n",
        ),
        (
            "ingress-rules",
            "apiVersion: networking.k8s.io/v1\n"
            "kind: Ingress\n"
            "metadata:\n"
            "  name: ledger-ingress\n"
            "  namespace: ledger\n"
            "  annotations:\n"
            "    ingress.kubernetes.io/rewrite-target: /\n"
            "spec:\n"
            "  ingressClassName: public\n"
            "  rules:\n"
            "    - host: ledger.internal.invalid\n"
            "      http:\n"
            "        paths:\n"
            "          - path: /\n"
            "            pathType: Prefix\n"
            "            backend:\n"
            "              service:\n"
            "                name: ledger-web\n"
            "                port:\n"
            "                  number: 80\n"
            "  tls:\n"
            "    - secretName: ledger-tls\n",
        ),
    ],
    "ci_pipeline_config": [
        (
            "lint-and-test",
            "name: lint-and-test\n"
            "on:\n"
            "  push:\n"
            "    branches: [trunk]\n"
            "  pull_request: {}\n"
            "jobs:\n"
            "  checks:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            "        toolchain: ['3.11', '3.12']\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Install toolchain\n"
            "        run: make bootstrap TOOLCHAIN=${{ matrix.toolchain }}\n"
            "      - name: Run linters\n"
            "        run: make lint\n"
            "      - name: Run unit suite\n"
            "        run: make test ARGS='--maxfail=1'\n"
            "      - name: Upload coverage artifact\n"
            "        uses: actions/upload-artifact@v4\n",
        ),
        (
            "release-pipeline",
            "name: release-pipeline\n"
            "on:\n"
            "  workflow_dispatch:\n"
            "    inputs:\n"
            "      channel:\n"
            "        description: release channel\n"
            "        default: beta\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    outputs:\n"
            "      version: ${{ steps.meta.outputs.version }}\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - id: meta\n"
            "        run: echo \"version=$(make print-version)\" >> \"$GITHUB_OUTPUT\"\n"
            "      - name: Build artifacts\n"
            "        run: make package CHANNEL=${{ inputs.channel }}\n"
            "  publish:\n"
            "    needs: build\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: Publish artifacts\n"
            "        run: make publish VERSION=${{ needs.build.outputs.version }}\n",
        ),
        (
            "nightly-matrix",
            "name: nightly-matrix\n"
            "on:\n"
            "  schedule:\n"
            "    - cron: '17 2 * * *'\n"
            "concurrency:\n"
            "  group: nightly\n"
            "  cancel-in-progress: true\n"
            "jobs:\n"
            "  soak:\n"
            "    runs-on: ubuntu-latest\n"
            "    timeout-minutes: 90\n"
            "    strategy:\n"
            "      fail-fast: false\n"
            "      matrix:\n"
            "        shard: [1, 2, 3, 4]\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Restore cache\n"
            "        uses: actions/cache@v4\n"
            "      - name: Run shard\n"
            "        run: make soak SHARD=${{ matrix.shard }} TOTAL_SHARDS=4\n",
        ),
        (
            "gitlab-ci",
            "stages:\n"
            "  - verify\n"
            "  - package\n"
            "  - promote\n"
            "variables:\n"
            "  CACHE_KEY: verify-$CI_COMMIT_REF_SLUG\n"
            "verify:lint:\n"
            "  stage: verify\n"
            "  script:\n"
            "    - make lint\n"
            "  rules:\n"
            "    - if: $CI_PIPELINE_SOURCE == 'merge_request_event'\n"
            "verify:test:\n"
            "  stage: verify\n"
            "  parallel: 3\n"
            "  script:\n"
            "    - make test\n"
            "  artifacts:\n"
            "    reports:\n"
            "      junit: reports/junit.xml\n"
            "package:build:\n"
            "  stage: package\n"
            "  needs: ['verify:lint', 'verify:test']\n"
            "  script:\n"
            "    - make package\n",
        ),
        (
            "pr-checks",
            "name: pr-checks\n"
            "on:\n"
            "  pull_request:\n"
            "    types: [opened, synchronize, reopened]\n"
            "permissions:\n"
            "  contents: read\n"
            "  checks: write\n"
            "jobs:\n"
            "  quick:\n"
            "    runs-on: ubuntu-latest\n"
            "    if: github.event.pull_request.draft == false\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "        with:\n"
            "          fetch-depth: 0\n"
            "      - name: Check formatting\n"
            "        run: make fmt-check\n"
            "      - name: Check changelog entry\n"
            "        run: make changelog-check BASE=${{ github.base_ref }}\n"
            "      - name: Comment summary\n"
            "        run: make pr-summary\n",
        ),
        (
            "buildkite.pipeline",
            "steps:\n"
            "  - label: ':mag: lint'\n"
            "    command: make lint\n"
            "    agents:\n"
            "      queue: verify\n"
            "  - label: ':test_tube: unit'\n"
            "    command: make test\n"
            "    parallelism: 4\n"
            "    retry:\n"
            "      automatic:\n"
            "        limit: 2\n"
            "  - wait: ~\n"
            "  - label: ':package: package'\n"
            "    command: make package\n"
            "    artifact_paths:\n"
            "      - 'dist/*.tar.gz'\n"
            "  - block: ':shipit: promote'\n"
            "    prompt: Promote this build?\n"
            "  - label: ':rocket: promote'\n"
            "    command: make promote\n",
        ),
    ],
    "server_logs": [
        (
            "gateway-access",
            "2026-03-11T09:14:02.118Z INFO gateway request_id=7f3a method=GET path=/v1/quotes status=200 ms=14\n"
            "2026-03-11T09:14:02.441Z INFO gateway request_id=7f3b method=POST path=/v1/quotes status=201 ms=63\n"
            "2026-03-11T09:14:03.002Z WARN gateway request_id=7f3c upstream=pricing latency_ms=812 retry=1\n"
            "2026-03-11T09:14:03.517Z INFO gateway request_id=7f3c method=GET path=/v1/quotes status=200 ms=915\n"
            "2026-03-11T09:14:05.880Z ERROR gateway request_id=7f3d upstream=pricing err=connection_reset\n"
            "2026-03-11T09:14:06.001Z INFO gateway request_id=7f3d method=GET path=/v1/quotes status=502 ms=121\n"
            "2026-03-11T09:14:11.310Z INFO gateway request_id=7f40 method=DELETE path=/v1/quotes/88 status=204\n"
            "2026-03-11T09:14:18.774Z DEBUG gateway pool=upstream idle=6 active=11 waiters=0\n"
            "2026-03-11T09:14:21.009Z INFO gateway request_id=7f41 method=GET path=/healthz status=200 ms=1\n",
        ),
        (
            "worker-stderr",
            "2026-03-11T10:02:00.004Z INFO worker shard=2 event=job_start job_id=a91f kind=settle\n"
            "2026-03-11T10:02:00.219Z DEBUG worker shard=2 event=lock_acquired job_id=a91f wait_ms=12\n"
            "2026-03-11T10:02:01.884Z INFO worker shard=2 event=job_done job_id=a91f ms=1880\n"
            "2026-03-11T10:02:02.100Z INFO worker shard=2 event=job_start job_id=a920 kind=reconcile\n"
            "2026-03-11T10:02:09.442Z WARN worker shard=2 event=slow_job job_id=a920 ms=7342 threshold_ms=5000\n"
            "2026-03-11T10:02:09.903Z ERROR worker shard=2 event=job_failed job_id=a920 err=deadline_exceeded\n"
            "2026-03-11T10:02:10.011Z INFO worker shard=2 event=job_requeued job_id=a920 attempt=2\n"
            "2026-03-11T10:02:15.330Z INFO worker shard=2 event=job_done job_id=a920 ms=5319 attempt=2\n"
            "2026-03-11T10:02:30.000Z DEBUG worker shard=2 event=heartbeat queued=4 inflight=1\n",
        ),
        (
            "auth-audit",
            "2026-03-11T11:30:01.772Z INFO audit event=login_ok subject=u-4412 source_ip=10.20.0.14 mfa=totp\n"
            "2026-03-11T11:30:44.010Z WARN audit event=login_failed subject=u-4412 reason=bad_totp attempt=1\n"
            "2026-03-11T11:31:02.556Z WARN audit event=login_failed subject=u-4412 reason=bad_totp attempt=2\n"
            "2026-03-11T11:31:19.004Z ERROR audit event=account_locked subject=u-4412 lock_minutes=15\n"
            "2026-03-11T11:45:00.221Z INFO audit event=account_unlocked subject=u-4412 actor=u-0001\n"
            "2026-03-11T11:46:31.907Z INFO audit event=login_ok subject=u-4412 source_ip=10.20.0.14 mfa=totp\n"
            "2026-03-11T12:01:10.333Z INFO audit event=scope_granted subject=u-4412 scope=quotes:write\n"
            "2026-03-11T12:07:55.128Z INFO audit event=token_revoked subject=u-7780 actor=u-0001\n"
            "2026-03-11T12:09:00.000Z DEBUG audit event=rotation_check next_rotation_hours=18\n",
        ),
        (
            "cache-node-01",
            "2026-03-11T13:00:00.000Z INFO cache node=01 event=startup version=7.2.1 maxmemory_mb=4096\n"
            "2026-03-11T13:00:02.441Z INFO cache node=01 event=rdb_loaded keys=812344 ms=2441\n"
            "2026-03-11T13:05:00.010Z DEBUG cache node=01 event=stats hits=98211 misses=1420 hit_rate=0.985\n"
            "2026-03-11T13:12:44.778Z WARN cache node=01 event=eviction policy=allkeys-lru evicted=2210\n"
            "2026-03-11T13:12:45.006Z WARN cache node=01 event=memory_pressure used_mb=3980 maxmemory_mb=4096\n"
            "2026-03-11T13:14:01.220Z ERROR cache node=01 event=client_dropped reason=output_buffer_limit\n"
            "2026-03-11T13:20:00.014Z DEBUG cache node=01 event=stats hits=104880 misses=1611 hit_rate=0.984\n"
            "2026-03-11T13:40:00.002Z INFO cache node=01 event=bgsave_started\n"
            "2026-03-11T13:40:06.918Z INFO cache node=01 event=bgsave_done ms=6916 size_mb=512\n",
        ),
        (
            "cron-runner",
            "2026-03-12T00:00:00.001Z INFO cron event=tick schedule=nightly-reconcile\n"
            "2026-03-12T00:00:00.114Z INFO cron event=task_start task=nightly-reconcile pid=48112\n"
            "2026-03-12T00:04:12.660Z INFO cron event=task_done task=nightly-reconcile exit=0 ms=252546\n"
            "2026-03-12T01:00:00.002Z INFO cron event=tick schedule=hourly-rollup\n"
            "2026-03-12T01:00:00.077Z INFO cron event=task_start task=hourly-rollup pid=48330\n"
            "2026-03-12T01:00:31.902Z ERROR cron event=task_done task=hourly-rollup exit=1 ms=31825\n"
            "2026-03-12T01:00:31.910Z WARN cron event=task_retry task=hourly-rollup attempt=2 backoff_s=60\n"
            "2026-03-12T01:01:32.004Z INFO cron event=task_done task=hourly-rollup exit=0 ms=60094\n"
            "2026-03-12T02:00:00.000Z INFO cron event=tick schedule=hourly-rollup\n",
        ),
        (
            "edge-proxy",
            "2026-03-12T07:30:00.442Z INFO edge conn_id=c1001 client=198.51.100.7 tls=1.3 sni=ledger alpn=h2\n"
            "2026-03-12T07:30:00.601Z INFO edge conn_id=c1001 method=GET path=/assets/app.css status=200 ms=3\n"
            "2026-03-12T07:30:04.118Z WARN edge conn_id=c1002 event=rate_limited bucket=ip tokens_left=0\n"
            "2026-03-12T07:30:04.120Z INFO edge conn_id=c1002 method=GET path=/v1/quotes status=429 ms=1\n"
            "2026-03-12T07:30:12.880Z ERROR edge conn_id=c1003 event=tls_handshake_failed alert=unknown_ca\n"
            "2026-03-12T07:31:00.004Z DEBUG edge event=upstream_health backend=gateway healthy=4 total=4\n"
            "2026-03-12T07:31:45.717Z INFO edge conn_id=c1004 method=POST path=/v1/quotes status=201 ms=88\n"
            "2026-03-12T07:32:10.339Z WARN edge conn_id=c1004 event=slow_upstream backend=gateway ms=1904\n"
            "2026-03-12T07:33:00.000Z DEBUG edge event=conn_stats open=182 closed=944 h2_streams=610\n",
        ),
    ],
    "sales_csv_data": [
        (
            "regional_sales_q1",
            "region,rep_id,units_sold,gross_revenue,discount_rate,quarter\n"
            "north,R-1001,412,18540.00,0.05,Q1\n"
            "north,R-1002,388,17120.50,0.07,Q1\n"
            "south,R-1103,504,23870.25,0.03,Q1\n"
            "south,R-1104,297,12455.75,0.11,Q1\n"
            "east,R-1207,631,29910.00,0.04,Q1\n"
            "east,R-1208,145,6320.40,0.15,Q1\n"
            "west,R-1310,522,24788.90,0.06,Q1\n"
            "west,R-1311,478,21004.10,0.08,Q1\n"
            "north,R-1003,209,9114.00,0.12,Q1\n"
            "south,R-1105,366,16092.60,0.09,Q1\n"
            "east,R-1209,441,19877.45,0.05,Q1\n"
            "west,R-1312,388,17660.30,0.07,Q1\n",
        ),
        (
            "regional_sales_q2",
            "region,rep_id,units_sold,gross_revenue,discount_rate,quarter\n"
            "north,R-1001,455,20310.00,0.05,Q2\n"
            "north,R-1002,402,18004.25,0.06,Q2\n"
            "south,R-1103,548,26120.80,0.04,Q2\n"
            "south,R-1104,311,13820.15,0.10,Q2\n"
            "east,R-1207,688,32440.70,0.03,Q2\n"
            "east,R-1208,190,8215.90,0.14,Q2\n"
            "west,R-1310,561,26993.55,0.05,Q2\n"
            "west,R-1311,499,22711.00,0.08,Q2\n"
            "north,R-1003,244,10730.40,0.11,Q2\n"
            "south,R-1105,381,17203.35,0.09,Q2\n"
            "east,R-1209,470,21440.60,0.05,Q2\n"
            "west,R-1312,410,18944.20,0.07,Q2\n",
        ),
        (
            "product_units_by_sku",
            "sku,product_line,units_sold,gross_revenue,returns,quarter\n"
            "SKU-4410,desk_lamp,1820,45500.00,41,Q1\n"
            "SKU-4411,desk_lamp,940,23500.00,18,Q1\n"
            "SKU-5520,office_chair,612,91800.00,27,Q1\n"
            "SKU-5521,office_chair,388,58200.00,15,Q1\n"
            "SKU-6630,filing_unit,1104,33120.00,52,Q1\n"
            "SKU-6631,filing_unit,877,26310.00,33,Q1\n"
            "SKU-7740,monitor_arm,2011,60330.00,88,Q1\n"
            "SKU-7741,monitor_arm,1455,43650.00,61,Q1\n"
            "SKU-8850,cable_tray,3022,30220.00,104,Q1\n"
            "SKU-8851,cable_tray,2744,27440.00,97,Q1\n",
        ),
        (
            "rep_quota_attainment",
            "rep_id,region,quota_revenue,gross_revenue,attainment_pct,units_sold\n"
            "R-1001,north,18000.00,18540.00,103.0,412\n"
            "R-1002,north,18000.00,17120.50,95.1,388\n"
            "R-1003,north,12000.00,9114.00,76.0,209\n"
            "R-1103,south,22000.00,23870.25,108.5,504\n"
            "R-1104,south,14000.00,12455.75,89.0,297\n"
            "R-1105,south,16000.00,16092.60,100.6,366\n"
            "R-1207,east,28000.00,29910.00,106.8,631\n"
            "R-1208,east,9000.00,6320.40,70.2,145\n"
            "R-1209,east,20000.00,19877.45,99.4,441\n"
            "R-1310,west,24000.00,24788.90,103.3,522\n"
            "R-1311,west,21000.00,21004.10,100.0,478\n"
            "R-1312,west,18000.00,17660.30,98.1,388\n",
        ),
        (
            "channel_revenue_monthly",
            "month,channel,region,orders,units_sold,gross_revenue,discount_rate\n"
            "2026-01,direct,north,311,1204,54210.00,0.06\n"
            "2026-01,reseller,north,188,940,38115.50,0.12\n"
            "2026-01,direct,south,402,1601,71880.20,0.05\n"
            "2026-02,direct,north,340,1288,58004.75,0.06\n"
            "2026-02,reseller,north,201,1012,40990.10,0.11\n"
            "2026-02,direct,south,418,1655,74330.60,0.05\n"
            "2026-03,direct,north,366,1377,62115.00,0.05\n"
            "2026-03,reseller,north,214,1080,43772.40,0.10\n"
            "2026-03,direct,south,440,1740,78210.90,0.04\n"
            "2026-03,reseller,west,177,815,33120.25,0.13\n",
        ),
        (
            "discount_impact_summary",
            "region,discount_band,orders,units_sold,gross_revenue,net_revenue\n"
            "north,0-5pct,410,1622,72440.00,69018.00\n"
            "north,6-10pct,288,1140,50210.50,46193.66\n"
            "north,11-15pct,114,468,20100.00,17587.50\n"
            "south,0-5pct,502,1980,89330.25,85183.60\n"
            "south,6-10pct,301,1188,53440.15,49164.94\n"
            "south,11-15pct,98,401,17220.80,15068.20\n"
            "east,0-5pct,611,2402,108440.70,103430.00\n"
            "east,6-10pct,244,955,42115.90,38746.63\n"
            "west,0-5pct,540,2140,96993.55,92143.87\n"
            "west,11-15pct,131,540,23660.20,20701.68\n",
        ),
    ],
    "ml_notebook": [
        (
            "churn_baseline",
            "# %% [markdown]\n"
            "# Baseline churn model: logistic regression on tabular features\n"
            "# %%\n"
            "features = load_frame('churn_features')\n"
            "labels = features.pop('churned')\n"
            "print(features.shape, labels.mean())\n"
            "# %%\n"
            "train_x, valid_x, train_y, valid_y = split(features, labels, valid_fraction=0.2, seed=7)\n"
            "scaler = StandardScaler().fit(train_x)\n"
            "# %%\n"
            "model = LogisticRegression(penalty='l2', C=0.4, max_iter=500)\n"
            "model.fit(scaler.transform(train_x), train_y)\n"
            "# %%\n"
            "probs = model.predict_proba(scaler.transform(valid_x))[:, 1]\n"
            "print('roc_auc', roc_auc_score(valid_y, probs))\n"
            "print('log_loss', log_loss(valid_y, probs))\n"
            "# %% [markdown]\n"
            "# Baseline roc_auc is 0.781. Next: gradient boosting with the same feature frame.\n",
        ),
        (
            "feature_exploration",
            "# %% [markdown]\n"
            "# Exploring the feature frame before modelling\n"
            "# %%\n"
            "frame = load_frame('churn_features')\n"
            "frame.describe().transpose().head(12)\n"
            "# %%\n"
            "missing = frame.isna().mean().sort_values(ascending=False)\n"
            "print(missing[missing > 0])\n"
            "# %%\n"
            "correlations = frame.corr(numeric_only=True)['tenure_months'].sort_values()\n"
            "plot_bar(correlations.tail(10), title='correlation with tenure_months')\n"
            "# %%\n"
            "plot_histogram(frame['monthly_spend'], bins=40, title='monthly_spend distribution')\n"
            "# %% [markdown]\n"
            "# monthly_spend is right skewed, so a log transform goes into the feature pipeline.\n"
            "# %%\n"
            "frame['log_spend'] = np_log1p(frame['monthly_spend'])\n"
            "save_frame(frame, 'churn_features_v2')\n",
        ),
        (
            "gbm_hyperparam_sweep",
            "# %% [markdown]\n"
            "# Gradient boosting sweep over depth and learning rate\n"
            "# %%\n"
            "train_x, valid_x, train_y, valid_y = load_split('churn_features_v2', seed=7)\n"
            "grid = [(d, lr) for d in (3, 5, 7) for lr in (0.02, 0.05, 0.1)]\n"
            "# %%\n"
            "scores = {}\n"
            "for depth, learning_rate in grid:\n"
            "    model = GradientBoosting(max_depth=depth, learning_rate=learning_rate, n_estimators=400)\n"
            "    model.fit(train_x, train_y)\n"
            "    probs = model.predict_proba(valid_x)[:, 1]\n"
            "    scores[(depth, learning_rate)] = roc_auc_score(valid_y, probs)\n"
            "# %%\n"
            "best = max(scores, key=scores.get)\n"
            "print('best params', best, 'roc_auc', scores[best])\n"
            "# %% [markdown]\n"
            "# depth=5, learning_rate=0.05 reaches roc_auc 0.834 on the validation split.\n",
        ),
        (
            "embedding_visualisation",
            "# %% [markdown]\n"
            "# Projecting learned customer embeddings into two dimensions\n"
            "# %%\n"
            "vectors = load_array('customer_embeddings')\n"
            "print(vectors.shape, vectors.dtype)\n"
            "# %%\n"
            "reducer = UMAP(n_neighbors=25, min_dist=0.08, metric='cosine', random_state=7)\n"
            "projected = reducer.fit_transform(vectors)\n"
            "# %%\n"
            "clusters = KMeans(n_clusters=6, random_state=7).fit_predict(projected)\n"
            "print('silhouette', silhouette_score(projected, clusters))\n"
            "# %%\n"
            "plot_scatter(projected[:, 0], projected[:, 1], colour=clusters, title='customer embedding map')\n"
            "# %% [markdown]\n"
            "# Cluster 3 groups high monthly_spend customers with short tenure_months.\n",
        ),
        (
            "model_evaluation_report",
            "# %% [markdown]\n"
            "# Evaluating the tuned model against the held-out split\n"
            "# %%\n"
            "model = load_model('gbm_depth5_lr005')\n"
            "holdout_x, holdout_y = load_holdout('churn_features_v2')\n"
            "# %%\n"
            "probs = model.predict_proba(holdout_x)[:, 1]\n"
            "print('roc_auc', roc_auc_score(holdout_y, probs))\n"
            "print('average_precision', average_precision_score(holdout_y, probs))\n"
            "# %%\n"
            "for threshold in (0.3, 0.4, 0.5, 0.6):\n"
            "    preds = probs >= threshold\n"
            "    print(threshold, precision_score(holdout_y, preds), recall_score(holdout_y, preds))\n"
            "# %%\n"
            "plot_calibration(holdout_y, probs, bins=10, title='calibration curve')\n"
            "# %% [markdown]\n"
            "# A 0.4 threshold balances precision 0.61 against recall 0.68.\n",
        ),
        (
            "feature_importance_shap",
            "# %% [markdown]\n"
            "# Attributing model predictions to individual features\n"
            "# %%\n"
            "model = load_model('gbm_depth5_lr005')\n"
            "sample_x = load_sample('churn_features_v2', rows=2000, seed=7)\n"
            "# %%\n"
            "explainer = TreeExplainer(model)\n"
            "attributions = explainer.shap_values(sample_x)\n"
            "print(attributions.shape)\n"
            "# %%\n"
            "mean_abs = abs(attributions).mean(axis=0)\n"
            "ranking = sorted(zip(sample_x.columns, mean_abs), key=lambda pair: -pair[1])\n"
            "for name, value in ranking[:10]:\n"
            "    print(name, round(float(value), 4))\n"
            "# %%\n"
            "plot_beeswarm(attributions, sample_x, title='feature attributions')\n"
            "# %% [markdown]\n"
            "# log_spend and tenure_months dominate; support_tickets matters less than expected.\n",
        ),
    ],
    "go_microservice": [
        (
            "quote_handler",
            "package quote\n"
            "import (\n"
            "\t'context'\n"
            "\t'encoding/json'\n"
            "\t'net/http'\n"
            ")\n"
            "type Handler struct {\n"
            "\tstore Store\n"
            "}\n"
            "func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {\n"
            "\tctx, cancel := context.WithTimeout(r.Context(), requestTimeout)\n"
            "\tdefer cancel()\n"
            "\tquote, err := h.store.Fetch(ctx, r.PathValue('id'))\n"
            "\tif err != nil {\n"
            "\t\thttp.Error(w, 'quote lookup failed', http.StatusBadGateway)\n"
            "\t\treturn\n"
            "\t}\n"
            "\tw.Header().Set('Content-Type', 'application/json')\n"
            "\tif err := json.NewEncoder(w).Encode(quote); err != nil {\n"
            "\t\tlogger.Error('encode failed', 'err', err)\n"
            "\t}\n"
            "}\n",
        ),
        (
            "quote_store",
            "package quote\n"
            "import (\n"
            "\t'context'\n"
            "\t'errors'\n"
            "\t'sync'\n"
            ")\n"
            "var ErrNotFound = errors.New('quote not found')\n"
            "type Store interface {\n"
            "\tFetch(ctx context.Context, id string) (Quote, error)\n"
            "\tPut(ctx context.Context, q Quote) error\n"
            "}\n"
            "type memStore struct {\n"
            "\tmu     sync.RWMutex\n"
            "\tquotes map[string]Quote\n"
            "}\n"
            "func (m *memStore) Fetch(ctx context.Context, id string) (Quote, error) {\n"
            "\tm.mu.RLock()\n"
            "\tdefer m.mu.RUnlock()\n"
            "\tq, ok := m.quotes[id]\n"
            "\tif !ok {\n"
            "\t\treturn Quote{}, ErrNotFound\n"
            "\t}\n"
            "\treturn q, nil\n"
            "}\n",
        ),
        (
            "grpc_server",
            "package transport\n"
            "import (\n"
            "\t'context'\n"
            "\t'net'\n"
            "\t'google.golang.org/grpc'\n"
            ")\n"
            "type quoteServer struct {\n"
            "\tUnimplementedQuoteServiceServer\n"
            "\tstore quote.Store\n"
            "}\n"
            "func (s *quoteServer) GetQuote(ctx context.Context, req *GetQuoteRequest) (*QuoteReply, error) {\n"
            "\tq, err := s.store.Fetch(ctx, req.GetId())\n"
            "\tif err != nil {\n"
            "\t\treturn nil, status.Error(codes.NotFound, 'quote missing')\n"
            "\t}\n"
            "\treturn &QuoteReply{Id: q.ID, Pence: q.Pence}, nil\n"
            "}\n"
            "func Serve(lis net.Listener, store quote.Store) error {\n"
            "\tsrv := grpc.NewServer(grpc.ConnectionTimeout(connTimeout))\n"
            "\tRegisterQuoteServiceServer(srv, &quoteServer{store: store})\n"
            "\treturn srv.Serve(lis)\n"
            "}\n",
        ),
        (
            "worker_pool",
            "package pipeline\n"
            "import (\n"
            "\t'context'\n"
            "\t'sync'\n"
            ")\n"
            "func Fan(ctx context.Context, jobs <-chan Job, workers int, fn func(Job) error) error {\n"
            "\tvar wg sync.WaitGroup\n"
            "\terrCh := make(chan error, workers)\n"
            "\tfor i := 0; i < workers; i++ {\n"
            "\t\twg.Add(1)\n"
            "\t\tgo func() {\n"
            "\t\t\tdefer wg.Done()\n"
            "\t\t\tfor job := range jobs {\n"
            "\t\t\t\tselect {\n"
            "\t\t\t\tcase <-ctx.Done():\n"
            "\t\t\t\t\treturn\n"
            "\t\t\t\tdefault:\n"
            "\t\t\t\t}\n"
            "\t\t\t\tif err := fn(job); err != nil {\n"
            "\t\t\t\t\terrCh <- err\n"
            "\t\t\t\t}\n"
            "\t\t\t}\n"
            "\t\t}()\n"
            "\t}\n"
            "\twg.Wait()\n"
            "\tclose(errCh)\n"
            "\treturn <-errCh\n"
            "}\n",
        ),
        (
            "quote_handler_test",
            "package quote\n"
            "import (\n"
            "\t'context'\n"
            "\t'net/http/httptest'\n"
            "\t'testing'\n"
            ")\n"
            "func TestHandlerReturnsQuote(t *testing.T) {\n"
            "\tstore := newMemStore()\n"
            "\tif err := store.Put(context.Background(), Quote{ID: 'q-1', Pence: 4200}); err != nil {\n"
            "\t\tt.Fatalf('put failed: %v', err)\n"
            "\t}\n"
            "\th := &Handler{store: store}\n"
            "\trec := httptest.NewRecorder()\n"
            "\treq := httptest.NewRequest('GET', '/quotes/q-1', nil)\n"
            "\th.ServeHTTP(rec, req)\n"
            "\tif rec.Code != 200 {\n"
            "\t\tt.Fatalf('want 200, got %d', rec.Code)\n"
            "\t}\n"
            "}\n"
            "func TestFetchMissingReturnsErr(t *testing.T) {\n"
            "\t_, err := newMemStore().Fetch(context.Background(), 'nope')\n"
            "\tif !errors.Is(err, ErrNotFound) {\n"
            "\t\tt.Fatalf('want ErrNotFound, got %v', err)\n"
            "\t}\n"
            "}\n",
        ),
        (
            "cmd_quoted",
            "package main\n"
            "import (\n"
            "\t'context'\n"
            "\t'net'\n"
            "\t'os'\n"
            "\t'os/signal'\n"
            ")\n"
            "func main() {\n"
            "\tctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)\n"
            "\tdefer stop()\n"
            "\tstore := quote.NewMemStore()\n"
            "\tlis, err := net.Listen('tcp', ':9090')\n"
            "\tif err != nil {\n"
            "\t\tlogger.Error('listen failed', 'err', err)\n"
            "\t\tos.Exit(1)\n"
            "\t}\n"
            "\tgo func() {\n"
            "\t\tif err := transport.Serve(lis, store); err != nil {\n"
            "\t\t\tlogger.Error('serve failed', 'err', err)\n"
            "\t\t}\n"
            "\t}()\n"
            "\t<-ctx.Done()\n"
            "\tlogger.Info('shutting down')\n"
            "}\n",
        ),
    ],
    "app_settings_config": [
        (
            "pyproject",
            "[project]\n"
            "name = 'ledger-tools'\n"
            "version = '2.4.0'\n"
            "requires-python = '>=3.11'\n"
            "dependencies = ['httpx>=0.27', 'orjson>=3.10']\n"
            "[project.optional-dependencies]\n"
            "dev = ['ruff>=0.6', 'pytest>=8.2']\n"
            "[tool.ruff]\n"
            "line-length = 100\n"
            "target-version = 'py311'\n"
            "[tool.ruff.lint]\n"
            "select = ['E', 'F', 'I', 'UP']\n"
            "ignore = ['E501']\n"
            "[tool.pytest.ini_options]\n"
            "testpaths = ['tests']\n"
            "addopts = '-ra --strict-markers'\n"
            "[build-system]\n"
            "requires = ['hatchling']\n"
            "build-backend = 'hatchling.build'\n",
        ),
        (
            "settings.defaults",
            "[general]\n"
            "app_name = ledger-tools\n"
            "locale = en_GB\n"
            "timezone = Etc/UTC\n"
            "theme = slate\n"
            "[limits]\n"
            "max_upload_mb = 25\n"
            "max_rows_per_export = 50000\n"
            "request_timeout_seconds = 30\n"
            "[features]\n"
            "enable_bulk_export = true\n"
            "enable_beta_reports = false\n"
            "enable_audit_trail = true\n"
            "[paths]\n"
            "state_dir = ~/.local/state/ledger-tools\n"
            "cache_dir = ~/.cache/ledger-tools\n"
            "[logging]\n"
            "level = info\n"
            "format = plain\n"
            "rotate_mb = 64\n",
        ),
        (
            "tsconfig",
            "{\n"
            "  'compilerOptions': {\n"
            "    'target': 'ES2022',\n"
            "    'module': 'ESNext',\n"
            "    'moduleResolution': 'bundler',\n"
            "    'strict': true,\n"
            "    'noUncheckedIndexedAccess': true,\n"
            "    'noImplicitOverride': true,\n"
            "    'declaration': true,\n"
            "    'outDir': 'dist',\n"
            "    'rootDir': 'src',\n"
            "    'skipLibCheck': true,\n"
            "    'esModuleInterop': true,\n"
            "    'resolveJsonModule': true,\n"
            "    'types': ['node']\n"
            "  },\n"
            "  'include': ['src/**/*.ts'],\n"
            "  'exclude': ['dist', 'coverage', 'fixtures']\n"
            "}\n",
        ),
        (
            "editor.preferences",
            "[editor]\n"
            "tab_width = 4\n"
            "insert_spaces = true\n"
            "trim_trailing_whitespace = true\n"
            "insert_final_newline = true\n"
            "ruler_column = 100\n"
            "[format_on_save]\n"
            "python = true\n"
            "typescript = true\n"
            "markdown = false\n"
            "[search]\n"
            "exclude_dirs = dist,coverage,node_modules,.venv\n"
            "follow_symlinks = false\n"
            "[keymap]\n"
            "profile = default\n"
            "leader = space\n"
            "[telemetry]\n"
            "enabled = false\n",
        ),
        (
            "package.manifest",
            "{\n"
            "  'name': 'ledger-tools-ui',\n"
            "  'version': '2.4.0',\n"
            "  'private': true,\n"
            "  'type': 'module',\n"
            "  'engines': { 'node': '>=20' },\n"
            "  'scripts': {\n"
            "    'build': 'tsc --build',\n"
            "    'check': 'tsc --noEmit',\n"
            "    'clean': 'rm -rf dist coverage'\n"
            "  },\n"
            "  'dependencies': {\n"
            "    'zustand': '^4.5.0'\n"
            "  },\n"
            "  'devDependencies': {\n"
            "    'typescript': '^5.5.0'\n"
            "  },\n"
            "  'files': ['dist']\n"
            "}\n",
        ),
        (
            "feature.flags",
            "[flags.bulk_export]\n"
            "enabled = true\n"
            "rollout_percent = 100\n"
            "owner = platform\n"
            "[flags.beta_reports]\n"
            "enabled = false\n"
            "rollout_percent = 0\n"
            "owner = analytics\n"
            "[flags.new_navigation]\n"
            "enabled = true\n"
            "rollout_percent = 25\n"
            "owner = design\n"
            "[flags.audit_trail]\n"
            "enabled = true\n"
            "rollout_percent = 100\n"
            "owner = platform\n"
            "[defaults]\n"
            "sticky_bucketing = true\n"
            "evaluation_cache_seconds = 60\n"
            "fallback = disabled\n",
        ),
    ],
    "api_docs_markdown": [
        (
            "quickstart",
            "# Quickstart\n"
            "\n"
            "This guide walks a new reader through the first request in under five minutes.\n"
            "\n"
            "## Before you begin\n"
            "\n"
            "You need an account, a workspace, and a token placeholder such as `REPLACE_ME`.\n"
            "\n"
            "## Steps\n"
            "\n"
            "1. Create a workspace from the console.\n"
            "2. Copy the token placeholder into your local environment.\n"
            "3. Send your first request and read the response body.\n"
            "\n"
            "## What you get back\n"
            "\n"
            "Every response carries a `request_id` you can quote when asking for help.\n"
            "\n"
            "## Next\n"
            "\n"
            "Read the reference page for the full list of endpoints and their arguments.\n",
        ),
        (
            "endpoint-reference",
            "# Endpoint reference\n"
            "\n"
            "Each endpoint below lists its arguments, its response shape, and the errors it can raise.\n"
            "\n"
            "## List quotes\n"
            "\n"
            "Returns a page of quotes. Accepts a `limit` argument between 1 and 200.\n"
            "\n"
            "| Argument | Type | Required | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| `limit` | integer | no | Defaults to 50 |\n"
            "| `cursor` | string | no | Opaque page cursor |\n"
            "\n"
            "## Create a quote\n"
            "\n"
            "Accepts a body with `customer` and `amount`. Raises a validation error when either is absent.\n"
            "\n"
            "## Errors\n"
            "\n"
            "Errors always include a machine-readable `code` and a human-readable `message`.\n",
        ),
        (
            "authentication-guide",
            "# Authentication\n"
            "\n"
            "Requests are authenticated with a bearer token issued per workspace.\n"
            "\n"
            "## Getting a token\n"
            "\n"
            "Create a token from the console. Store it as `REPLACE_ME` in a secret manager, never in a repo.\n"
            "\n"
            "## Scopes\n"
            "\n"
            "Tokens carry scopes. A read-only integration should hold only the read scope.\n"
            "\n"
            "## Rotation\n"
            "\n"
            "Rotate tokens every ninety days. Create the replacement first, then retire the old one.\n"
            "\n"
            "## Troubleshooting\n"
            "\n"
            "A missing token gives an unauthorised response. A valid token with the wrong scope is forbidden.\n",
        ),
        (
            "pagination-and-limits",
            "# Pagination and limits\n"
            "\n"
            "Collections are paginated with opaque cursors rather than page numbers.\n"
            "\n"
            "## Reading a page\n"
            "\n"
            "Ask for a page, read the items, and follow the cursor in the response until it is absent.\n"
            "\n"
            "## Why cursors\n"
            "\n"
            "Cursors stay correct while items are added or removed, which page numbers do not.\n"
            "\n"
            "## Rate limits\n"
            "\n"
            "Each workspace has a per-minute budget. When you exceed it the response tells you to wait.\n"
            "\n"
            "## Advice\n"
            "\n"
            "Back off, retry with jitter, and never spin tightly on a limited response.\n",
        ),
        (
            "webhooks-overview",
            "# Webhooks\n"
            "\n"
            "Webhooks let your own service react to changes without asking repeatedly.\n"
            "\n"
            "## Registering\n"
            "\n"
            "Register a destination and choose the event names you care about.\n"
            "\n"
            "## Delivery\n"
            "\n"
            "Deliveries are retried with growing gaps for up to a day. Respond quickly and do the work later.\n"
            "\n"
            "## Verifying\n"
            "\n"
            "Every delivery is signed. Verify the signature with your shared placeholder `xxxxxxxx` value.\n"
            "\n"
            "## Ordering\n"
            "\n"
            "Deliveries are not ordered. Use the event timestamp to discard anything you already handled.\n",
        ),
        (
            "changelog",
            "# Changelog\n"
            "\n"
            "Changes that affect readers of this documentation, newest first.\n"
            "\n"
            "## 2.4.0\n"
            "\n"
            "Added the quickstart page. Rewrote the authentication guide around scopes.\n"
            "\n"
            "## 2.3.0\n"
            "\n"
            "Documented cursors on every collection. Removed the old page-number wording.\n"
            "\n"
            "## 2.2.0\n"
            "\n"
            "Added a webhooks overview with a verification section.\n"
            "\n"
            "## 2.1.0\n"
            "\n"
            "Clarified which arguments are required on each endpoint and which are optional.\n"
            "\n"
            "## 2.0.0\n"
            "\n"
            "Reorganised the whole reference so related pages sit beside one another.\n",
        ),
    ],
}

EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python_web_api": ("py",),
    "javascript_frontend": ("js", "ts"),
    "sql_migrations": ("sql",),
    "shell_deploy_scripts": ("sh", "txt"),
    "docker_k8s_config": ("yaml", "yml"),
    "ci_pipeline_config": ("yml", "yaml"),
    "server_logs": ("log", "txt"),
    "sales_csv_data": ("csv", "txt"),
    "ml_notebook": ("ipynb", "py"),
    "go_microservice": ("go",),
    "app_settings_config": ("toml", "ini", "json"),
    "api_docs_markdown": ("md", "txt"),
}
