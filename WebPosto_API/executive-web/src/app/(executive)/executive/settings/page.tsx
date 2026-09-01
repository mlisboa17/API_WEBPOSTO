"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bell,
  Settings,
  RefreshCcw,
  Save,
  User,
  Building2,
  Clock,
  AlertTriangle,
  Mail,
  MessageSquare,
  Smartphone,
  Check,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Select } from "@/components/ui/select";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { ClearBrowserCacheButton } from "@/components/executive/clear-browser-cache-button";
import { cn } from "@/lib/utils";

interface NotificationProfile {
  user_id: string;
  user_name: string;
  role: string;
  empresas_autorizadas: number[];
  severidades_autorizadas: string[];
  categorias_autorizadas: string[];
  renotification_interval_min: number;
  notification_channels: string[];
  active: boolean;
}

interface AlertSummary {
  total_pendentes: number;
  criticos: number;
  medios: number;
  baixos: number;
  impacto_total_rs: number;
  aguardando_renotificacao: number;
  thresholds: Record<string, number>;
  renotification_intervals: Record<string, string>;
}

const ROLES = [
  { value: "diretor", label: "Diretor Executivo" },
  { value: "gerente_compras", label: "Gerente de Compras" },
  { value: "gerente_pista", label: "Gerente de Pista" },
  { value: "analista", label: "Analista Financeiro" },
];

const EMPRESAS = [
  { value: "5555", label: "AP Casa Caiada" },
  { value: "11495", label: "Posto VIP" },
  { value: "74014", label: "Posto Real / Doze" },
];

const SEVERIDADES = [
  { value: "CRITICO", label: "Critico (> R$ 3.000)", color: "text-red-400" },
  { value: "MEDIO", label: "Medio (R$ 500 - 3.000)", color: "text-amber-400" },
  { value: "BAIXO", label: "Baixo (< R$ 500)", color: "text-slate-400" },
];

const CATEGORIAS = [
  { value: "QUEBRA_CAIXA", label: "Quebra de Caixa" },
  { value: "ABASTECIMENTO_RETIDO", label: "Abastecimento Retido" },
  { value: "GIRO_CAIXA", label: "Giro de Caixa" },
  { value: "DESVIO_TANQUE", label: "Desvio de Tanque" },
  { value: "PRECO_COMBUSTIVEL", label: "Preco Combustivel" },
  { value: "ESTOQUE_CRITICO", label: "Estoque Critico" },
  { value: "MARGEM_NEGATIVA", label: "Margem Negativa" },
];

const RENOTIFICATION_OPTIONS = [
  { value: "15", label: "15 minutos" },
  { value: "30", label: "30 minutos" },
  { value: "60", label: "1 hora" },
  { value: "120", label: "2 horas" },
];

const CHANNELS = [
  { id: "app", label: "Notificacao no App", icon: Smartphone },
  { id: "email", label: "Email", icon: Mail },
  { id: "whatsapp", label: "WhatsApp", icon: MessageSquare },
];

