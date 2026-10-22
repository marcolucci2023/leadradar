"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { searchBusinesses, enrichAndScoreLead, sendLeadEmail, createCampaign, listCampaigns, getCampaign } from "@/lib/api";
import type { LeadResult } from "@/lib/api";

// ============================================================
// UI Components
// ============================================================

function ScoreBadge({ score, size = "sm" }: { score: number; size?: "sm" | "lg" }) {
  const config =
    score >= 70
      ? { bg: "bg-emerald-500/10 border-emerald-500/30", text: "text-emerald-300", dot: "bg-emerald-400" }
      : score >= 40
      ? { bg: "bg-yellow-500/10 border-yellow-500/30", text: "text-yellow-300", dot: "bg-yellow-400" }
      : { bg: "bg-red-500/10 border-red-500/30", text: "text-red-300", dot: "bg-red-400" };
  const sizeCls = size === "lg" ? "px-3 py-1.5 text-sm" : "px-2.5 py-1 text-xs";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-bold ${config.bg} ${config.text} ${sizeCls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {score}/100
    </span>
  );
}

function SafeLink({
  href,
  children,
  className,
}: {
  href?: string;
  children: ReactNode;
  className?: string;
}) {
  if (!href || (!href.startsWith("http://") && !href.startsWith("https://"))) {
    return <span className="text-gray-600">—</span>;
  }
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
      {children}
    </a>
  );
}

// ... le reste du fichier reste EXACTEMENT identique à la version précédente

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: string;
  label: string;
  value: string | number;
  accent: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3 transition-colors hover:border-gray-700">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${accent}`}>
        {icon}
      </div>
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-xl font-bold text-white">{value}</p>
      </div>
    </div>
  );
}

