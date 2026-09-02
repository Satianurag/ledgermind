.PHONY: web-install smoke-ui sync smoke-vertex reset seed demo eval test lint ui install-npm verify-prd bootstrap-onchain prerun mcp-exercise langfuse-up setup-acp

sync:
	uv sync --all-extras

smoke-vertex:
	uv run python scripts/smoke-vertex.py

bootstrap-onchain:
	IS_TESTNET=true PYTHONPATH=. uv run python scripts/bootstrap_onchain.py

setup-acp:
	IS_TESTNET=true bash scripts/setup_acp.sh

prerun:
	IS_TESTNET=true PYTHONPATH=. uv run python scripts/prerun_settlement.py

reset:
	uv run python demo/reset_demo.py

seed:
	PYTHONPATH=. uv run python demo/seed_case_2214.py

demo: reset seed
	bash scripts/demo.sh

eval:
	PYTHONPATH=. uv run python eval/run_utility.py


mcp-exercise:
	uv run python scripts/exercise_mcp.py

langfuse-up:
	docker compose -f docker-compose.langfuse.yml up -d

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check packages/python tests demo agents onchain ui scripts

ui:
	uv run uvicorn ui.app:app --host 0.0.0.0 --port 8787

install-npm:
	cd packages/npm/ledgermind && npm install

verify-pins:
	uv pip install --dry-run "langgraph==1.2.11" "sibyl-memory-langgraph==0.1.1" 2>&1 || true

verify-prd:
	uv run python scripts/verify_prd.py

smoke-ui:
	bash scripts/smoke_ui.sh

web-install:
	cd web && npm install
