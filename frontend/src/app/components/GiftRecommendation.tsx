import { motion, AnimatePresence } from "motion/react";
import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "./ui/button";
import {
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Loader2,
  AlertCircle,
  Brain,
  Users,
  Layers,
  MessageSquare,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  Info,
} from "lucide-react";
import { Navbar } from "./Navbar";
import { FloatingEmojiBackground } from "./FloatingEmojiBackground";
import { ProfileModal } from "./ProfileModal";
import {
  compareModels,
  getGiftDetails,
} from "../../lib/api/recommendations";
import type {
  CompareResponse,
  MetricValue,
  ModelResult,
  RecommendationWithGift,
  GiftDetailsWithMetrics,
} from "../../lib/api/recommendations";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "./ui/context-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
} from "recharts";

interface DisplayGift {
  id: number;
  name: string;
  description: string;
  price: string;
  image: string;
  category: string;
  product_url?: string;
  score: number;
  model: string;
  is_valid_recommendation?: boolean | null;
  validity_score?: number | null;
  validity_reasons?: string[] | null;
  query_cosine_similarity?: number | null;
  content_cosine_similarity?: number | null;
  collaborative_cosine_similarity?: number | null;
  knowledge_similarity?: number | null;
  rag_similarity?: number | null;
  occasion_match?: boolean | null;
  relationship_match?: boolean | null;
  age_match?: boolean | null;
  gender_match?: boolean | null;
  price_match?: boolean | null;
  hobby_overlap?: number | null;
}

interface GiftRecommendationProps {
  onComplete: (gift: DisplayGift) => void;
  onBack: () => void;
  formData: {
    age: string;
    relation: string;
    occasion: string;
    hobbies: string;
    gender: string;
    budgetMax: number;
  };
}

const FALLBACK =
  "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=800&q=80";

function toDisplay(r: RecommendationWithGift): DisplayGift {
  return {
    id: r.gift_id,
    name: r.title,
    description: r.description ?? "",
    price: "$" + r.price.toFixed(2),
    image: r.image_url ?? FALLBACK,
    category: r.category_name ?? "Gift",
    product_url: r.product_url,
    score: r.score,
    model: r.model_type,
    is_valid_recommendation: r.is_valid_recommendation,
    validity_score: r.validity_score,
    validity_reasons: r.validity_reasons,
    query_cosine_similarity: r.query_cosine_similarity,
    content_cosine_similarity: r.content_cosine_similarity,
    collaborative_cosine_similarity: r.collaborative_cosine_similarity,
    knowledge_similarity: r.knowledge_similarity,
    rag_similarity: r.rag_similarity,
    occasion_match: r.occasion_match,
    relationship_match: r.relationship_match,
    age_match: r.age_match,
    gender_match: r.gender_match,
    price_match: r.price_match,
    hobby_overlap: r.hobby_overlap,
  };
}

const CFG = {
  content: {
    label: "Content-Based",
    sub: "TF-IDF + Cosine",
    Icon: Brain,
    grad: "from-violet-500 to-purple-600",
    light: "bg-violet-50 border-violet-200",
    badge: "bg-violet-100 text-violet-700",
    ring: "ring-violet-400",
  },
  collaborative: {
    label: "Collaborative",
    sub: "User Similarity+Matrix",
    Icon: Users,
    grad: "from-blue-500 to-cyan-600",
    light: "bg-blue-50 border-blue-200",
    badge: "bg-blue-100 text-blue-700",
    ring: "ring-blue-400",
  },
  hybrid: {
    label: "Hybrid",
    sub: "Content+Collaborative",
    Icon: Layers,
    grad: "from-rose-500 to-orange-500",
    light: "bg-rose-50 border-rose-200",
    badge: "bg-rose-100 text-rose-700",
    ring: "ring-rose-400",
  },
  rag: {
    label: "RAG",
    sub: "OpenAI+Vector Search",
    Icon: MessageSquare,
    grad: "from-emerald-500 to-teal-600",
    light: "bg-emerald-50 border-emerald-200",
    badge: "bg-emerald-100 text-emerald-700",
    ring: "ring-emerald-400",
  },
  knowledge: {
    label: "Knowledge-Based",
    sub: "Rules+Keywords",
    Icon: BookOpen,
    grad: "from-amber-500 to-orange-500",
    light: "bg-amber-50 border-amber-200",
    badge: "bg-amber-100 text-amber-700",
    ring: "ring-amber-400",
  },
} as const;

type MK = keyof typeof CFG;

const HIDDEN_METRIC_KEYS = new Set(["query_used", "inputs", "error"]);
const DISPLAY_DECIMAL_KEYS = new Set([
  "precision",
  "precision_at_k",
  "recall",
  "recall_at_k",
  "f1",
  "f1_at_k",
  "f1_score",
  "hit_rate_at_k",
  "ndcg_at_k",
  "map_at_k",
  "mrr_at_k",
  "accuracy",
  "error_rate",
  "mae",
  "rmse",
  "coverage",
  "validity_rate",
  "invalidity_rate",
  "avg_validity_score",
  "avg_query_cosine_similarity",
]);
const WEIGHT_KEYS = new Set(["content_weight", "collab_weight", "knowledge_weight"]);
const METRIC_ORDER = [
  "precision_at_k",
  "recall_at_k",
  "f1_at_k",
  "hit_rate_at_k",
  "ndcg_at_k",
  "map_at_k",
  "mrr_at_k",
  "hits_at_k",
  "k",
  "positive_pool_size",
  "precision",
  "recall",
  "f1",
  "f1_score",
  "accuracy",
  "error_rate",
  "mae",
  "rmse",
  "confusion_matrix",
  "tp",
  "fp",
  "tn",
  "fn",
  "coverage",
  "recommended_count",
  "metrics_mode",
  "valid_recommendations",
  "invalid_recommendations",
  "validity_rate",
  "invalidity_rate",
  "avg_validity_score",
  "avg_query_cosine_similarity",
  "top_invalid_reasons",
  "history_used",
  "blend_mode",
  "content_weight",
  "collab_weight",
  "knowledge_weight",
  "retrieved_count",
  "validity_supplemented",
] as const;
const METRIC_LABELS: Record<string, string> = {
  precision_at_k: "Precision@K",
  recall_at_k: "Recall@K",
  f1_at_k: "F1@K",
  hit_rate_at_k: "Hit Rate@K",
  ndcg_at_k: "NDCG@K",
  map_at_k: "MAP@K",
  mrr_at_k: "MRR@K",
  hits_at_k: "Hits@K",
  k: "K",
  positive_pool_size: "Positive Pool Size",
  precision: "Precision",
  recall: "Recall",
  f1: "F1",
  f1_score: "F1 Score",
  accuracy: "Accuracy",
  error_rate: "Error Rate",
  mae: "Mae",
  rmse: "Rmse",
  confusion_matrix: "Confusion Matrix",
  tp: "Tp",
  fp: "Fp",
  tn: "Tn",
  fn: "Fn",
  coverage: "Coverage",
  recommended_count: "Recommended Count",
  metrics_mode: "Metrics Mode",
  valid_recommendations: "Valid Recommendations",
  invalid_recommendations: "Invalid Recommendations",
  validity_rate: "Validity Rate",
  invalidity_rate: "Invalidity Rate",
  avg_validity_score: "Avg Validity Score",
  avg_query_cosine_similarity: "Avg Query Cosine Similarity",
  top_invalid_reasons: "Top Invalid Reasons",
  history_used: "History Used",
  blend_mode: "Blend Mode",
  content_weight: "Content Weight",
  collab_weight: "Collab Weight",
  knowledge_weight: "Knowledge Weight",
  retrieved_count: "Retrieved Count",
  validity_supplemented: "Validity Supplemented",
};

