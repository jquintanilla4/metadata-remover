.PHONY: run build app typecheck clean legacy-run legacy-build

run:
	npm start

build:
	npm run package

app: build
	npm run make

typecheck:
	npm run typecheck

clean:
	rm -rf .webpack/ out/ build/ dist/ __pycache__/

legacy-run:
	uv run python app.py

legacy-build:
	uv sync --extra build
	uv run pyinstaller metadata_remover.spec --clean
