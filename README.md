cd path_to_your_project    # Change to your project directory
source venv/bin/activate  # Activate the virtual environment
poetry --version          # Now Poetry should work
poetry install --no-root

# Add a new dependency
poetry add fastapi

# Add a development dependency
poetry add --group dev pytest

# Run the interactive assistant
poetry run python main.py

# Ingest documents
poetry run python main.py --ingest data/algorithms/

# Run tests
poetry run pytest
