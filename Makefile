install:
	poetry install

lint:
	poetry run pre-commit run -a

image:
	docker build -t iopac:latest .
