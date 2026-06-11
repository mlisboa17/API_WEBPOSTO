# CASH NULL HARDENING — P0 · IA-2

Helpers adicionados em `cash_operations_service.py`:

- `safe_float(value, default=0.0)`
- `safe_int(value, default=0)`
- `_dec()` delega para `safe_float()`

Critério: nenhuma operação matemática ou sort falha com `None`, string vazia ou valor inválido.
