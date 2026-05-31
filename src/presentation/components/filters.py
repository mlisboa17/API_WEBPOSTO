import reflex as rx
from datetime import date
from typing import List

"""Reusable filter components: RangeFilter and MultiSelectFilter for executive UI."""


def RangeFilter(*, value_from: date | None = None, value_to: date | None = None, on_change=None) -> rx.Component:
    class _Local(rx.State):
        vfrom: date | None = value_from
        vto: date | None = value_to

        def set_from(self, v: date | None):
            self.vfrom = v
            if on_change:
                on_change()

        def set_to(self, v: date | None):
            self.vto = v
            if on_change:
                on_change()

    return rx.hstack(
        rx.vstack(rx.text('Data Início', size='xs'), rx.date_picker(value=_Local.vfrom, on_change=_Local.set_from)),
        rx.vstack(rx.text('Data Fim', size='xs'), rx.date_picker(value=_Local.vto, on_change=_Local.set_to)),
        spacing='4', width='100%'
    )


def MultiSelectFilter(*, label: str, options: List[str], value: List[str] | None = None, on_change=None) -> rx.Component:
    class _Local(rx.State):
        val: List[str] = value or []

        def toggle(self, v: str):
            if v in self.val:
                self.val = [x for x in self.val if x != v]
            else:
                self.val = self.val + [v]
            if on_change:
                on_change()

    chips = [rx.tag(o, on_click=lambda _, o=o: _Local.toggle(o), variant='subtle') for o in options]
    return rx.vstack(rx.text(label, size='sm'), rx.hstack(*chips, spacing='2'))
