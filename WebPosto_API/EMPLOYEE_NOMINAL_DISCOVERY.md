# EMPLOYEE NOMINAL DISCOVERY — D02 · Agente 1

Janela ref: **7d** · {'inicio': '2026-06-02', 'fim': '2026-06-08'}

## Endpoints auditados

| Endpoint | Path | HTTP | Registros | Campos nome/CPF |
|---|---|---|---|---|
| FuncionarioRede | /INTEGRACAO/FUNCIONARIO_REDE | 401 | 0 | — |
| ConsultarFuncionario | /INTEGRACAO/CONSULTAR_FUNCIONARIO | 401 | 0 | — |
| Funcionario | /INTEGRACAO/FUNCIONARIO | 200 | 84 | cpf, funcionarioCodigo, funcionarioCodigoExterno, funcionarioReferencia, nome, ultimoUsuarioAlteracao |
| FuncionarioEmpresa | /INTEGRACAO/FUNCIONARIO_EMPRESA | 401 | 0 | — |
| FuncionarioMovimento | /INTEGRACAO/FUNCIONARIO_MOVIMENTO | 401 | 0 | — |
| ValeFuncionarioRede | /INTEGRACAO/VALE_FUNCIONARIO_REDE | 401 | 0 | — |
| Usuario | /INTEGRACAO/USUARIO | 200 | 58 | nome, usuarioCodigo |
| UsuarioEmpresaRede | /INTEGRACAO/USUARIO_EMPRESA_REDE | 401 | 0 | — |
| GrupoMeta | /INTEGRACAO/GRUPO_META | 200 | 3 | — |
| ProdutoMeta | /INTEGRACAO/PRODUTO_META | 200 | 22 | — |
| FechamentoCaixa | /INTEGRACAO/FECHAMENTO_CAIXA | 401 | 0 | — |

## Respostas

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Existe funcionarioNome? | **Sim** |
| 2 | Existe nome completo? | **Sim** |
| 3 | Existe CPF? | **Sim** |
| 4 | Existe matrícula? | **Não** |
| 5 | Existe apelido operacional? | **Não** |
| 6 | Existe status ativo? | **Sim** |

## Conclusão

/INTEGRACAO/FUNCIONARIO expõe nome/cpf/ativo — join por funcionarioCodigo; transacional permanece codigo-only

Endpoints **401/403**: /INTEGRACAO/FUNCIONARIO_REDE, /INTEGRACAO/CONSULTAR_FUNCIONARIO, /INTEGRACAO/FUNCIONARIO_EMPRESA, /INTEGRACAO/FUNCIONARIO_MOVIMENTO, /INTEGRACAO/VALE_FUNCIONARIO_REDE, /INTEGRACAO/USUARIO_EMPRESA_REDE, /INTEGRACAO/FECHAMENTO_CAIXA

Endpoints **com dados**: /INTEGRACAO/FUNCIONARIO, /INTEGRACAO/USUARIO, /INTEGRACAO/GRUPO_META, /INTEGRACAO/PRODUTO_META
