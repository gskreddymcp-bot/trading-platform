.PHONY: backend frontend test docker clean

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest -q

docker:
	docker compose up --build

clean:
	rm -rf backend/.venv backend/.pytest_cache frontend/node_modules
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