export default function NotificationSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  
  const [profile, setProfile] = useState<NotificationProfile>({
    user_id: "usr_001",
    user_name: "Admin Lisboa",
    role: "diretor",
    empresas_autorizadas: [5555, 11495, 74014],
    severidades_autorizadas: ["CRITICO", "MEDIO", "BAIXO"],
    categorias_autorizadas: CATEGORIAS.map(c => c.value),
    renotification_interval_min: 30,
    notification_channels: ["app", "email"],
    active: true,
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryRes, profileRes] = await Promise.all([
        fetch("/api/proxy/executive/alerts/engine/summary"),
        fetch(`/api/proxy/executive/alerts/settings/profile?userId=${encodeURIComponent(profile.user_id)}`),
      ]);
      if (summaryRes.ok) {
        setSummary((await summaryRes.json()) as AlertSummary);
      }
      if (profileRes.ok) {
        const body = (await profileRes.json()) as {
          success?: boolean;
          data?: NotificationProfile;
        };
        const saved = body?.data;
        if (saved?.user_id) {
          setProfile((prev) => ({
            user_id: saved.user_id,
            user_name: saved.user_name || prev.user_name,
            role: saved.role || "diretor",
            empresas_autorizadas: saved.empresas_autorizadas || [],
            severidades_autorizadas: saved.severidades_autorizadas || [],
            categorias_autorizadas: saved.categorias_autorizadas || [],
            renotification_interval_min: saved.renotification_interval_min || 30,
            notification_channels: saved.notification_channels || ["app"],
            active: saved.active !== false,
          }));
        }
      }
    } catch (err) {
      console.error("[NotificationSettings] Error:", err);
    } finally {
      setLoading(false);
    }
  }, [profile.user_id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch("/api/proxy/executive/alerts/settings/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      const body = (await response.json().catch(() => null)) as {
        success?: boolean;
        data?: NotificationProfile;
        error?: string;
        message?: string;
      } | null;
      if (!response.ok || body?.success === false) {
        throw new Error(body?.error || "Falha ao persistir configurações");
      }
      if (body?.data?.user_id) {
        setProfile((prev) => ({
          ...prev,
          ...body.data!,
          empresas_autorizadas: body.data!.empresas_autorizadas || prev.empresas_autorizadas,
          severidades_autorizadas: body.data!.severidades_autorizadas || prev.severidades_autorizadas,
          categorias_autorizadas: body.data!.categorias_autorizadas || prev.categorias_autorizadas,
          notification_channels: body.data!.notification_channels || prev.notification_channels,
        }));
      }
      alert(body?.message || "Configurações salvas com sucesso!");
    } catch (err) {
      console.error("[NotificationSettings] Save error:", err);
      alert(err instanceof Error ? err.message : "Erro ao salvar configurações");
    } finally {
      setSaving(false);
    }
  };

  const toggleEmpresa = (codigo: number) => {
    setProfile(prev => ({
      ...prev,
      empresas_autorizadas: prev.empresas_autorizadas.includes(codigo)
        ? prev.empresas_autorizadas.filter(e => e !== codigo)
        : [...prev.empresas_autorizadas, codigo],
    }));
  };

  const toggleSeveridade = (sev: string) => {
    setProfile(prev => ({
      ...prev,
      severidades_autorizadas: prev.severidades_autorizadas.includes(sev)
        ? prev.severidades_autorizadas.filter(s => s !== sev)
        : [...prev.severidades_autorizadas, sev],
    }));
  };

  const toggleCategoria = (cat: string) => {
    setProfile(prev => ({
      ...prev,
      categorias_autorizadas: prev.categorias_autorizadas.includes(cat)
        ? prev.categorias_autorizadas.filter(c => c !== cat)
        : [...prev.categorias_autorizadas, cat],
    }));
  };

  const toggleChannel = (channel: string) => {
    setProfile(prev => ({
      ...prev,
      notification_channels: prev.notification_channels.includes(channel)
        ? prev.notification_channels.filter(c => c !== channel)
        : [...prev.notification_channels, channel],
    }));
  };

  if (loading) {
    return (
      <div className="p-4 lg:p-8 max-w-[1200px] mx-auto space-y-6">
        <Skeleton className="h-12 w-64 bg-slate-800" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 bg-slate-800" />)}
        </div>
        <Skeleton className="h-96 bg-slate-800" />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 max-w-[1200px] mx-auto space-y-6">
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Bell className="text-cyan-400" />
            Configuracao de Notificacoes
            <InfoTooltip content="Configure perfis de notificacao, niveis de criticidade e canais de alerta para cada usuario." />
          </h1>
          <p className="text-slate-500 text-sm">
            Matriz de Criticidade e Escalacao de Alertas Proativos
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <ClearBrowserCacheButton variant="inline" />
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} />
            Atualizar
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving}
            className="bg-cyan-500 hover:bg-cyan-600 text-white"
          >
            <Save size={14} className="mr-2" />
            {saving ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </header>

      {/* Resumo de Alertas */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Alertas Criticos</p>
                  <p className="text-2xl font-bold text-red-400">{summary.criticos}</p>
                  <p className="text-xs text-slate-500">
                    {summary.aguardando_renotificacao} aguardando re-notificacao
                  </p>
                </div>
                <div className="p-2 bg-red-500/10 rounded-lg">
                  <AlertTriangle className="text-red-400" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Alertas Medios</p>
                  <p className="text-2xl font-bold text-amber-400">{summary.medios}</p>
                </div>
                <div className="p-2 bg-amber-500/10 rounded-lg">
                  <Clock className="text-amber-400" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Alertas Baixos</p>
                  <p className="text-2xl font-bold text-slate-300">{summary.baixos}</p>
                </div>
                <div className="p-2 bg-slate-500/10 rounded-lg">
                  <Bell className="text-slate-400" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400">Impacto Total</p>
                  <p className="text-2xl font-bold text-cyan-400">
                    {summary.impacto_total_rs.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                  </p>
                </div>
                <div className="p-2 bg-cyan-500/10 rounded-lg">
                  <Settings className="text-cyan-400" size={20} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Matriz de Criticidade */}
      <Card className="bg-slate-800/50 border-slate-700/50">
        <CardHeader>
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-400" />
            Matriz de Criticidade
          </CardTitle>
          <CardDescription>
            Thresholds de impacto financeiro para classificacao automatica
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
              <div className="flex items-center gap-2 mb-2">
                <Badge className="bg-red-500/20 text-red-300">CRITICO</Badge>
              </div>
              <p className="text-2xl font-bold text-red-400">
                {"> R$ 3.000,00"}
              </p>
              <p className="text-xs text-slate-400 mt-2">
                Requer aprovacao imediata. Re-notificacao ativa ate reconhecimento.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <div className="flex items-center gap-2 mb-2">
                <Badge className="bg-amber-500/20 text-amber-300">MEDIO</Badge>
              </div>
              <p className="text-2xl font-bold text-amber-400">
                R$ 500 - R$ 3.000
              </p>
              <p className="text-xs text-slate-400 mt-2">
                Notificacao operacional para gerentes e analistas.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-500/10 border border-slate-500/30">
              <div className="flex items-center gap-2 mb-2">
                <Badge className="bg-slate-500/20 text-slate-300">BAIXO</Badge>
              </div>
              <p className="text-2xl font-bold text-slate-400">
                {"< R$ 500,00"}
              </p>
              <p className="text-xs text-slate-400 mt-2">
                Incluido no resumo executivo diario.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuracao do Perfil */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Perfil do Usuario */}
        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <User size={18} className="text-cyan-400" />
              Perfil do Usuario
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 block mb-2">Nome</label>
              <input
                type="text"
                value={profile.user_name}
                onChange={(e) => setProfile(prev => ({ ...prev, user_name: e.target.value }))}
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-md text-white text-sm"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-2">Funcao</label>
              <Select
                value={profile.role}
                onChange={(value) => setProfile(prev => ({ ...prev, role: value }))}
                options={ROLES}
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-2">
                Frequencia de Re-notificacao (Alertas Criticos)
              </label>
              <Select
                value={profile.renotification_interval_min.toString()}
                onChange={(value) => setProfile(prev => ({ ...prev, renotification_interval_min: parseInt(value) }))}
                options={RENOTIFICATION_OPTIONS}
              />
              <p className="text-xs text-slate-500 mt-1">
                Alertas criticos serao re-enviados neste intervalo ate serem reconhecidos.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Empresas Autorizadas */}
        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Building2 size={18} className="text-cyan-400" />
              Empresas Autorizadas
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {EMPRESAS.map((emp) => (
              <button
                key={emp.value}
                onClick={() => toggleEmpresa(parseInt(emp.value))}
                className={cn(
                  "w-full flex items-center justify-between p-3 rounded-lg border transition-colors",
                  profile.empresas_autorizadas.includes(parseInt(emp.value))
                    ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"
                    : "bg-slate-700/30 border-slate-600 text-slate-400 hover:bg-slate-700/50"
                )}
              >
                <span>{emp.label}</span>
                {profile.empresas_autorizadas.includes(parseInt(emp.value)) && (
                  <Check size={16} className="text-cyan-400" />
                )}
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Severidades */}
        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <AlertTriangle size={18} className="text-amber-400" />
              Niveis de Severidade
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {SEVERIDADES.map((sev) => (
              <button
                key={sev.value}
                onClick={() => toggleSeveridade(sev.value)}
                className={cn(
                  "w-full flex items-center justify-between p-3 rounded-lg border transition-colors",
                  profile.severidades_autorizadas.includes(sev.value)
                    ? "bg-cyan-500/10 border-cyan-500/30"
                    : "bg-slate-700/30 border-slate-600 hover:bg-slate-700/50"
                )}
              >
                <span className={sev.color}>{sev.label}</span>
                {profile.severidades_autorizadas.includes(sev.value) && (
                  <Check size={16} className="text-cyan-400" />
                )}
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Canais de Notificacao */}
        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Bell size={18} className="text-cyan-400" />
              Canais de Notificacao
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {CHANNELS.map((channel) => {
              const Icon = channel.icon;
              return (
                <button
                  key={channel.id}
                  onClick={() => toggleChannel(channel.id)}
                  className={cn(
                    "w-full flex items-center justify-between p-3 rounded-lg border transition-colors",
                    profile.notification_channels.includes(channel.id)
                      ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"
                      : "bg-slate-700/30 border-slate-600 text-slate-400 hover:bg-slate-700/50"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Icon size={16} />
                    <span>{channel.label}</span>
                  </div>
                  {profile.notification_channels.includes(channel.id) && (
                    <Check size={16} className="text-cyan-400" />
                  )}
                </button>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Categorias de Alerta */}
      <Card className="bg-slate-800/50 border-slate-700/50">
        <CardHeader>
          <CardTitle className="text-lg text-white">Categorias de Alerta Autorizadas</CardTitle>
          <CardDescription>
            Selecione quais tipos de alertas este perfil pode receber
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {CATEGORIAS.map((cat) => (
              <button
                key={cat.value}
                onClick={() => toggleCategoria(cat.value)}
                className={cn(
                  "flex items-center justify-between p-3 rounded-lg border transition-colors text-sm",
                  profile.categorias_autorizadas.includes(cat.value)
                    ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"
                    : "bg-slate-700/30 border-slate-600 text-slate-400 hover:bg-slate-700/50"
                )}
              >
                <span>{cat.label}</span>
                {profile.categorias_autorizadas.includes(cat.value) && (
                  <Check size={14} className="text-cyan-400" />
                )}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
