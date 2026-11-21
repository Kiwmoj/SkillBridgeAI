from collections.abc import Callable
from typing import Any

from PyQt6.QtWidgets import QInputDialog

from apps.desktop.ui.pages.base import Page


def choose_record(page: Page, fetch: Callable[[], Any], title: str, label: str,
                  action: Callable[[Any], object]) -> None:
    def show(items: list[dict[str, Any]]) -> None:
        if not items:
            page.notify(f"No records to show: {title}.")
            return
        entries = [f"{item['id']} | {item.get(label) or 'Untitled'}" for item in items]
        selected, ok = QInputDialog.getItem(page.context.parent, title, "Select a record:", entries, editable=False)
        if ok:
            action(items[entries.index(selected)])

    page.run(fetch, show)


def edit_activity_dialog(page: Page, record: dict[str, Any] | None, roadmap_id: int | None = None) -> None:
    parent = page.context.parent
    details = record or {}
    title, ok = QInputDialog.getText(parent, "Learning activity", "Activity:", text=details.get("title", ""))
    if not ok:
        return
    states = ["not_started", "in_progress", "paused", "completed"]
    status, ok = QInputDialog.getItem(parent, "Learning activity", "Status:", states,
                                      states.index(details.get("status", "not_started")), editable=False)
    if not ok:
        return
    notes, ok = QInputDialog.getMultiLineText(parent, "Learning activity", "Notes:", details.get("notes") or "")
    if not ok:
        return
    payload = {"title": title, "status": status, "notes": notes,
               "roadmap_id": details.get("roadmap_id", roadmap_id)}
    backend = page.backend
    operation = (lambda: backend.update_activity(details["id"], payload)) if record else (
        lambda: backend.create_activity(payload)
    )
    page.run(operation, lambda _: page.notify("Learning activity saved."))
