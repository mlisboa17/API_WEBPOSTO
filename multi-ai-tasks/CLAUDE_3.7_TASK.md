🔄 CLAUDE 3.7 - INSTRUÇÕES TÉCNICAS DETALHADAS
===============================================

OBJETIVO PRINCIPAL:
Architecture & DDD para implementar lógica de negócio isolada de externos.

📊 ESCOPO (40% do projeto):
- 24-32 horas de desenvolvimento
- 4 componentes principais
- DDD compliance total

---

## COMPONENTE 1: Domain Model - Agregado Empresa

ARQUIVO: src/domain/entities/empresa.py

### Classe: Empresa (AggregateRoot)

```python
class Empresa(AggregateRoot):
    """
    Root Aggregate representando uma empresa (tenant).
    
    Responsabilidades:
    - Manter colecção de Centros de Custo
    - Orquestrar sincronização
    - Emitir eventos de domínio
    - Validar invariantes de negócio
    """
    
    empresa_id: EmpresaID
    nome: str
    centros_custo: List[CentroCusto]
    config_rateio: RateiConfiguracao
    eventos_nao_commitados: List[DomainEvent]
    
    def __init__(self, empresa_id: str, nome: str, config: RateiConfiguracao):
        self.empresa_id = EmpresaID(valor=empresa_id)
        self.nome = nome
        self.centros_custo = []
        self.config_rateio = config
        self.eventos_nao_commitados = []
        
        # Emitir evento de criação
        self._emit_event(EmpresaCriadaEvent(empresa_id=empresa_id, timestamp=datetime.utcnow()))
    
    def adicionar_centro_custo(self, cc: CentroCusto):
        """
        Validar e adicionar novo Centro de Custo.
        
        Validações:
        - CC não existe duplicado
        - Percentual válido (0-100)
        - Soma de percentuais ≤ 100 (se config exigir)
        """
        if any(c.centro_custo_id.valor == cc.centro_custo_id.valor 
               for c in self.centros_custo):
            raise DomainException("Centro de Custo já existe")
        
        self.centros_custo.append(cc)
        self._emit_event(CentroCustoAdicionadoEvent(
            empresa_id=self.empresa_id.valor,
            cc_id=cc.centro_custo_id.valor
        ))
    
    def sincronizar(self, dados: List[Dict]) -> List[Rateio]:
        """
        Orquestrar sincronização:
        
        1. Validar cada lancamento
        2. Executar rateio via ValidadorRateio
        3. Detectar divergências
        4. Emitir eventos de resultado
        
        Retorna: Lista de Rateios criados
        """
        pass
    
    def _emit_event(self, event: DomainEvent):
        """Adicionar evento não-commitado."""
        self.eventos_nao_commitados.append(event)
```

---

## COMPONENTE 2: Value Objects & Entities

ARQUIVO: src/domain/value_objects/ + src/domain/entities/

### Value Objects (Imutáveis):

```python
class EmpresaID(ValueObject):
    """Identidade única da empresa."""
    valor: str
    
    @field_validator('valor')
    def validar_formato(cls, v):
        if not isinstance(v, str) or len(v) > 50:
            raise ValueError("Formato inválido")
        return v


class CentroCustoID(ValueObject):
    """Identidade do centro de custo."""
    valor: str


class ValorMonetario(ValueObject):
    """Representa valores financeiros com precisão."""
    valor: Decimal
    moeda: str = "BRL"
    
    def __add__(self, outro: 'ValorMonetario') -> 'ValorMonetario':
        return ValorMonetario(valor=self.valor + outro.valor, moeda=self.moeda)


class RateioCentroCusto(ValueObject):
    """Composição de rateio para um CC específico."""
    centro_custo_id: CentroCustoID
    percentual: Decimal  # 0-100
    valor: ValorMonetario
    
    def validar(self):
        if not 0 <= self.percentual <= 100:
            raise ValueError("Percentual inválido")
        if self.valor.valor <= 0:
            raise ValueError("Valor deve ser positivo")
```

### Entity: CentroCusto

```python
class CentroCusto(Entity):
    """
    Entity dentro do agregado Empresa.
    Cada empresa pode ter múltiplos CCs.
    """
    centro_custo_id: CentroCustoID
    nome: str
    percentual_padrao: Decimal
    ativo: bool = True
    timestamp_criacao: datetime
```

### Entity: Rateio