function metricAsNumber(value: MetricValue | undefined | null): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatMetricValue(key: string, value: MetricValue): string {
  if (typeof value === "number") {
    if (Number.isInteger(value) && !DISPLAY_DECIMAL_KEYS.has(key)) {
      return value.toString();
    }
    if (WEIGHT_KEYS.has(key)) {
      return value.toFixed(2);
    }
    if (DISPLAY_DECIMAL_KEYS.has(key)) {
      return value.toFixed(3);
    }
    if (value >= 0 && value <= 1) {
      return value.toFixed(3);
    }
    return value.toFixed(2);
  }
  if (typeof value === "boolean") {
    return value ? "True" : "False";
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => (Array.isArray(item) ? item.map(String).join(":") : String(item)))
      .join(" | ");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  if (value == null) {
    return "-";
  }
  return String(value);
}

function metricRows(
  metrics: Record<string, MetricValue>,
  hidden: Set<string> = HIDDEN_METRIC_KEYS,
): Array<[string, MetricValue]> {
  const filteredEntries = Object.entries(metrics).filter(
    ([k, v]) => !hidden.has(k) && v !== undefined && v !== null,
  );
  const byKey = new Map(filteredEntries);
  const rows: Array<[string, MetricValue]> = [];

  for (const key of METRIC_ORDER) {
    if (byKey.has(key)) {
      rows.push([key, byKey.get(key) as MetricValue]);
      byKey.delete(key);
    }
  }

  const extraRows = Array.from(byKey.entries()).sort((a, b) =>
    a[0].localeCompare(b[0]),
  );
  return [...rows, ...extraRows];
}

function metricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key.replace(/_/g, " ");
}

function GiftCard({
  gift,
  selected,
  onSelect,
  onDetails,
  mk,
}: {
  gift: DisplayGift;
  selected: boolean;
  onSelect: () => void;
  onDetails: () => void;
  mk: MK;
}) {
  const c = CFG[mk];
  const card = (
    <motion.div
      whileHover={{ y: -4 }}
      onClick={onSelect}
      className={
        "group relative cursor-pointer rounded-2xl border-2 overflow-hidden transition-all " +
        (selected
          ? "border-transparent ring-4 " + c.ring + " shadow-xl scale-[1.02]"
          : "border-gray-100 hover:border-gray-200 shadow-md")
      }
    >
      {selected && (
        <div className="absolute top-3 right-3 z-10">
          <CheckCircle2 className="text-white drop-shadow-md" size={24} />
        </div>
      )}
      <div className="relative h-44 overflow-hidden bg-gray-50">
        <img
          src={gift.image}
          alt={gift.name}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).src = FALLBACK;
          }}
        />
        <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-black/40 to-transparent" />
        <span
          className={
            "absolute top-3 left-3 text-xs font-bold px-2 py-1 rounded-full " +
            c.badge
          }
        >
          {gift.category}
        </span>
        {/* Hover overlay */}
        <div className="pointer-events-none absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-colors" />
        <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            size="sm"
            variant="secondary"
            onClick={(e) => {
              e.stopPropagation();
              onDetails();
            }}
          >
            See details
          </Button>
        </div>
      </div>
      <div className="p-4 bg-white">
        <h4 className="font-semibold text-sm leading-tight mb-1 line-clamp-2">
          {gift.name}
        </h4>
        <div className="flex items-center justify-between">
          <span className="font-bold text-rose-600">{gift.price}</span>
          <div className="flex items-center gap-2">
            {gift.product_url && (
              <a
                href={gift.product_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-gray-400 hover:text-gray-600"
              >
                <ExternalLink size={14} />
              </a>
            )}
            <span className="text-xs text-gray-400">
              {gift.score.toFixed(3)}
            </span>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {gift.is_valid_recommendation != null && (
            <span
              className={
                "rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                (gift.is_valid_recommendation
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-amber-50 text-amber-700 border-amber-200")
              }
            >
              {gift.is_valid_recommendation ? "Valid match" : "Needs review"}
            </span>
          )}
          {gift.query_cosine_similarity != null && (
            <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
              Cosine {gift.query_cosine_similarity.toFixed(3)}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{card}</ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onClick={onDetails}>View details</ContextMenuItem>
        {gift.product_url && (
          <ContextMenuItem asChild>
            <a href={gift.product_url} target="_blank" rel="noreferrer">
              Open product
            </a>
          </ContextMenuItem>
        )}
      </ContextMenuContent>
    </ContextMenu>
  );
}

function Metrics({
  metrics,
  cold,
  explanation,
  showRows = true,
  showInputDetails = true,
  showDetailsHint = false,
}: {
  metrics: Record<string, MetricValue>;
  cold: boolean;
  explanation?: string;
  showRows?: boolean;
  showInputDetails?: boolean;
  showDetailsHint?: boolean;
}) {
  const rows = metricRows(metrics);
  const inputDetails = metrics.inputs || metrics.query_used;

  return (
    <div className="space-y-3 text-xs">
      {cold && (
        <div className="flex items-center gap-2 text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <Info size={14} />
          <span>Cold start — interact with gifts to improve this model.</span>
        </div>
      )}
      {showRows && rows.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {rows.map(([k, v]) => (
            <div
              key={k}
              className="bg-white rounded-lg p-2 text-center border border-gray-100"
            >
              <div className="font-bold text-gray-800 text-sm break-words">
                {formatMetricValue(k, v)}
              </div>
              <div className="text-gray-400 mt-0.5">{metricLabel(k)}</div>
            </div>
          ))}
        </div>
      )}
      {explanation && (
        <div className="bg-white rounded-lg p-3 border border-gray-100 text-gray-600 prose prose-sm max-w-none prose-p:my-1 prose-li:my-0.5 prose-ul:my-1 prose-ol:my-1 prose-strong:text-gray-800">
          <span className="font-semibold text-gray-700 block mb-1">
            AI Explanation:
          </span>
          <ReactMarkdown>{explanation}</ReactMarkdown>
        </div>
      )}
      {showInputDetails && inputDetails && (
        <div className="bg-white rounded-lg p-3 border border-gray-100 text-gray-600">
          <span className="font-semibold text-gray-700 block mb-1">
            Model inputs
          </span>
          <span className="text-xs break-words">{String(inputDetails)}</span>
        </div>
      )}
      {showDetailsHint && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-indigo-700">
          Open a gift's details to view full per-gift metrics and graphs.
        </div>
      )}
      {metrics.error && (
        <p className="text-red-500">Error: {String(metrics.error)}</p>
      )}
    </div>
  );
}