function Toast({
  toast,
  onClose,
}: {
  toast: { message: string; type: "success" | "error" | "info" } | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [toast, onClose]);

  if (!toast) return null;

  const config = {
    success: "bg-emerald-500/15 border-emerald-500/40 text-emerald-200",
    error: "bg-red-500/15 border-red-500/40 text-red-200",
    info: "bg-blue-500/15 border-blue-500/40 text-blue-200",
  }[toast.type];
  const icon = { success: "✅", error: "❌", info: "ℹ️" }[toast.type];

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border shadow-2xl backdrop-blur-sm max-w-sm ${config}`}
    >
      <span>{icon}</span>
      <p className="text-sm font-medium flex-1">{toast.message}</p>
      <button onClick={onClose} className="text-xs opacity-60 hover:opacity-100" aria-label="Fermer">
        ✕
      </button>
    </div>
  );
}

// ============================================================
// Main
// ============================================================

type Filter = "all" | "unanalyzed" | "analyzed" | "hot";
type SortKey = "default" | "score" | "name";

export default function DashboardPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [city, setCity] = useState("Casablanca");
  const [businessType, setBusinessType] = useState("restaurant");
  const [radius, setRadius] = useState(5000);
  const [leads, setLeads] = useState<LeadResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyzingIds, setAnalyzingIds] = useState<Set<string>>(new Set());
  const analyzingRef = useRef<Set<string>>(new Set());
  const [searchInfo, setSearchInfo] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [sortBy, setSortBy] = useState<SortKey>("default");
  const [activeTab, setActiveTab] = useState<"search" | "campaigns">("search");
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [campaignName, setCampaignName] = useState("");
  const [batchProgress, setBatchProgress] = useState<{ done: number; total: number } | null>(null);
  const batchCancelRef = useRef(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(
    null
  );
    const [sendingIds, setSendingIds] = useState<Set<string>>(new Set());

  const showToast = useCallback(
    (message: string, type: "success" | "error" | "info" = "info") => {
      setToast({ message, type });
    },
    []
  );

  // Auth + config persistence
  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    if (!savedToken) {
      router.replace("/login");
      return;
    }
    setToken(savedToken);
    const savedConfig = localStorage.getItem("searchConfig");
    if (savedConfig) {
      try {
        const cfg = JSON.parse(savedConfig);
        if (cfg.city) setCity(cfg.city);
        if (cfg.businessType) setBusinessType(cfg.businessType);
        if (cfg.radius) setRadius(cfg.radius);
      } catch {
        /* ignore */
      }
    }
    setReady(true);
  }, [router]);

  useEffect(() => {
    if (!ready) return;
    localStorage.setItem("searchConfig", JSON.stringify({ city, businessType, radius }));
  }, [city, businessType, radius, ready]);

  const getLeadKey = useCallback(
    (lead: LeadResult) => `${lead.name}__${lead.address || lead.phone || lead.website || "no-addr"}`,
    []
  );

  // ============ Derived state ============
  const stats = useMemo(() => {
    const analyzed = leads.filter((l) => l.ai_score != null);
    const avg =
      analyzed.length > 0
        ? Math.round(analyzed.reduce((s, l) => s + (l.ai_score || 0), 0) / analyzed.length)
        : 0;
    return {
      total: leads.length,
      analyzed: analyzed.length,
      hot: leads.filter((l) => (l.ai_score || 0) >= 70).length,
      avg,
    };
  }, [leads]);

  const filteredLeads = useMemo(() => {
    let result = [...leads];
    if (filter === "unanalyzed") result = result.filter((l) => l.ai_score == null);
    else if (filter === "analyzed") result = result.filter((l) => l.ai_score != null);
    else if (filter === "hot") result = result.filter((l) => (l.ai_score || 0) >= 70);

    if (sortBy === "score") result.sort((a, b) => (b.ai_score ?? -1) - (a.ai_score ?? -1));
    else if (sortBy === "name") result.sort((a, b) => a.name.localeCompare(b.name));

    return result;
  }, [leads, filter, sortBy]);

  // ============ Handlers ============
  const handleSearch = useCallback(async () => {
    if (!token || !city.trim() || !businessType.trim()) return;
    setLoading(true);
    setError(null);
    setSearchInfo(null);
    setLeads([]);
    setFilter("all");
    try {
      const data = await searchBusinesses(token, city.trim(), businessType.trim(), radius);
      const results: LeadResult[] = Array.isArray(data) ? data : data.results || [];
      const total = Array.isArray(data) ? data.length : data.total || results.length;
      const source = Array.isArray(data) ? "Overpass" : data.source || "Overpass";
      setLeads(results);
      setSearchInfo(`${total} résultat${total > 1 ? "s" : ""} · source : ${source}`);
      showToast(`${total} leads trouvés`, "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  }, [token, city, businessType, radius, showToast]);

  const handleAnalyze = useCallback(
    async (lead: LeadResult) => {
      if (!token) return;
      const key = getLeadKey(lead);
      if (analyzingRef.current.has(key)) return;

      analyzingRef.current.add(key);
      setAnalyzingIds(new Set(analyzingRef.current));
      try {
        const result = await enrichAndScoreLead(
          token,
          lead.name,
          lead.address,
          lead.website || "",
          businessType,
          city
        );
        setLeads((prev) =>
          prev.map((l) =>
            getLeadKey(l) === key
              ? {
                  ...l,
                  email: result.email || l.email,
                  phone: result.phone || l.phone,
                  website: result.website || l.website,
                  address: result.address || l.address,
                  instagram: result.instagram || "",
                  facebook: result.facebook || "",
                  ai_score: result.ai_score ?? null,
                  ai_reason: result.ai_reason || "",
                  ai_message_subject: result.ai_message_subject || "",
                  ai_message_body: result.ai_message_body || "",
                }
              : l
          )
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Erreur";
        setError(`Analyse ${lead.name} : ${msg}`);
        showToast(`Échec : ${lead.name}`, "error");
      } finally {
        analyzingRef.current.delete(key);
        setAnalyzingIds(new Set(analyzingRef.current));
      }
    },
    [token, businessType, city, getLeadKey, showToast]
  );

  const handleAnalyzeAll = useCallback(async () => {
    const targets = leads.filter((l) => l.ai_score == null);
    if (targets.length === 0) {
      showToast("Tous les leads sont déjà analysés", "info");
      return;
    }
    batchCancelRef.current = false;
    setBatchProgress({ done: 0, total: targets.length });
    let done = 0;
    for (const lead of targets) {
      if (batchCancelRef.current) break;
      await handleAnalyze(lead);
      done++;
      setBatchProgress({ done, total: targets.length });
      // Delai pour respecter le rate limit Gemini (15 req/min, 2 appels/lead)
      if (done < targets.length) {
        await new Promise((r) => setTimeout(r, 8000));
      }
    }
    setBatchProgress(null);
    showToast(
      batchCancelRef.current ? `Batch arrêté (${done}/${targets.length})` : `${done} leads analysés`,
      "success"
    );
  }, [leads, handleAnalyze, showToast]);

  const handleExportCSV = useCallback(() => {
    if (leads.length === 0) return;
    const escape = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const headers = [
      "Nom",
      "Adresse",
      "Téléphone",
      "Email",
      "Site web",
      "Instagram",
      "Facebook",
      "Score",
      "Raison",
      "Sujet",
      "Message",
    ];
    const rows = leads.map((l) =>
      [
        l.name,
        l.address,
        l.phone,
        l.email,
        l.website,
        l.instagram,
        l.facebook,
        l.ai_score,
        l.ai_reason,
        l.ai_message_subject,
        l.ai_message_body,
      ]
        .map(escape)
        .join(",")
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `leads-${city}-${businessType}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Export CSV téléchargé", "success");
  }, [leads, city, businessType, showToast]);

  const copyText = useCallback(
    async (text: string, label = "Copié") => {
      try {
        await navigator.clipboard.writeText(text);
        showToast(label, "success");
      } catch {
        showToast("Impossible de copier", "error");
      }
    },
    [showToast]
  );

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.replace("/login");
  };


  const handleSendEmail = async (lead: LeadResult) => {
    const token = localStorage.getItem('token') || '';
    const key = getLeadKey(lead);
    setSendingIds(prev => new Set(prev).add(key));
    try {
      const subject = lead.ai_message_subject || 'Proposition de collaboration - ' + lead.name;
      const body = lead.ai_message_body || 'Bonjour, je me permets de vous contacter...';
      await sendLeadEmail(token, lead.email || "", subject, body);
      alert('Email envoye avec succes !');
    } catch (err: unknown) {
      alert('Erreur: ' + (err instanceof Error ? err.message : 'inconnue'));
    } finally {
      setSendingIds(prev => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };
  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white">
        <p className="animate-pulse">Chargement...</p>
      </div>
    );
  }

  const isBatchRunning = batchProgress !== null;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Toast toast={toast} onClose={() => setToast(null)} />

      {/* Header */}
      <header className="sticky top-0 z-10 backdrop-blur-md bg-gray-950/80 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-lg">
              📡
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                LeadRadar
              </h1>
              <p className="text-[10px] text-gray-500 -mt-0.5">Prospection intelligente</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Déconnexion
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-6 pt-4 flex gap-2 border-b border-gray-800">
        <button
          onClick={() => setActiveTab("search")}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${activeTab === "search" ? "border-emerald-500 text-white" : "border-transparent text-gray-400 hover:text-white"}`}
        >
          🔍 Recherche
        </button>
        <button
          onClick={() => { setActiveTab("campaigns"); listCampaigns().then(setCampaigns).catch(() => {}); }}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${activeTab === "campaigns" ? "border-emerald-500 text-white" : "border-transparent text-gray-400 hover:text-white"}`}
        >
          📧 Campagnes
        </button>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {activeTab === "search" && (
          <>
        {/* Search Form */}
        <form
          className="bg-gray-900 rounded-xl p-6 border border-gray-800"
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">🔍</span>
            <h2 className="text-lg font-semibold">Rechercher des leads</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
            <div className="md:col-span-4">
              <label htmlFor="city" className="block text-xs text-gray-400 mb-1.5 font-medium">
                Ville
              </label>
              <input
                id="city"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Casablanca, Rabat..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 transition-colors"
                required
              />
            </div>
            <div className="md:col-span-4">
              <label htmlFor="type" className="block text-xs text-gray-400 mb-1.5 font-medium">
                Type de commerce
              </label>
              <input
                id="type"
                type="text"
                value={businessType}
                onChange={(e) => setBusinessType(e.target.value)}
                placeholder="restaurant, café, hôtel..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 transition-colors"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label htmlFor="radius" className="block text-xs text-gray-400 mb-1.5 font-medium">
                Rayon (m)
              </label>
              <input
                id="radius"
                type="number"
                value={radius}
                onChange={(e) => setRadius(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/30 transition-colors"
                min={500}
                max={50000}
              />
            </div>
            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={loading || isBatchRunning}
                className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold px-4 py-2.5 rounded-lg transition-colors text-sm"
              >
                {loading ? "⏳ Recherche..." : "🚀 Rechercher"}
              </button>
            </div>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div
            className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3"
            role="alert"
          >
            <span className="text-lg">❌</span>
            <div className="flex-1">
              <p className="text-red-300 font-semibold text-sm">Erreur</p>
              <p className="text-red-200/80 text-sm mt-0.5">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 text-xs hover:text-red-300"
            >
              ✕
            </button>
          </div>
        )}

        {/* Search info */}
        {searchInfo && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3 flex items-center gap-2">
            <span>✅</span>
            <p className="text-emerald-300 text-sm">{searchInfo}</p>
          </div>
        )}

        {/* Stats */}
        {leads.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon="🎯" label="Leads trouvés" value={stats.total} accent="bg-blue-500/10 text-blue-400" />
            <StatCard
              icon="🤖"
              label="Analysés"
              value={`${stats.analyzed}/${stats.total}`}
              accent="bg-purple-500/10 text-purple-400"
            />
            <StatCard icon="🔥" label="Haut potentiel" value={stats.hot} accent="bg-emerald-500/10 text-emerald-400" />
            <StatCard
              icon="📊"
              label="Score moyen"
              value={stats.avg ? `${stats.avg}/100` : "—"}
              accent="bg-yellow-500/10 text-yellow-400"
            />
          </div>
        )}

        {/* Toolbar */}
        {leads.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 justify-between">
            <div className="flex gap-1 bg-gray-900 p-1 rounded-lg border border-gray-800 flex-wrap">
              {(
                [
                  { key: "all", label: "Tous", count: stats.total },
                  { key: "unanalyzed", label: "Non analysés", count: stats.total - stats.analyzed },
                  { key: "analyzed", label: "Analysés", count: stats.analyzed },
                  { key: "hot", label: "🔥 Chauds", count: stats.hot },
                ] as { key: Filter; label: string; count: number }[]
              ).map((f) => (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    filter === f.key
                      ? "bg-emerald-600 text-white"
                      : "text-gray-400 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  {f.label} <span className="opacity-60 ml-1">{f.count}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortKey)}
                className="bg-gray-900 border border-gray-800 text-gray-300 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
              >
                <option value="default">Tri par défaut</option>
                <option value="score">Tri par score ↓</option>
                <option value="name">Tri par nom</option>
              </select>
              <button
                onClick={handleExportCSV}
                className="bg-gray-900 border border-gray-800 hover:border-gray-700 text-gray-300 text-xs px-3 py-2 rounded-lg transition-colors"
              >
                📥 CSV
              </button>
              {stats.analyzed < stats.total && (
                <button
                  onClick={isBatchRunning ? () => { batchCancelRef.current = true; } : handleAnalyzeAll}
                  disabled={loading}
                  className="bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 text-white text-xs font-medium px-3 py-2 rounded-lg transition-colors"
                >
                  {isBatchRunning
                    ? "⏹ Arrêter"
                    : `🤖 Tout analyser (${stats.total - stats.analyzed})`}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Batch progress */}
        {batchProgress && (
          <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-purple-300 text-sm font-medium">Analyse en cours...</p>
              <p className="text-purple-200 text-xs">
                {batchProgress.done}/{batchProgress.total}
              </p>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-purple-500 to-pink-500 h-full transition-all duration-300"
                style={{ width: `${(batchProgress.done / batchProgress.total) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Table */}
        {leads.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Nom</th>
                    <th className="px-4 py-3 text-left font-medium">Contact</th>
                    <th className="px-4 py-3 text-left font-medium">Site / Réseaux</th>
                    <th className="px-4 py-3 text-center font-medium">Score</th>
                    <th className="px-4 py-3 text-center font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeads.map((lead, idx) => {
                      const key = getLeadKey(lead) + "__" + idx;
                    const isAnalyzing = analyzingIds.has(key);
                    const hasScore = lead.ai_score != null;
                    return (
                      <tr
                        key={key}
                        className="border-t border-gray-800 hover:bg-gray-800/30 transition-colors"
                      >
                        <td className="px-4 py-3">
                          <p className="font-medium text-white">{lead.name}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {lead.address || "Adresse inconnue"}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400 space-y-0.5">
                          {lead.phone && <p>📞 {lead.phone}</p>}
                          {lead.email && (
                            <p className="truncate max-w-[180px]">✉️ {lead.email}</p>
                          )}
                          {!lead.phone && !lead.email && (
                            <span className="text-gray-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs space-y-0.5">
                          {lead.website && (
                            <SafeLink
                              href={lead.website}
                              className="text-emerald-400 hover:underline block truncate max-w-[180px]"
                            >
                              🌐 {lead.website.replace(/^https?:\/\//, "").slice(0, 30)}
                            </SafeLink>
                          )}
                          <div className="flex gap-2">
                            {lead.instagram && (
                              <SafeLink href={lead.instagram} className="text-pink-400 hover:underline">
                                📸 IG
                              </SafeLink>
                            )}
                            {lead.facebook && (
                              <SafeLink href={lead.facebook} className="text-blue-400 hover:underline">
                                📘 FB
                              </SafeLink>
                            )}
                          </div>
                          {!lead.website && !lead.instagram && !lead.facebook && (
                            <span className="text-gray-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {hasScore ? (
                            <ScoreBadge score={lead.ai_score!} />
                          ) : (
                            <span className="text-gray-600 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => handleAnalyze(lead)}
                            disabled={isAnalyzing || isBatchRunning}
                            className="bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 text-white text-xs px-3 py-1.5 rounded-lg transition-colors font-medium"
                            aria-label={`Analyser ${lead.name}`}
                          >
                            {isAnalyzing ? "⏳..." : hasScore ? "🔄 Refaire" : "🤖 Analyser"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredLeads.length === 0 && (
                <div className="text-center py-12 text-gray-500 text-sm">
                  Aucun lead ne correspond à ce filtre
                </div>
              )}
            </div>
          </div>
        )}

        {/* Messages IA */}
        {leads.some((l) => l.ai_message_subject || l.ai_reason) && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <span>🧠</span> Messages IA générés
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              {leads
                .filter((l) => l.ai_message_subject || l.ai_reason)
                .map((lead) => (
                  <div
                    key={getLeadKey(lead)}
                    className="bg-gray-900 rounded-xl border border-gray-800 p-5 hover:border-gray-700 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div>
                        <h4 className="font-bold text-white">{lead.name}</h4>
                        {lead.ai_reason && (
                          <p className="text-gray-500 text-xs mt-1">{lead.ai_reason}</p>
                        )}
                      </div>
                      {lead.ai_score != null && <ScoreBadge score={lead.ai_score} />}
                    </div>
                    {lead.ai_message_subject && (
                      <div className="bg-gray-800/60 rounded-lg p-4 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-purple-300 font-semibold text-sm flex-1">
                            📧 {lead.ai_message_subject}
                          </p>
                          <button
                            onClick={() =>
                              copyText(
                                `${lead.ai_message_subject}\n\n${lead.ai_message_body}`,
                                "Message copié"
                              )
                            }
                            className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-gray-700 transition-colors flex-shrink-0"
                          >
                            📋 Copier
                              </button>
                              {lead.email && lead.email.includes("@") ? (
                                <button
                                  onClick={() => handleSendEmail(lead)}
                                  disabled={sendingIds.has(getLeadKey(lead))}
                                  className="text-emerald-400 hover:text-emerald-300 disabled:text-gray-600 text-xs px-2 py-1 rounded hover:bg-gray-700 transition-colors font-medium"
                                >
                                  {sendingIds.has(getLeadKey(lead)) ? "..." : "📧 Envoyer"}
                                </button>
                              ) : (
                                <span className="text-gray-600 text-xs px-2 py-1">
                                  📧 -
                                </span>
                              )}
                        </div>
                        <p className="text-gray-300 text-sm whitespace-pre-line leading-relaxed">
                          {lead.ai_message_body}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Empty */}
        {!loading && leads.length === 0 && !error && (
          <div className="text-center text-gray-500 py-20">
            <p className="text-5xl mb-4">📡</p>
            <p className="text-lg font-medium text-gray-400">Aucune recherche effectuée</p>
            <p className="text-sm mt-1">Lance une recherche pour trouver des leads qualifiés</p>
          </div>
        )}
          </>
        )}

        {activeTab === "campaigns" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Mes Campagnes</h2>
              <button
                onClick={() => setShowCampaignModal(true)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors"
              >
                + Nouvelle Campagne
              </button>
            </div>

            {campaigns.length === 0 ? (
              <div className="text-center text-gray-500 py-20">
                <p className="text-5xl mb-4">📧</p>
                <p className="text-lg font-medium text-gray-400">Aucune campagne</p>
                <p className="text-sm mt-1">Créez une campagne pour organiser vos leads</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {campaigns.map((c: any) => (
                  <div key={c.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between hover:border-gray-700 transition-colors">
                    <div>
                      <h3 className="font-semibold text-white">{c.name}</h3>
                      <p className="text-sm text-gray-400 mt-1">{c.description || "Pas de description"}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-400">{c.lead_count} leads</span>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                        c.status === "draft" ? "bg-gray-700 text-gray-300" :
                        c.status === "active" ? "bg-emerald-500/10 text-emerald-300" :
                        "bg-yellow-500/10 text-yellow-300"
                      }`}>
                        {c.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showCampaignModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md">
                  <h3 className="text-lg font-bold mb-4">Nouvelle Campagne</h3>
                  <input
                    type="text"
                    placeholder="Nom de la campagne"
                    value={campaignName}
                    onChange={(e) => setCampaignName(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white mb-4"
                  />
                  <p className="text-sm text-gray-400 mb-4">
                    {leads.filter(l => (l.ai_score ?? 0) > 0).length} leads analyses seront ajoutes
                  </p>
                  <div className="flex gap-3 justify-end">
                    <button
                      onClick={() => setShowCampaignModal(false)}
                      className="px-4 py-2 text-gray-400 hover:text-white"
                    >
                      Annuler
                    </button>
                    <button
                      onClick={async () => {
                        if (!campaignName.trim()) return;
                        const scoredLeads = leads.filter(l => (l.ai_score ?? 0) > 0);
                        await createCampaign(campaignName, scoredLeads.map(l => l.id || ""));
                        setShowCampaignModal(false);
                        setCampaignName("");
                        const updated = await listCampaigns();
                        setCampaigns(updated);
                      }}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium"
                    >
                      Creer
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}