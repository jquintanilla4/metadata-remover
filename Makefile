.PHONY: run build app clean

run:
	uv run python app.py

build:
	uv sync --extra build
	uv run pyinstaller metadata_remover.spec --clean

app: build
	./build_app.sh

clean:
	rm -rf build/ dist/ __pycache__/
