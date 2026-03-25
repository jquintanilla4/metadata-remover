.PHONY: run build app typecheck clean

run:
	npm start

build:
	npm run package

app: build
	npm run make

typecheck:
	npm run typecheck

clean:
	rm -rf .webpack/ out/
