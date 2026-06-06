.PHONY: sync

sync:
	uv sync
	uv run python sync_from_label_studio.py