```python
class Rateio(Entity):
    """
    Entity representando divisão de um Lancamento.
    Agregado: Empresa
    """
    rateio_id: str
    lancamento_id: str
    centros_custo: List[RateioCentroCusto]
    valor_total: ValorMonetario
    timestamp_criacao: datetime
    
    def validar_soma(self):
        """Validar se soma de rateios = valor_total"""
        soma = sum(r.valor.valor for r in self.centros_custo)
        if soma != self.valor_total.valor:
            raise DomainException(
                f"Soma de rateios ({soma}) ≠ valor_total ({self.valor_total.valor})"
            )
```

---

## COMPONENTE 3: Domain Service - Validador Rateio

ARQUIVO: src/domain/services/validador_rateio.py

```python
class ValidadorRateio:
    """
    Domain Service que valida rateios.
    
    Responsabilidades:
    - Validar soma de percentuais = 100%
    - Validar soma de valores = total
    - Detectar CCs ausentes
    - Aplicar regras customizadas por empresa
    """
    
    def __init__(self, config: RateiConfiguracao):
        self.config = config
    
    def validar(self, rateio: Rateio) -> Tuple[bool, Optional[str]]:
        """
        Validar integridade do rateio.
        
        Retorna: (valido, erro_message)
        """
        # 1. Validar soma de valores
        # 2. Validar soma de percentuais (se aplicável)
        # 3. Aplicar regras customizadas
        # 4. Retornar resultado
        pass
```

---

## COMPONENTE 4: Use Case - Orquestrador de Sincronização

ARQUIVO: src/application/usecases/sync_all.py

```python
class OrquestradorSincronizacaoMultiTenant:
    """
    Use Case: Sincronizar dados de múltiplas empresas.
    
    Orquestra:
    1. Recuperar configs de todas as empresas
    2. Para cada empresa: executar sincronização
    3. Coletar eventos de divergência
    4. Persistir resultados
    5. Emitir eventos de conclusão
    """
    
    def __init__(self, 
                 client_factory: WebPostoClientFactory,
                 empresa_repository: EmpresaRepository,
                 event_store: EventStore):
        self.client_factory = client_factory
        self.empresa_repo = empresa_repository
        self.event_store = event_store
    
    async def executar(self) -> SincronizacaoResultado:
        """
        Sincronizar todas as empresas em paralelo.
        
        Passos:
        1. event_store.emit(SyncStartedEvent)
        2. Para cada empresa:
           a. Recuperar lancamentos
           b. Calcular rateios
           c. Validar com ValidadorRateio
           d. Persistir em MongoDB
        3. event_store.emit(SyncCompletedEvent)
        4. Retornar resultado consolidado
        """
        pass
```

---

## TESTES OBRIGATÓRIOS

ARQUIVO: tests/unit/domain/test_claude_tasks.py

```python
# TEST 1: Empresa Aggregate
async def test_empresa_creation():
    """Criar empresa e validar invariantes"""
    
# TEST 2: Centro de Custo
async def test_adicionar_centro_custo():
    """Adicionar CC e validar eventos"""
    
# TEST 3: Validador Rateio
async def test_validador_soma_100_porcento():
    """Validar que soma de percentuais = 100%"""
    
# TEST 4: Rateio Entity
async def test_rateio_soma_valores():
    """Validar que soma de valores = total"""
    
# TEST 5: Value Objects Imutáveis
async def test_value_objects_imutaveis():
    """Tentar modificar value object deve falhar"""
    
# TEST 6: Domain Events
async def test_domain_events_emitidos():
    """Validar que eventos foram emitidos"""
    
# TEST 7: Factory Pattern
async def test_factory_criacao_sincronizacao():
    """Factory cria instâncias corretas"""
```

---

## PYDANTIC V2.15 STRICT MODE

```python
from pydantic import BaseModel, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True)
    
    # Erros se:
    # - Tipo wrong (ex: "123" ao invés de 123)
    # - Campo extra não definido
    # - Campo obrigatório faltando
```

---

## VALIDAÇÃO DE SUCESSO

✅ Todas as entidades respeitam DDD
✅ Value Objects são imutáveis
✅ Domain Events emitidos corretamente
✅ Factory Pattern funcionando
✅ Unit tests com >90% coverage
✅ Inversão de Dependência implementada
✅ Pydantic v2.15 strict mode ativo

---

## PRÓXIMA ETAPA (Sincronização com GROK 4)

Quando CLAUDE terminar:
1. Compartilhar entidades Empresa e Rateio
2. GROK usará para gerar hashes e detectar anomalias
3. GROK integrará com AuditEngine