export function GiftRecommendation({
  onComplete,
  onBack,
  formData,
}: GiftRecommendationProps) {
  const [data, setData] = useState<CompareResponse | null>(null);
  const [model, setModel] = useState("content");
  const [picked, setPicked] = useState<DisplayGift | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const minP = 0;
  const maxP =
    typeof formData.budgetMax === "number" && Number.isFinite(formData.budgetMax)
      ? formData.budgetMax
      : undefined;
  const [profileOpen, setProfileOpen] = useState(false);

  // Details dialog state
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsErr, setDetailsErr] = useState<string | null>(null);
  const [details, setDetails] = useState<GiftDetailsWithMetrics | null>(null);

  async function openDetails(giftId: number, selectedModel: MK) {
    setDetailsOpen(true);
    setDetailsLoading(true);
    setDetailsErr(null);
    setDetails(null);
    try {
      const d = await getGiftDetails(
        giftId,
        {
          model: selectedModel,
          occasion: formData.occasion || undefined,
          relationship: formData.relation || undefined,
          min_price: minP,
          max_price: maxP,
          age: formData.age || undefined,
          gender: formData.gender || undefined,
          hobbies: formData.hobbies || undefined,
        },
        { timeoutMs: 60000, retry: { attempts: 1 } },
      );
      setDetails(d);
    } catch (e: any) {
      if (e?.name === "AbortError") {
        setDetailsErr("Request timed out. Please try again.");
      } else {
        const msg = e?.status
          ? `Failed to load details (status ${e.status}). ${e?.message || ""}`
          : e?.message || "Failed to load details";
        setDetailsErr(msg);
      }
    } finally {
      setDetailsLoading(false);
    }
  }

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const d = await compareModels(
          {
            top_n: 6,
            occasion: formData.occasion || undefined,
            relationship: formData.relation || undefined,
            min_price: minP,
            max_price: maxP,
            age: formData.age || undefined,
            gender: formData.gender || undefined,
            hobbies: formData.hobbies || undefined,
            // Let backend generate the query internally to avoid duplicates and improve relevance
          },
          { signal: ctrl.signal },
        );
        setData(d);
        setModel(d.user_has_history ? "hybrid" : "content");
      } catch (e: unknown) {
        const ex = e as any;
        if (ex?.name === "AbortError") {
          // ignore abort on unmount/navigation
        } else {
          setErr(
            ex?.status === 401
              ? "Please sign in."
              : (ex?.message ?? "Failed to load."),
          );
        }
      } finally {
        setLoading(false);
      }
    })();
    return () => ctrl.abort();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const md: ModelResult | undefined = data?.models.find(
    (m) => m.model === model,
  );
  const gifts = (md?.gifts ?? []).map(toDisplay);
  const cfg = CFG[model as MK] ?? CFG.hybrid;
  const Icon = cfg.Icon;
  const label = picked
    ? picked.name.length > 22
      ? picked.name.slice(0, 22) + "..."
      : picked.name
    : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-rose-50 to-orange-50 relative overflow-hidden">
      <FloatingEmojiBackground />
      <Navbar
        showAuthButtons={false}
        showNavLinks={false}
        onLogoClick={onBack}
        onProfileClick={() => setProfileOpen(true)}
      />
      <ProfileModal isOpen={profileOpen} onClose={() => setProfileOpen(false)} />
      <div className="pt-28 pb-16 px-4 relative z-10 max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className="inline-flex items-center gap-2 bg-white/80 backdrop-blur-sm rounded-full px-5 py-2 shadow-md mb-4 border border-rose-100">
            <Sparkles className="text-rose-500" size={18} />
            <span className="text-sm font-medium text-gray-700">
              5 AI Models — Compare and choose
            </span>
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
            Gift Recommendations
          </h1>
          {data && !data.user_has_history && (
            <p className="text-amber-600 text-sm mt-3 bg-amber-50 inline-block px-4 py-1.5 rounded-full border border-amber-200">
              New user — interact to unlock Collaborative and Hybrid
            </p>
          )}
        </motion.div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <Loader2 className="animate-spin text-rose-500" size={48} />
            <p className="text-gray-500 text-lg">Running all 5 AI models...</p>
            <p className="text-gray-400 text-sm">
              Content - Collaborative - Hybrid - Knowledge - RAG
            </p>
          </div>
        )}

        {err && !loading && (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <AlertCircle className="text-rose-500" size={48} />
            <p className="text-gray-600 text-center max-w-sm">{err}</p>
            <Button onClick={onBack} variant="outline">
              Go Back
            </Button>
          </div>
        )}

        {!loading && !err && data && (
          <>
            <div className="flex flex-wrap justify-center gap-3 mb-8">
              {data.models.map((m) => {
                const c = CFG[m.model as MK];
                if (!c) return null;
                const active = model === m.model;
                const n = m.gifts.length;
                const TI = c.Icon;
                return (
                  <button
                    key={m.model}
                    onClick={() => {
                      setModel(m.model);
                      setPicked(null);
                    }}
                    className={
                      "flex flex-col items-start px-5 py-3 rounded-2xl border-2 transition-all font-medium text-sm min-w-[160px] " +
                      (active
                        ? "bg-gradient-to-br " +
                          c.grad +
                          " text-white border-transparent shadow-lg scale-105"
                        : "bg-white border-gray-100 hover:border-gray-200 text-gray-700")
                    }
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <TI size={18} />
                      <span className="font-bold">{c.label}</span>
                    </div>
                    <span
                      className={
                        "text-xs " +
                        (active ? "text-white/80" : "text-gray-400")
                      }
                    >
                      {c.sub}
                    </span>
                    <span
                      className={
                        "text-xs mt-1.5 font-semibold " +
                        (active ? "text-white" : "text-rose-500")
                      }
                    >
                      {n === 0
                        ? m.is_cold_start
                          ? "No history yet"
                          : "No matches"
                        : n + " gift" + (n !== 1 ? "s" : "") + " found"}
                    </span>
                  </button>
                );
              })}
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={model}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.2 }}
              >
                <div className={"rounded-2xl p-5 border mb-6 " + cfg.light}>
                  <div className="flex items-center gap-3 mb-4">
                    <div
                      className={
                        "w-9 h-9 rounded-xl bg-gradient-to-br " +
                        cfg.grad +
                        " flex items-center justify-center text-white shadow"
                      }
                    >
                      <Icon size={18} />
                    </div>
                    <div>
                      <h2 className="font-bold text-gray-800">{md?.label}</h2>
                      <p className="text-xs text-gray-500">{cfg.sub}</p>
                    </div>
                  </div>
                  {md && (
                    <Metrics
                      metrics={md.metrics}
                      cold={md.is_cold_start}
                      explanation={md.explanation}
                      showRows={false}
                      showInputDetails={false}
                      showDetailsHint
                    />
                  )}
                </div>

                {gifts.length === 0 ? (
                  <div className="text-center py-20 text-gray-400">
                    <Brain size={56} className="mx-auto mb-4 opacity-20" />
                    <p className="font-semibold text-lg">
                      {md?.is_cold_start
                        ? "Not enough interaction history yet."
                        : "No gifts matched your preferences."}
                    </p>
                    <p className="text-sm mt-2">Try a different model tab.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-5 mb-8">
                    {gifts.map((g) => (
                      <GiftCard
                        key={g.id + "-" + model}
                        gift={g}
                        selected={
                          picked?.id === g.id && picked?.model === g.model
                        }
                        onSelect={() =>
                          setPicked(picked?.id === g.id ? null : g)
                        }
                        onDetails={() => openDetails(g.id, model as MK)}
                        mk={model as MK}
                      />
                    ))}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="flex gap-4"
            >
              <Button
                onClick={onBack}
                variant="outline"
                className="flex-1 py-7 text-lg border-2 border-rose-300 hover:bg-rose-50"
              >
                <ArrowLeft className="mr-2" size={20} />
                Back
              </Button>
              <Button
                onClick={() => picked && onComplete(picked)}
                disabled={!picked}
                className="flex-1 py-7 text-lg bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 disabled:opacity-40 shadow-lg"
              >
                {picked
                  ? 'Continue with "' + label + '"'
                  : "Select a gift to continue"}
                {picked && <ArrowRight className="ml-2" size={20} />}
              </Button>
            </motion.div>
          </>
        )}
      </div>

      {/* Details Dialog */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto max-w-[min(1100px,calc(100vw-2rem))]">
          <DialogHeader>
            <DialogTitle>Gift details & metrics</DialogTitle>
          </DialogHeader>
          {detailsLoading ? (
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 className="animate-spin" /> Loading...
            </div>
          ) : detailsErr ? (
            <div className="text-red-500 text-sm">{detailsErr}</div>
          ) : details ? (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
              <div className="lg:col-span-2 space-y-3">
                <div className="aspect-[4/3] overflow-hidden rounded-lg bg-gray-50">
                  <img
                    src={details.gift.image_url || FALLBACK}
                    className="w-full h-full object-cover"
                    onError={(e) =>
                      ((e.target as HTMLImageElement).src = FALLBACK)
                    }
                  />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">
                    {details.gift.title}
                  </h3>
                  <div className="text-rose-600 font-bold text-sm mt-1">
                    ${""}
                    {details.gift.price.toFixed(2)}
                  </div>
                  {details.gift.product_url && (
                    <a
                      href={details.gift.product_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Open product page
                    </a>
                  )}
                  {details.gift.category?.name && (
                    <div className="mt-2 inline-flex items-center rounded-full border bg-white px-2 py-0.5 text-[11px] text-gray-700">
                      Category: {details.gift.category.name}
                    </div>
                  )}
                  <p className="text-xs text-gray-600 mt-2 whitespace-pre-wrap">
                    {details.gift.description || "No description."}
                  </p>
                </div>
              </div>
              <div className="lg:col-span-3 space-y-4">
                {(() => {
                  const compareGift = gifts.find((g) => g.id === details.gift.id);
                  const currentModelMetrics = (md?.metrics ?? {}) as Record<
                    string,
                    MetricValue
                  >;
                  const currentRows = metricRows(
                    currentModelMetrics,
                    new Set([...HIDDEN_METRIC_KEYS, "confusion_matrix"]),
                  );
                  const confusion = Array.isArray(
                    currentModelMetrics.confusion_matrix,
                  )
                    ? currentModelMetrics.confusion_matrix
                    : null;
                  const modelGiftDiagnostics = (data?.models ?? []).map(
                    (modelResult) => ({
                      modelResult,
                      gift: modelResult.gifts.find(
                        (g) => g.gift_id === details.gift.id,
                      ),
                    }),
                  );

                  const currentPrecisionAtK =
                    metricAsNumber(currentModelMetrics.precision_at_k) ??
                    metricAsNumber(currentModelMetrics.precision);
                  const currentRecallAtK =
                    metricAsNumber(currentModelMetrics.recall_at_k) ??
                    metricAsNumber(currentModelMetrics.recall);
                  const currentHitRateAtK = metricAsNumber(
                    currentModelMetrics.hit_rate_at_k,
                  );
                  const currentNdcgAtK = metricAsNumber(
                    currentModelMetrics.ndcg_at_k,
                  );
                  const currentMapAtK = metricAsNumber(
                    currentModelMetrics.map_at_k,
                  );
                  const currentMrrAtK = metricAsNumber(
                    currentModelMetrics.mrr_at_k,
                  );
                  const currentK = metricAsNumber(currentModelMetrics.k);
                  const hitsAtK = metricAsNumber(currentModelMetrics.hits_at_k);
                  const positivePoolSize = metricAsNumber(
                    currentModelMetrics.positive_pool_size,
                  );
                  const errorRate = metricAsNumber(currentModelMetrics.error_rate);
                  const mae = metricAsNumber(currentModelMetrics.mae);
                  const rmse = metricAsNumber(currentModelMetrics.rmse);
                  const coverage = metricAsNumber(currentModelMetrics.coverage);
                  const recommendedCount = metricAsNumber(
                    currentModelMetrics.recommended_count,
                  );
                  const validRecommendations = metricAsNumber(
                    currentModelMetrics.valid_recommendations,
                  );
                  const invalidRecommendations = metricAsNumber(
                    currentModelMetrics.invalid_recommendations,
                  );
                  const cmFromMatrix =
                    confusion &&
                    Array.isArray(confusion[0]) &&
                    Array.isArray(confusion[1])
                      ? {
                          tn:
                            typeof confusion[0][0] === "number"
                              ? confusion[0][0]
                              : null,
                          fp:
                            typeof confusion[0][1] === "number"
                              ? confusion[0][1]
                              : null,
                          fn:
                            typeof confusion[1][0] === "number"
                              ? confusion[1][0]
                              : null,
                          tp:
                            typeof confusion[1][1] === "number"
                              ? confusion[1][1]
                              : null,
                        }
                      : null;
                  const cm = {
                    tp:
                      metricAsNumber(currentModelMetrics.tp) ??
                      cmFromMatrix?.tp ??
                      null,
                    fp:
                      metricAsNumber(currentModelMetrics.fp) ??
                      cmFromMatrix?.fp ??
                      null,
                    tn:
                      metricAsNumber(currentModelMetrics.tn) ??
                      cmFromMatrix?.tn ??
                      null,
                    fn:
                      metricAsNumber(currentModelMetrics.fn) ??
                      cmFromMatrix?.fn ??
                      null,
                  };
                  const confusionMax = Math.max(
                    1,
                    Number(cm.tp ?? 0),
                    Number(cm.fp ?? 0),
                    Number(cm.tn ?? 0),
                    Number(cm.fn ?? 0),
                  );
                  const confusionBars =
                    cm.tp != null ||
                    cm.fp != null ||
                    cm.tn != null ||
                    cm.fn != null
                      ? [
                          {
                            name: "counts",
                            tp: Number(cm.tp ?? 0),
                            fp: Number(cm.fp ?? 0),
                            tn: Number(cm.tn ?? 0),
                            fn: Number(cm.fn ?? 0),
                          },
                        ]
                      : [];
                  const allModelMetricSeries = (data?.models ?? []).map(
                    (modelResult) => ({
                      model: CFG[modelResult.model as MK]?.label ?? modelResult.model,
                      precision_at_k: Number(
                        metricAsNumber(modelResult.metrics.precision_at_k) ??
                          metricAsNumber(modelResult.metrics.precision) ??
                          0,
                      ),
                      recall_at_k: Number(
                        metricAsNumber(modelResult.metrics.recall_at_k) ??
                          metricAsNumber(modelResult.metrics.recall) ??
                          0,
                      ),
                      ndcg_at_k: Number(
                        metricAsNumber(modelResult.metrics.ndcg_at_k) ?? 0,
                      ),
                      hit_rate_at_k: Number(
                        metricAsNumber(modelResult.metrics.hit_rate_at_k) ?? 0,
                      ),
                      f1_at_k: Number(
                        metricAsNumber(modelResult.metrics.f1_at_k) ??
                          metricAsNumber(modelResult.metrics.f1) ??
                          metricAsNumber(modelResult.metrics.f1_score) ??
                          0,
                      ),
                    }),
                  );
                  const currentModelKey = model as MK;
                  const selectedModelScore =
                    metricAsNumber(compareGift?.score) ??
                    metricAsNumber(details.metrics.selected_model_score) ??
                    null;
                  const selectedModelSimilarity = (() => {
                    if (!compareGift) return null;
                    if (currentModelKey === "content") {
                      return compareGift.content_cosine_similarity ?? null;
                    }
                    if (currentModelKey === "collaborative") {
                      return compareGift.collaborative_cosine_similarity ?? null;
                    }
                    if (currentModelKey === "knowledge") {
                      return compareGift.knowledge_similarity ?? null;
                    }
                    if (currentModelKey === "rag") {
                      return compareGift.rag_similarity ?? null;
                    }
                    return compareGift.query_cosine_similarity ?? null;
                  })();
                  const selectedModelSimilarityLabel =
                    currentModelKey === "content"
                      ? "Content similarity"
                      : currentModelKey === "collaborative"
                        ? "Collaborative similarity"
                        : currentModelKey === "knowledge"
                          ? "Knowledge similarity"
                          : currentModelKey === "rag"
                            ? "RAG similarity"
                            : "Query cosine";
                  const diagnosticsBars = [
                    {
                      name: "error_rate",
                      value: Number(errorRate ?? 0),
                    },
                    {
                      name: "mae",
                      value: Number(mae ?? 0),
                    },
                    {
                      name: "rmse",
                      value: Number(rmse ?? 0),
                    },
                    {
                      name: "coverage",
                      value: Number(coverage ?? 0),
                    },
                  ];

                  // Scores bar chart
                  return (
                    <>
                      {currentModelKey === "hybrid" ? (
                        <>
                          {/* Hybrid sub-score breakdown */}
                          <div className="bg-white rounded-lg border p-3">
                            <h4 className="text-sm font-semibold mb-2">
                              Hybrid model sub-scores
                            </h4>
                            <div className="h-40">
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                  data={[
                                    {
                                      name: "scores",
                                      hybrid: details.metrics.hybrid_score,
                                      content: details.metrics.content_score,
                                      collab: details.metrics.collab_score,
                                      knowledge:
                                        details.metrics.knowledge_score ?? 0,
                                    },
                                  ]}
                                >
                                  <XAxis dataKey="name" hide />
                                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                                  <Tooltip />
                                  <Legend />
                                  <Bar dataKey="hybrid" fill="#f43f5e" />
                                  <Bar dataKey="content" fill="#8b5cf6" />
                                  <Bar dataKey="collab" fill="#0ea5e9" />
                                  <Bar dataKey="knowledge" fill="#f59e0b" />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                          <div className="bg-white rounded-lg border p-3">
                            <h4 className="text-sm font-semibold mb-2">
                              Hybrid confidence
                            </h4>
                            <div className="h-36">
                              <ResponsiveContainer width="100%" height="100%">
                                <RadialBarChart
                                  innerRadius="60%"
                                  outerRadius="100%"
                                  data={[
                                    {
                                      name: "conf",
                                      value: Math.max(
                                        0,
                                        Math.min(1, details.metrics.confidence),
                                      ),
                                    },
                                  ]}
                                  startAngle={90}
                                  endAngle={450}
                                >
                                  <RadialBar dataKey="value" fill="#10b981" />
                                  <Tooltip
                                    formatter={(v: number) =>
                                      (v * 100).toFixed(0) + "%"
                                    }
                                  />
                                </RadialBarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="bg-white rounded-lg border p-3">
                          <h4 className="text-sm font-semibold mb-2">
                            Current model gift score
                          </h4>
                          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                            <div className="rounded-md border p-2 bg-gray-50">
                              Score:{" "}
                              {selectedModelScore != null
                                ? selectedModelScore.toFixed(3)
                                : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              {selectedModelSimilarityLabel}:{" "}
                              {selectedModelSimilarity != null
                                ? selectedModelSimilarity.toFixed(3)
                                : "-"}
                            </div>
                          </div>
                          <div className="h-36">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart
                                data={[
                                  {
                                    name: "current",
                                    score: Number(selectedModelScore ?? 0),
                                    similarity: Number(selectedModelSimilarity ?? 0),
                                  },
                                ]}
                              >
                                <XAxis dataKey="name" hide />
                                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="score" fill="#f43f5e" />
                                <Bar dataKey="similarity" fill="#0ea5e9" />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}
                      {/* Current model headline ranking metrics */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="bg-white rounded-lg p-3 border text-center">
                          <div className="text-lg font-bold">
                            {currentPrecisionAtK != null
                              ? Number(currentPrecisionAtK).toFixed(3)
                              : "N/A"}
                          </div>
                          <div className="text-xs text-gray-500">Precision@K</div>
                        </div>
                        <div className="bg-white rounded-lg p-3 border text-center">
                          <div className="text-lg font-bold">
                            {currentRecallAtK != null
                              ? Number(currentRecallAtK).toFixed(3)
                              : "N/A"}
                          </div>
                          <div className="text-xs text-gray-500">Recall@K</div>
                        </div>
                        <div className="bg-white rounded-lg p-3 border text-center">
                          <div className="text-lg font-bold">
                            {currentNdcgAtK != null
                              ? Number(currentNdcgAtK).toFixed(3)
                              : "N/A"}
                          </div>
                          <div className="text-xs text-gray-500">NDCG@K</div>
                        </div>
                        <div className="bg-white rounded-lg p-3 border text-center">
                          <div className="text-lg font-bold">
                            {currentHitRateAtK != null
                              ? Number(currentHitRateAtK).toFixed(3)
                              : "N/A"}
                          </div>
                          <div className="text-xs text-gray-500">Hit Rate@K</div>
                        </div>
                      </div>
                      {/* Current model ranking metrics chart */}
                      {(currentPrecisionAtK != null ||
                        currentRecallAtK != null ||
                        currentNdcgAtK != null ||
                        currentHitRateAtK != null) && (
                        <div className="bg-white rounded-lg border p-3">
                          <h4 className="text-sm font-semibold mb-2">
                            Current model ranking metrics
                          </h4>
                          <div className="h-36">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart
                                data={[
                                  {
                                    name: "metrics",
                                    precision_at_k: Number(currentPrecisionAtK ?? 0),
                                    recall_at_k: Number(currentRecallAtK ?? 0),
                                    ndcg_at_k: Number(currentNdcgAtK ?? 0),
                                    hit_rate_at_k: Number(currentHitRateAtK ?? 0),
                                  },
                                ]}
                              >
                                <XAxis dataKey="name" hide />
                                <YAxis
                                  domain={[0, 1]}
                                  tick={{ fontSize: 11 }}
                                />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="precision_at_k" fill="#6366f1" />
                                <Bar dataKey="recall_at_k" fill="#22c55e" />
                                <Bar dataKey="ndcg_at_k" fill="#f97316" />
                                <Bar dataKey="hit_rate_at_k" fill="#0ea5e9" />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                            <div className="rounded-md border p-2 bg-gray-50">
                              MAP@K:{" "}
                              {currentMapAtK != null ? currentMapAtK.toFixed(3) : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              MRR@K:{" "}
                              {currentMrrAtK != null ? currentMrrAtK.toFixed(3) : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              K: {currentK != null ? currentK.toFixed(0) : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Hits@K: {hitsAtK != null ? hitsAtK.toFixed(0) : "-"}
                            </div>
                          </div>
                        </div>
                      )}
                      {(cm.tp != null ||
                        cm.fp != null ||
                        cm.tn != null ||
                        cm.fn != null) && (
                        <div className="bg-white rounded-lg border p-3">
                          <h4 className="text-sm font-semibold mb-2">
                            Confusion matrix graph (current model)
                          </h4>
                          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                            <div
                              className="rounded-md border p-2 text-center"
                              style={{
                                backgroundColor: `rgba(16,185,129,${Math.max(0.1, Number(cm.tn ?? 0) / confusionMax)})`,
                              }}
                            >
                              <div className="font-semibold">TN</div>
                              <div>{cm.tn ?? 0}</div>
                            </div>
                            <div
                              className="rounded-md border p-2 text-center"
                              style={{
                                backgroundColor: `rgba(244,63,94,${Math.max(0.1, Number(cm.fp ?? 0) / confusionMax)})`,
                              }}
                            >
                              <div className="font-semibold">FP</div>
                              <div>{cm.fp ?? 0}</div>
                            </div>
                            <div
                              className="rounded-md border p-2 text-center"
                              style={{
                                backgroundColor: `rgba(249,115,22,${Math.max(0.1, Number(cm.fn ?? 0) / confusionMax)})`,
                              }}
                            >
                              <div className="font-semibold">FN</div>
                              <div>{cm.fn ?? 0}</div>
                            </div>
                            <div
                              className="rounded-md border p-2 text-center"
                              style={{
                                backgroundColor: `rgba(34,197,94,${Math.max(0.1, Number(cm.tp ?? 0) / confusionMax)})`,
                              }}
                            >
                              <div className="font-semibold">TP</div>
                              <div>{cm.tp ?? 0}</div>
                            </div>
                          </div>
                          <div className="h-40">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={confusionBars}>
                                <XAxis dataKey="name" hide />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="tp" fill="#22c55e" />
                                <Bar dataKey="fp" fill="#f43f5e" />
                                <Bar dataKey="tn" fill="#10b981" />
                                <Bar dataKey="fn" fill="#f97316" />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}
                      {(errorRate != null ||
                        mae != null ||
                        rmse != null ||
                        coverage != null) && (
                        <div className="bg-white rounded-lg border p-3">
                          <h4 className="text-sm font-semibold mb-2">
                            Error and coverage diagnostics
                          </h4>
                          <div className="h-44">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={diagnosticsBars}>
                                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                                <Tooltip />
                                <Bar dataKey="value" fill="#6366f1" />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs mt-2">
                            <div className="rounded-md border p-2 bg-gray-50">
                              Recommended count:{" "}
                              {recommendedCount != null
                                ? recommendedCount.toFixed(0)
                                : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Valid recommendations:{" "}
                              {validRecommendations != null
                                ? validRecommendations.toFixed(0)
                                : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Invalid recommendations:{" "}
                              {invalidRecommendations != null
                                ? invalidRecommendations.toFixed(0)
                                : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Metrics mode:{" "}
                              {String(currentModelMetrics.metrics_mode ?? "-")}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Positive pool size:{" "}
                              {positivePoolSize != null
                                ? positivePoolSize.toFixed(0)
                                : "-"}
                            </div>
                          </div>
                        </div>
                      )}
                      {currentPrecisionAtK == null &&
                        currentRecallAtK == null &&
                        currentNdcgAtK == null &&
                        currentHitRateAtK == null && (
                        <div className="bg-amber-50 border border-amber-200 text-amber-700 rounded-lg p-3 text-xs">
                          Ranking metrics unavailable yet for this model/query.
                        </div>
                      )}
                      {currentPrecisionAtK === 0 &&
                        currentRecallAtK === 0 &&
                        currentNdcgAtK === 0 &&
                        currentHitRateAtK === 0 && (
                        <div className="bg-amber-50 border border-amber-200 text-amber-700 rounded-lg p-3 text-xs">
                          Ranking metrics are all zero for this query and top-K.
                          This usually means no relevant gift was found in the top
                          results for current constraints.
                        </div>
                      )}
                      {md && (
                        <div className="bg-white rounded-lg border p-3">
                          <h4 className="text-sm font-semibold mb-2">
                            {md.label} - all model metrics
                          </h4>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                            {currentRows.map(([k, v]) => (
                              <div key={k} className="rounded-md border p-2 bg-gray-50">
                                <div className="font-semibold text-gray-800 break-words">
                                  {formatMetricValue(k, v)}
                                </div>
                                <div className="text-gray-500">{metricLabel(k)}</div>
                              </div>
                            ))}
                          </div>
                          {confusion && (
                            <div className="mt-2 rounded-md border p-2 bg-gray-50 text-xs">
                              <div className="font-semibold mb-1">Confusion matrix</div>
                              <div className="font-mono">
                                {formatMetricValue("confusion_matrix", confusion)}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                      {compareGift && (
                        <div className="bg-white rounded-lg border p-3">
                          <h4 className="text-sm font-semibold mb-2">
                            Current model gift diagnostics
                          </h4>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="rounded-md border p-2 bg-gray-50">
                              Valid recommendation:{" "}
                              {compareGift.is_valid_recommendation == null
                                ? "-"
                                : compareGift.is_valid_recommendation
                                  ? "True"
                                  : "False"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Validity score:{" "}
                              {compareGift.validity_score != null
                                ? compareGift.validity_score.toFixed(3)
                                : "-"}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Current rank score: {compareGift.score.toFixed(3)}
                            </div>
                            <div className="rounded-md border p-2 bg-gray-50">
                              Query cosine:{" "}
                              {compareGift.query_cosine_similarity != null
                                ? compareGift.query_cosine_similarity.toFixed(3)
                                : "-"}
                            </div>
                            {currentModelKey === "content" && (
                              <div className="rounded-md border p-2 bg-gray-50">
                                Content similarity:{" "}
                                {compareGift.content_cosine_similarity != null
                                  ? compareGift.content_cosine_similarity.toFixed(3)
                                  : "-"}
                              </div>
                            )}
                            {currentModelKey === "collaborative" && (
                              <div className="rounded-md border p-2 bg-gray-50">
                                Collaborative similarity:{" "}
                                {compareGift.collaborative_cosine_similarity != null
                                  ? compareGift.collaborative_cosine_similarity.toFixed(3)
                                  : "-"}
                              </div>
                            )}
                            {currentModelKey === "knowledge" && (
                              <div className="rounded-md border p-2 bg-gray-50">
                                Knowledge similarity:{" "}
                                {compareGift.knowledge_similarity != null
                                  ? compareGift.knowledge_similarity.toFixed(3)
                                  : "-"}
                              </div>
                            )}
                            {currentModelKey === "rag" && (
                              <div className="rounded-md border p-2 bg-gray-50">
                                RAG similarity:{" "}
                                {compareGift.rag_similarity != null
                                  ? compareGift.rag_similarity.toFixed(3)
                                  : "-"}
                              </div>
                            )}
                            {currentModelKey === "hybrid" && (
                              <>
                                <div className="rounded-md border p-2 bg-gray-50">
                                  Content similarity:{" "}
                                  {compareGift.content_cosine_similarity != null
                                    ? compareGift.content_cosine_similarity.toFixed(3)
                                    : "-"}
                                </div>
                                <div className="rounded-md border p-2 bg-gray-50">
                                  Collaborative similarity:{" "}
                                  {compareGift.collaborative_cosine_similarity != null
                                    ? compareGift.collaborative_cosine_similarity.toFixed(3)
                                    : "-"}
                                </div>
                                <div className="rounded-md border p-2 bg-gray-50">
                                  Knowledge similarity:{" "}
                                  {compareGift.knowledge_similarity != null
                                    ? compareGift.knowledge_similarity.toFixed(3)
                                    : "-"}
                                </div>
                              </>
                            )}
                            <div className="rounded-md border p-2 bg-gray-50">
                              Hobby overlap:{" "}
                              {compareGift.hobby_overlap != null
                                ? (compareGift.hobby_overlap * 100).toFixed(0) + "%"
                                : "-"}
                            </div>
                          </div>
                          {compareGift.validity_reasons &&
                            compareGift.validity_reasons.length > 0 && (
                              <div className="mt-2 text-xs text-gray-600">
                                Reasons: {compareGift.validity_reasons.join(", ")}
                              </div>
                            )}
                        </div>
                      )}
                      <div className="bg-white rounded-lg border p-3">
                        <h4 className="text-sm font-semibold mb-2">
                          This gift across all models
                        </h4>
                        <div className="overflow-auto border rounded-lg">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-50 text-gray-600">
                              <tr>
                                <th className="text-left px-3 py-2">Model</th>
                                <th className="text-right px-3 py-2">Rank score</th>
                                <th className="text-right px-3 py-2">Validity</th>
                                <th className="text-right px-3 py-2">Query cosine</th>
                              </tr>
                            </thead>
                            <tbody>
                              {modelGiftDiagnostics.map(({ modelResult, gift }) => (
                                <tr key={modelResult.model} className="border-t">
                                  <td className="px-3 py-2">{modelResult.label}</td>
                                  <td className="px-3 py-2 text-right">
                                    {gift ? gift.score.toFixed(3) : "Not in top results"}
                                  </td>
                                  <td className="px-3 py-2 text-right">
                                    {gift?.validity_score != null
                                      ? gift.validity_score.toFixed(3)
                                      : "-"}
                                  </td>
                                  <td className="px-3 py-2 text-right">
                                    {gift?.query_cosine_similarity != null
                                      ? gift.query_cosine_similarity.toFixed(3)
                                      : "-"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      <div className="bg-white rounded-lg border p-3">
                        <h4 className="text-sm font-semibold mb-2">
                          All models headline metrics (current query)
                        </h4>
                        <div className="h-56 mb-3">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={allModelMetricSeries}>
                              <XAxis dataKey="model" tick={{ fontSize: 10 }} />
                              <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                              <Tooltip />
                              <Legend />
                              <Bar dataKey="precision_at_k" fill="#6366f1" />
                              <Bar dataKey="recall_at_k" fill="#22c55e" />
                              <Bar dataKey="ndcg_at_k" fill="#f97316" />
                              <Bar dataKey="hit_rate_at_k" fill="#0ea5e9" />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="overflow-auto border rounded-lg">
                          <table className="w-full text-xs">
                            <thead className="bg-gray-50 text-gray-600">
                              <tr>
                                <th className="text-left px-3 py-2">Model</th>
                                <th className="text-right px-3 py-2">P@K</th>
                                <th className="text-right px-3 py-2">R@K</th>
                                <th className="text-right px-3 py-2">NDCG@K</th>
                                <th className="text-right px-3 py-2">Hit@K</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(data?.models ?? []).map((modelResult) => {
                                const precisionAtK =
                                  metricAsNumber(modelResult.metrics.precision_at_k) ??
                                  metricAsNumber(modelResult.metrics.precision);
                                const recallAtK =
                                  metricAsNumber(modelResult.metrics.recall_at_k) ??
                                  metricAsNumber(modelResult.metrics.recall);
                                const ndcgAtK = metricAsNumber(
                                  modelResult.metrics.ndcg_at_k,
                                );
                                const hitAtK = metricAsNumber(
                                  modelResult.metrics.hit_rate_at_k,
                                );
                                return (
                                  <tr key={modelResult.model} className="border-t">
                                    <td className="px-3 py-2">{modelResult.label}</td>
                                    <td className="px-3 py-2 text-right">
                                      {precisionAtK != null
                                        ? precisionAtK.toFixed(3)
                                        : "-"}
                                    </td>
                                    <td className="px-3 py-2 text-right">
                                      {recallAtK != null ? recallAtK.toFixed(3) : "-"}
                                    </td>
                                    <td className="px-3 py-2 text-right">
                                      {ndcgAtK != null ? ndcgAtK.toFixed(3) : "-"}
                                    </td>
                                    <td className="px-3 py-2 text-right">
                                      {hitAtK != null ? hitAtK.toFixed(3) : "-"}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
