.PHONY: setup run ollama-start pull-model

setup:
	pip install -r requirements.txt

run:
	python -m src.main

ollama-start:
	ollama serve

pull-model:
	ollama pull llama3:8b-instruct-q4_K_M
