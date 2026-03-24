.PHONY: run build clean

run:
	uv run python app.py

build:
	uv sync --extra build
	uv run pyinstaller metadata_remover.spec --clean

clean:
	rm -rf build/ dist/ __pycache__/
