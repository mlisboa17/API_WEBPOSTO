"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import {
  fetchGruposCadastro,
  fetchProdutos,
  fetchProduto,
  createProduto,
  updateProduto,
  produtoPrecoVenda,
  produtoPrecoCusto,
  produtoCodigoGrupo,
  produtoSubgrupos,
} from "@/lib/produtos-api";
import type {
  GrupoCadastro,
  Produto,
  SituacaoProduto,
  TipoProdutoFiltro,
  ProdutoFormPayload,
} from "@/types/produtos";
import { fmtBRL, fmtBRLPreciso } from "@/lib/format";
import { RecifeClock } from "@/components/recife-clock";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import {
  CheckIcon,
  FilterIcon,
  FolderIcon,
  GridIcon,
  LayersIcon,
  ListFilterIcon,
  PackagePlusIcon,
  RefreshCwIcon,
  SearchIcon,
  TagIcon,
  SlidersHorizontalIcon,
} from "lucide-react";
import { toast } from "sonner";

export function ProdutosLive() {
  // Filtros principais
  const [pagina, setPagina] = useState(1);
  const [limite] = useState(30);
  const [descricao, setDescricao] = useState("");
  const [descInput, setDescInput] = useState("");
  const [situacao, setSituacao] = useState<SituacaoProduto>("todos");
  const [tipoProduto, setTipoProduto] = useState<TipoProdutoFiltro>("todos");
  const [subgrupoBusca, setSubgrupoBusca] = useState<string>("");

  // Grupos e Subgrupos selecionados
  const [grupos, setGrupos] = useState<GrupoCadastro[]>([]);
  const [gruposSelecionados, setGruposSelecionados] = useState<number[]>([]);
  const [subgruposSelecionados, setSubgruposSelecionados] = useState<number[]>([]);

  // Dados de produtos retornados
  const [loading, setLoading] = useState(true);
  const [produtosData, setProdutosData] = useState<{
    produtos: Produto[];
    total_paginas: number;
    total_registros: number;
  } | null>(null);
  const [loadingGrupos, setLoadingGrupos] = useState(true);

  // Controle do Formulário / Drawer CRUD
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [isPending, startTransition] = useTransition();

  // Estados dos campos do formulário
  const [formDescricao, setFormDescricao] = useState("");
  const [formDescricaoResumida, setFormDescricaoResumida] = useState("");
  const [formTipo, setFormTipo] = useState("P");
  const [formGrupoCodigo, setFormGrupoCodigo] = useState<string>("");
  const [formPrecoVenda, setFormPrecoVenda] = useState("");
  const [formPrecoCusto, setFormPrecoCusto] = useState("");
  const [formUnidadeVenda, setFormUnidadeVenda] = useState("UN");
  const [formCodigoBarras, setFormCodigoBarras] = useState("");
  const [formNcm, setFormNcm] = useState("00000000");
  const [formCstSaida, setFormCstSaida] = useState("060");
  const [formAtivo, setFormAtivo] = useState(true);

  // Carrega os grupos cadastrados
  const carregarGrupos = useCallback(async () => {
    setLoadingGrupos(true);
    try {
      const g = await fetchGruposCadastro();
      setGrupos(g);
    } catch (err) {
      console.error("Erro ao carregar grupos", err);
      toast.error("Não foi possível carregar os grupos de produto.");
    } finally {
      setLoadingGrupos(false);
    }
  }, []);

  // Carrega produtos baseados nos filtros ativos
  const carregarProdutos = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchProdutos({
        pagina,
        limite,
        descricao: descricao || undefined,
        grupos: gruposSelecionados.length ? gruposSelecionados : undefined,
        situacao,
        tipoProduto,
        subgrupos: subgruposSelecionados.length ? subgruposSelecionados : undefined,
      });
      setProdutosData({
        produtos: data.produtos ?? [],
        total_paginas: data.total_paginas ?? 1,
        total_registros: data.total_registros ?? 0,
      });
    } catch (err) {
      console.error("Erro ao carregar produtos", err);
      toast.error(err instanceof Error ? err.message : "Erro ao carregar produtos.");
    } finally {
      setLoading(false);
    }
  }, [pagina, limite, descricao, gruposSelecionados, situacao, tipoProduto, subgruposSelecionados]);

  // Carrega no Mount
  useEffect(() => {
    carregarGrupos();
  }, [carregarGrupos]);

  // Dispara recarga sempre que pagina ou filtros mudam
  useEffect(() => {
    carregarProdutos();
  }, [carregarProdutos]);

  // Handler para busca de texto (ao pressionar Enter)
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPagina(1);
    setDescricao(descInput);
  };

  // Limpa todos os filtros de grupo/subgrupo e texto
  const handleLimparFiltros = () => {
    setDescInput("");
    setDescricao("");
    setSituacao("todos");
    setTipoProduto("todos");
    setGruposSelecionados([]);
    setSubgruposSelecionados([]);
    setSubgrupoBusca("");
    setPagina(1);
    toast.info("Filtros redefinidos");
  };

  // Alterna grupo na seleção múltipla
  const toggleGrupo = (codigo: number) => {
    setPagina(1);
    setGruposSelecionados((prev) =>
      prev.includes(codigo) ? prev.filter((id) => id !== codigo) : [...prev, codigo]
    );
  };

  // Seleciona ou remove subgrupo do filtro por ID numérico direto
  const handleToggleSubgrupo = (sg: number) => {
    setPagina(1);
    setSubgruposSelecionados((prev) =>
      prev.includes(sg) ? prev.filter((id) => id !== sg) : [...prev, sg]
    );
  };

  // Abre form de criação de novo produto
  const handleNovoProduto = () => {
    setEditandoId(null);
    setFormDescricao("");
    setFormDescricaoResumida("");
    setFormTipo("P");
    if (grupos.length > 0) {
      setFormGrupoCodigo(String(grupos[0].codigo));
    } else {
      setFormGrupoCodigo("");
    }
    setFormPrecoVenda("");
    setFormPrecoCusto("");
    setFormUnidadeVenda("UN");
    setFormCodigoBarras("");
    setFormNcm("00000000");
    setFormCstSaida("060");
    setFormAtivo(true);
    setIsFormOpen(true);
  };

  // Abre form para edição de produto existente
  const handleEditarProduto = async (id: number) => {
    try {
      const p = await fetchProduto(id);
      setEditandoId(p.id);
      setFormDescricao(p.descricao || "");
      setFormDescricaoResumida("");
      setFormTipo(p.combustivel ? "C" : p.tipoProduto || p.tipo_produto || "P");
      
      const gCod = produtoCodigoGrupo(p);
      setFormGrupoCodigo(gCod != null ? String(gCod) : "");
      
      setFormPrecoVenda(String(produtoPrecoVenda(p) || ""));
      setFormPrecoCusto(String(produtoPrecoCusto(p) || ""));
      setFormUnidadeVenda(p.unidadeMedida || p.unidade_medida || "UN");
      
      const cb = p.codigoBarras || p.codigo_barra || "";
      setFormCodigoBarras(cb);
      
      setFormNcm(p.ncm || "00000000");
      setFormCstSaida(p.cstIcms || p.cst_icms || "060");
      setFormAtivo(p.ativo !== false);
      setIsFormOpen(true);
    } catch (err) {
      console.error("Erro ao buscar detalhes do produto", err);
      toast.error("Falha ao abrir edição do produto.");
    }
  };

  // Submete criação ou alteração
  const handleSalvarProduto = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formDescricao.trim()) {
      toast.warning("A descrição é obrigatória.");
      return;
    }
    if (!formGrupoCodigo) {
      toast.warning("Selecione um grupo de produtos.");
      return;
    }

    const payload: ProdutoFormPayload = {
      descricao: formDescricao.trim(),
      descricaoResumida: formFormValueOrUndefined(formDescricaoResumida),
      tipoProduto: formTipo,
      grupoCodigo: parseInt(formGrupoCodigo, 10),
      precoVenda: parseFloat(formPrecoVenda) || 0,
      precoCusto: parseFloat(formPrecoCusto) || 0,
      precoCompra: parseFloat(formPrecoCusto) || 0,
      unidadeCompra: formUnidadeVenda || "UN",
      unidadeVenda: formUnidadeVenda || "UN",
      codigoBarras: formFormValueOrUndefined(formCodigoBarras),
      codigoNcm: formNcm.trim() || "00000000",
      ativo: formAtivo,
      tributoIcms: {
        cstSaida: formCstSaida || "060",
        percentualIcmsSaida: 0,
        cstEntrada: "060",
        percentualIcmsEntrada: 0,
      },
    };

    setSaving(true);
    try {
      if (editandoId != null) {
        const res = await updateProduto(editandoId, payload);
        toast.success(res.mensagem || "Produto atualizado com sucesso!");
      } else {
        const res = await createProduto(payload);
        toast.success(res.mensagem || "Produto cadastrado na WebPosto!");
      }
      setIsFormOpen(false);
      carregarProdutos();
    } catch (err) {
      console.error("Erro ao salvar produto", err);
      toast.error(err instanceof Error ? err.message : "Falha ao gravar produto.");
    } finally {
      setSaving(false);
    }
  };

  const formFormValueOrUndefined = (val: string) => {
    const clean = val.trim();
    return clean === "" ? undefined : clean;
  };

  // Mapeamento de subgrupos baseados nos produtos listados (extração dinâmica em memória para o filtro rápido)
  const subgruposDisponiveis = useMemo(() => {
    if (!produtosData?.produtos) return [];
    const set = new Set<number>();
    for (const p of produtosData.produtos) {
      const sgs = produtoSubgrupos(p);
      for (const sg of sgs) set.add(sg);
    }
    return [...set].sort((a, b) => a - b);
  }, [produtosData?.produtos]);

  return (
    <div className="flex flex-1 flex-col gap-4 py-4 md:gap-6 md:py-6">
      {/* Omie Hero Banner com Relógio Recife sem Hydration Mismatch */}
      <Card className="omie-hero mx-4 lg:mx-6">
        <CardHeader className="pb-3">
          <CardTitle>Cadastro & Catálogo de Produtos</CardTitle>
          <CardDescription>
            Fuso <strong>America/Recife</strong> · <RecifeClock /> · Integração em tempo real via Quality API
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-4">
          <div className="text-sm text-cyan-100 font-medium">
            Gerencie o catálogo de itens do posto (combustíveis, lubrificantes, conveniência, etc) com preços da Tabela A e custos fiscais.
          </div>
          <Button
            onClick={handleNovoProduto}
            className="bg-emerald-500 hover:bg-emerald-600 text-black font-bold flex items-center gap-2"
          >
            <PackagePlusIcon className="size-4" />
            + Novo Produto
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 px-4 lg:px-6">
        {/* Coluna 1: Painel de Filtros Laterais */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="omie-card">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <FilterIcon className="size-4 text-cyan-400" />
                <CardTitle className="text-sm font-semibold">
                  Filtros Rápidos
                </CardTitle>
              </div>
              {(descInput ||
                situacao !== "todos" ||
                tipoProduto !== "todos" ||
                gruposSelecionados.length > 0 ||
                subgruposSelecionados.length > 0) && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-amber-400 hover:text-amber-500 p-0"
                  onClick={handleLimparFiltros}
                >
                  Limpar
                </Button>
              )}
            </CardHeader>
            <CardContent className="space-y-4 pt-2">
              {/* Pesquisa textual */}
              <form onSubmit={handleSearchSubmit} className="space-y-1.5">
                <Label htmlFor="desc" className="text-xs text-muted-foreground font-medium">Descrição / Código</Label>
                <div className="relative">
                  <Input
                    id="desc"
                    value={descInput}
                    onChange={(e) => setDescInput(e.target.value)}
                    placeholder="Buscar nome do produto..."
                    className="pr-8 h-9"
                  />
                  <button type="submit" className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-white">
                    <SearchIcon className="size-4" />
                  </button>
                </div>
              </form>

              {/* Situação */}
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground font-medium">Situação Cadastral</Label>
                <Select
                  value={situacao}
                  onValueChange={(val: "todos" | "ativos" | "inativos" | null) => {
                    if (val) {
                      setPagina(1);
                      setSituacao(val);
                    }
                  }}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos os registros</SelectItem>
                    <SelectItem value="ativos">Somente Ativos</SelectItem>
                    <SelectItem value="inativos">Somente Inativos</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Tipo de Produto */}
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground font-medium">Tipo do Item</Label>
                <Select
                  value={tipoProduto}
                  onValueChange={(val: TipoProdutoFiltro | null) => {
                    if (val) {
                      setPagina(1);
                      setTipoProduto(val);
                    }
                  }}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos os tipos</SelectItem>
                    <SelectItem value="combustivel">Combustíveis (Atalhos)</SelectItem>
                    <SelectItem value="P">Mercadoria (P)</SelectItem>
                    <SelectItem value="C">Combustíveis Cadastrados (C)</SelectItem>
                    <SelectItem value="S">Serviços (S)</SelectItem>
                    <SelectItem value="K">Kit / Combo (K)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Filtro por Múltiplos Grupos */}
          <Card className="omie-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <FolderIcon className="size-4 text-cyan-400" />
                Grupos ({gruposSelecionados.length} sel.)
              </CardTitle>
              <CardDescription className="text-xs">
                Selecione um ou mais grupos abaixo:
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              {loadingGrupos ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                </div>
              ) : (
                <div className="max-h-48 overflow-y-auto space-y-1 pr-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                  {grupos.map((g) => {
                    const isChecked = gruposSelecionados.includes(g.codigo);
                    return (
                      <div
                        key={g.codigo}
                        onClick={() => toggleGrupo(g.codigo)}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-xs cursor-pointer transition-colors ${
                          isChecked
                            ? "bg-cyan-950/40 text-cyan-300 border border-cyan-500/20"
                            : "hover:bg-white/[0.03] text-muted-foreground hover:text-white border border-transparent"
                        }`}
                      >
                        <div className="flex size-4 items-center justify-center shrink-0 border border-input rounded-[4px] data-[state=checked]:bg-primary">
                          {isChecked && <CheckIcon className="size-3 text-cyan-400" />}
                        </div>
                        <span className="truncate flex-1">{g.nome}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">({g.codigo})</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Filtro por Múltiplos Subgrupos */}
          <Card className="omie-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <LayersIcon className="size-4 text-cyan-400" />
                Subgrupos ({subgruposSelecionados.length} sel.)
              </CardTitle>
              <CardDescription className="text-xs">
                Mapeados nos produtos carregados:
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              {loading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                </div>
              ) : subgruposDisponiveis.length === 0 ? (
                <div className="text-xs text-muted-foreground py-2 text-center">
                  Nenhum subgrupo identificado na listagem atual
                </div>
              ) : (
                <div className="max-h-40 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
                  {subgruposDisponiveis.map((sg) => {
                    const isChecked = subgruposSelecionados.includes(sg);
                    return (
                      <div
                        key={sg}
                        onClick={() => handleToggleSubgrupo(sg)}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-xs cursor-pointer transition-colors ${
                          isChecked
                            ? "bg-cyan-950/40 text-cyan-300 border border-cyan-500/20"
                            : "hover:bg-white/[0.03] text-muted-foreground hover:text-white border border-transparent"
                        }`}
                      >
                        <div className="flex size-4 items-center justify-center shrink-0 border border-input rounded-[4px]">
                          {isChecked && <CheckIcon className="size-3 text-cyan-400" />}
                        </div>
                        <span className="font-mono flex-1">Subgrupo #{sg}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Coluna 2: Tabela de Produtos */}
        <div className="lg:col-span-3 space-y-4">
          <Card className="omie-card">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <GridIcon className="size-5 text-cyan-400" />
                  Tabela Geral de Itens
                </CardTitle>
                <CardDescription>
                  {produtosData ? (
                    <span>{produtosData.total_registros.toLocaleString("pt-BR")} produto(s) correspondente(s)</span>
                  ) : (
                    <span>Consultando catálogo...</span>
                  )}
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="icon-sm"
                onClick={carregarProdutos}
                disabled={loading}
                title="Sincronizar tabela"
              >
                <RefreshCwIcon className={`size-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </CardHeader>
            <CardContent className="pt-2">
              <div className="overflow-x-auto rounded-lg border border-white/5 bg-black/10">
                <Table className="min-w-[850px]">
                  <TableHeader className="bg-white/[0.01]">
                    <TableRow>
                      <TableHead className="w-20 font-bold">Cód. ID</TableHead>
                      <TableHead className="font-bold">Nome do Produto</TableHead>
                      <TableHead className="font-bold">Grupo</TableHead>
                      <TableHead className="font-bold">Tipo / Unid.</TableHead>
                      <TableHead className="font-bold text-center w-24">Situação</TableHead>
                      <TableHead className="font-bold text-right w-32">Preço Tabela A</TableHead>
                      <TableHead className="font-bold text-right w-32">Preço Custo</TableHead>
                      <TableHead className="font-bold text-right w-24">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="font-mono">
                    {loading ? (
                      Array.from({ length: 8 }).map((_, idx) => (
                        <TableRow key={idx}>
                          <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-48" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                          <TableCell className="text-center"><Skeleton className="h-5 w-16 mx-auto" /></TableCell>
                          <TableCell className="text-right"><Skeleton className="h-4 w-20 ml-auto" /></TableCell>
                          <TableCell className="text-right"><Skeleton className="h-4 w-20 ml-auto" /></TableCell>
                          <TableCell className="text-right"><Skeleton className="h-5 w-12 ml-auto" /></TableCell>
                        </TableRow>
                      ))
                    ) : !produtosData?.produtos || produtosData.produtos.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-muted-foreground p-8 font-sans">
                          Nenhum produto atende aos filtros definidos. Remova filtros ou busque novamente.
                        </TableCell>
                      </TableRow>
                    ) : (
                      produtosData.produtos.map((p) => {
                        const isAtivo = p.ativo !== false;
                        const pVenda = produtoPrecoVenda(p);
                        const pCusto = produtoPrecoCusto(p);
                        const gCod = produtoCodigoGrupo(p);
                        const gNome = p.nomeGrupo || p.nome_grupo || "";
                        const subSgs = produtoSubgrupos(p);
                        const tipo = p.tipoProduto || p.tipo_produto || (p.combustivel ? "C" : "P");

                        return (
                          <TableRow key={p.id} className="hover:bg-white/[0.02]">
                            <TableCell className="text-cyan-400 font-bold font-mono">{p.id}</TableCell>
                            <TableCell className="font-sans font-medium text-white max-w-xs truncate">
                              <div className="flex flex-col">
                                <span className="truncate" title={p.descricao}>{p.descricao}</span>
                                <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                                  {p.codigoBarras || p.codigo_barra ? (
                                    <span className="text-[10px] text-muted-foreground" title="EAN / Código Barras">
                                      EAN: {p.codigoBarras || p.codigo_barra}
                                    </span>
                                  ) : null}
                                  {p.ncm ? (
                                    <span className="text-[10px] text-muted-foreground border-l border-white/10 pl-1.5">
                                      NCM: {p.ncm}
                                    </span>
                                  ) : null}
                                  {subSgs.length > 0 ? (
                                    <span className="text-[10px] text-yellow-400 border-l border-white/10 pl-1.5 flex items-center gap-0.5">
                                      <LayersIcon className="size-2.5" /> sg: {subSgs.join(",")}
                                    </span>
                                  ) : null}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="font-sans text-xs text-muted-foreground max-w-[120px] truncate">
                              <span title={gNome || `Grupo #${gCod}`}>
                                {gNome || (gCod != null ? `Grupo #${gCod}` : "Sem Grupo")}
                              </span>
                            </TableCell>
                            <TableCell className="text-xs">
                              <div className="flex items-center gap-1">
                                <Badge variant="secondary" className="px-1 py-0 text-[10px] font-mono bg-white/[0.04] text-gray-300">
                                  {tipo}
                                </Badge>
                                <span className="text-muted-foreground">{p.unidadeMedida || p.unidade_medida || "UN"}</span>
                              </div>
                            </TableCell>
                            <TableCell className="text-center font-sans">
                              {isAtivo ? (
                                <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 bg-emerald-950/20 font-sans font-bold text-[11px] px-2 py-0.5">
                                  Ativo
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="border-red-500/30 text-red-400 bg-red-950/20 font-sans font-bold text-[11px] px-2 py-0.5">
                                  Inativo
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-right text-emerald-400 font-mono font-bold">
                              {fmtBRLPreciso(pVenda)}
                            </TableCell>
                            <TableCell className="text-right text-amber-200/90 font-mono">
                              {fmtBRLPreciso(pCusto)}
                            </TableCell>
                            <TableCell className="text-right font-sans">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs text-cyan-400 hover:text-cyan-300 font-bold hover:underline"
                                onClick={() => handleEditarProduto(p.id)}
                              >
                                Editar
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Paginação */}
              {produtosData && produtosData.total_paginas > 1 && (
                <div className="flex justify-between items-center mt-4 text-xs text-muted-foreground font-sans">
                  <div>
                    Página {pagina} de {produtosData.total_paginas} · Registros no filtro: {produtosData.total_registros}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPagina((prev) => Math.max(1, prev - 1))}
                      disabled={pagina <= 1 || loading}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPagina((prev) => Math.min(produtosData.total_paginas, prev + 1))}
                      disabled={pagina >= produtosData.total_paginas || loading}
                    >
                      Próxima
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Sheet Form/Drawer para Criar ou Editar Produto */}
      <Sheet open={isFormOpen} onOpenChange={setIsFormOpen}>
        <SheetContent side="right" className="sm:max-w-md w-full bg-zinc-950 border-l border-white/10">
          <SheetHeader>
            <SheetTitle className="text-cyan-300 font-bold text-lg">
              {editandoId != null ? `Editar Produto #${editandoId}` : "Novo Produto WebPosto"}
            </SheetTitle>
            <SheetDescription className="text-xs text-muted-foreground">
              Preencha os campos obrigatórios. O salvamento persistirá as informações diretamente no banco do WebPosto.
            </SheetDescription>
          </SheetHeader>

          <form onSubmit={handleSalvarProduto} className="space-y-4 py-4 font-sans max-h-[80vh] overflow-y-auto pr-1">
            {/* Descrição Principal */}
            <div className="space-y-1.5">
              <Label htmlFor="form-desc" className="text-xs font-bold text-gray-300">Descrição do Produto *</Label>
              <Input
                id="form-desc"
                required
                placeholder="Ex: ADITIVO RADIADOR ORBI 1L"
                value={formDescricao}
                onChange={(e) => setFormDescricao(e.target.value)}
                maxLength={120}
              />
            </div>

            {/* Descrição Resumida */}
            <div className="space-y-1.5">
              <Label htmlFor="form-resumida" className="text-xs font-bold text-gray-300">Descrição Resumida (Opcional)</Label>
              <Input
                id="form-resumida"
                placeholder="Ex: ADIT RAD ORBI 1L"
                value={formDescricaoResumida}
                onChange={(e) => setFormDescricaoResumida(e.target.value)}
              />
            </div>

            {/* Tipo de Cadastro */}
            <div className="space-y-1.5">
              <Label htmlFor="form-tipo" className="text-xs font-bold text-gray-300">Tipo de Produto *</Label>
              <Select value={formTipo} onValueChange={(val) => { if (val) setFormTipo(val); }}>
                <SelectTrigger id="form-tipo">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="P">P — Produto / Mercadoria</SelectItem>
                  <SelectItem value="C">C — Combustível</SelectItem>
                  <SelectItem value="S">S — Serviço</SelectItem>
                  <SelectItem value="K">K — Kit / Combo</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Grupo de Produto */}
            <div className="space-y-1.5">
              <Label htmlFor="form-grupo" className="text-xs font-bold text-gray-300">Grupo Associado *</Label>
              <Select value={formGrupoCodigo} onValueChange={(val) => { if (val) setFormGrupoCodigo(val); }}>
                <SelectTrigger id="form-grupo">
                  <SelectValue placeholder="Selecione um grupo..." />
                </SelectTrigger>
                <SelectContent>
                  {grupos.map((g) => (
                    <SelectItem key={g.codigo} value={String(g.codigo)}>
                      {g.nome} ({g.codigo})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Preço de Venda */}
              <div className="space-y-1.5">
                <Label htmlFor="form-venda" className="text-xs font-bold text-gray-300">Preço de Venda (A) *</Label>
                <Input
                  id="form-venda"
                  type="number"
                  step="0.0001"
                  min="0"
                  required
                  placeholder="0.0000"
                  value={formPrecoVenda}
                  onChange={(e) => setFormPrecoVenda(e.target.value)}
                />
              </div>

              {/* Preço de Custo */}
              <div className="space-y-1.5">
                <Label htmlFor="form-custo" className="text-xs font-bold text-gray-300">Preço de Custo</Label>
                <Input
                  id="form-custo"
                  type="number"
                  step="0.0001"
                  min="0"
                  placeholder="0.0000"
                  value={formPrecoCusto}
                  onChange={(e) => setFormPrecoCusto(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Unidade de Venda */}
              <div className="space-y-1.5">
                <Label htmlFor="form-unidade" className="text-xs font-bold text-gray-300">Unidade de Medida</Label>
                <Input
                  id="form-unidade"
                  maxLength={6}
                  value={formUnidadeVenda}
                  onChange={(e) => setFormUnidadeVenda(e.target.value)}
                />
              </div>

              {/* CST ICMS */}
              <div className="space-y-1.5">
                <Label htmlFor="form-cst" className="text-xs font-bold text-gray-300">CST ICMS Saída</Label>
                <Input
                  id="form-cst"
                  maxLength={3}
                  value={formCstSaida}
                  onChange={(e) => setFormCstSaida(e.target.value)}
                />
              </div>
            </div>

            {/* Código NCM e Barras */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="form-ncm" className="text-xs font-bold text-gray-300">NCM *</Label>
                <Input
                  id="form-ncm"
                  maxLength={8}
                  required
                  value={formNcm}
                  onChange={(e) => setFormNcm(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="form-barras" className="text-xs font-bold text-gray-300">Código de Barras (EAN)</Label>
                <Input
                  id="form-barras"
                  placeholder="Opcional"
                  value={formCodigoBarras}
                  onChange={(e) => setFormCodigoBarras(e.target.value)}
                />
              </div>
            </div>

            {/* Checkbox Ativo */}
            <div className="flex items-center gap-2 pt-2">
              <Checkbox
                id="form-ativo"
                checked={formAtivo}
                onCheckedChange={(checked) => setFormAtivo(checked === true)}
              />
              <Label htmlFor="form-ativo" className="text-xs font-medium text-gray-300 cursor-pointer">
                Produto Ativo para Vendas e Pista
              </Label>
            </div>

            <div className="flex gap-3 pt-4 border-t border-white/5">
              <Button
                type="submit"
                disabled={saving}
                className="bg-emerald-500 hover:bg-emerald-600 text-black font-bold flex-1"
              >
                {saving ? "Salvando na Quality..." : "Salvar na WebPosto"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsFormOpen(false)}
                disabled={saving}
                className="border-white/10 text-gray-300"
              >
                Cancelar
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  );
}
