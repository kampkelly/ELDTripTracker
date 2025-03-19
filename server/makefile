# Set of commands to manage migrations
activate-env:
	@echo "activating env..."
	. venv/bin/activate

# Set of commands to start-app
install:
	@echo "Installing packages..."
	pip-compile requirements.in && pip-sync requirements.txt && python sync_requirements.py

# make make-migration MSG="your_migration_message"
make-migration:
	@echo "Making migrations."
	python manage.py makemigrations --name $(MSG)
	
run-migration:
	@echo "Run migrations."
	python manage.py migrate
	
# make undo-migration APP_NAME="your_migration_message" NO=0001
undo-migration:
	@echo "Run migrations."
	python manage.py migrate $(APP_NAME) $(NO)
	
start-app:
	@echo "Starting app on port ${PORT}..."
	python manage.py runserver

lint:
	@echo "Checking lint errors"
	black . && isort . --profile black && flake8 .

typings:
	@echo "Checking type errors"
	mypy
