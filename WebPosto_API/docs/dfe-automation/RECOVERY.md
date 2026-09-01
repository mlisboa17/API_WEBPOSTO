# Recuperação

- Timeout ou queda: o lease expira; NSU só muda se a importação persistiu.
- XML corrompido: quarentena, NSU não avança se o lote SEFAZ falhou.
- Duplicata: status DUPLICATE, original intacto.
- Duas execuções: a segunda recebe `LEASE_HELD`.
- Não zerar NSU. `reset_nsu` existente exige admin e confirmação explícita.
