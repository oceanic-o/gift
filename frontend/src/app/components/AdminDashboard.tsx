import { useState, useEffect, useCallback } from "react";
import { motion } from "motion/react";
import {
  BarChart3,
  Users,
  Activity,
  RefreshCw,
  FlaskConical,
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Gift,
  Trash2,
  Plus,
  Database,
  UploadCloud,
  Settings,
  Key,
  Save,
} from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Slider } from "./ui/slider";
import { Label } from "./ui/label";
import { Navbar } from "./Navbar";
import {
  getStats,
  getAllUsers,
  getAllInteractions,
  retrainModel,
  evaluateModel,
  listGifts,
  listCategories,
  createGift,
  deleteGift,
  createCategory,
  importGifts,
  resetCatalog,
  embedGifts,
  deleteUser,
  deleteInteraction,
  updateUserRole,
  ingestWebGifts,
  getDatasetMetadata,
  getDatabaseSchema,
  runAdminQuery,
  getEnvSettings,
  updateEnvSettings,
  type AdminStats,
  type AdminUser,
  type AdminInteraction,
  type AdminGift,
  type CategoryResponse,
  type GiftCreatePayload,
  type DatasetMetadata,
  type DatabaseSchema,
  type AdminQueryResponse,
  type EnvSettingsResponse,
} from "@/lib/api/admin";

type Tab =
  | "overview"
  | "users"
  | "interactions"
  | "gifts"
  | "data"
  | "model"
  | "tuning"
  | "settings";

interface AdminDashboardProps {
  onBack: () => void;
  onLogoClick: () => void;
}

const TUNING_BOOSTS = [
  { key: "BOOST_WEIGHT_HOBBIES", label: "Hobbies & Interests", icon: "✨" },
  { key: "BOOST_WEIGHT_OCCASION", label: "Occasion Match", icon: "📅" },
  { key: "BOOST_WEIGHT_RELATIONSHIP", label: "Relationship Match", icon: "❤️" },
  { key: "BOOST_WEIGHT_AGE", label: "Age Group Bonus", icon: "🎂" },
  { key: "BOOST_WEIGHT_GENDER", label: "Gender Bonus", icon: "👤" },
  { key: "BOOST_WEIGHT_PRICE", label: "Budget/Price Fit", icon: "💰" },
] as const;

type TuningKey = (typeof TUNING_BOOSTS)[number]["key"];

const TUNING_DEFAULTS: Record<TuningKey, number> = {
  BOOST_WEIGHT_HOBBIES: 0.35,
  BOOST_WEIGHT_OCCASION: 0.18,
  BOOST_WEIGHT_RELATIONSHIP: 0.12,
  BOOST_WEIGHT_AGE: 0.08,
  BOOST_WEIGHT_GENDER: 0.06,
  BOOST_WEIGHT_PRICE: 0.05,
};

export function AdminDashboard({ onBack, onLogoClick }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [interactions, setInteractions] = useState<AdminInteraction[]>([]);
  const [gifts, setGifts] = useState<AdminGift[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [newGift, setNewGift] = useState<GiftCreatePayload>({
    title: "",
    description: "",
    category_id: 0,
    price: 0,
    occasion: "",
    relationship: "",
    image_url: "",
    product_url: "",
  });
  const [newCategory, setNewCategory] = useState("");
  const [importLimit, setImportLimit] = useState(200);
  const [importForce, setImportForce] = useState(false);
  const [resetLimit, setResetLimit] = useState<number | "">("");
  const [resetEmbedBatch, setResetEmbedBatch] = useState(100);
  const [resetConfirm, setResetConfirm] = useState(false);
  const [datasetInfo, setDatasetInfo] = useState<DatasetMetadata | null>(null);
  const [dbSchema, setDbSchema] = useState<DatabaseSchema | null>(null);
  const [schemaStatus, setSchemaStatus] = useState<
    "idle" | "loading" | "error"
  >("idle");
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [queryText, setQueryText] = useState(
    "SELECT id, title, price FROM gifts ORDER BY id DESC LIMIT 5",
  );
  const [queryLimit, setQueryLimit] = useState(200);
  const [queryResult, setQueryResult] = useState<AdminQueryResponse | null>(
    null,
  );
  const [queryStatus, setQueryStatus] = useState<"idle" | "loading" | "error">(
    "idle",
  );
  const [queryError, setQueryError] = useState<string | null>(null);
  const [webQuery, setWebQuery] = useState("");
  const [webLimit, setWebLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [tuningSaving, setTuningSaving] = useState(false);
  const [envSettings, setEnvSettings] = useState<EnvSettingsResponse | null>(
    null,
  );
  const [backendDraft, setBackendDraft] = useState<Record<string, string>>({});
  const [frontendDraft, setFrontendDraft] = useState<Record<string, string>>(
    {},
  );
  const [settingsDirty, setSettingsDirty] = useState<{
    backend: boolean;
    frontend: boolean;
  }>({ backend: false, frontend: false });
  const [settingsSaving, setSettingsSaving] = useState<
    "backend" | "frontend" | null
  >(null);
  const [tuningValues, setTuningValues] =
    useState<Record<TuningKey, number>>(TUNING_DEFAULTS);
  const [tuningDirty, setTuningDirty] = useState(false);
  const [actionMsg, setActionMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const loadEnvSettings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getEnvSettings();
      setEnvSettings(data);
    } catch {
      setEnvSettings(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSettingChange = (
    target: "backend" | "frontend",
    key: string,
    value: string,
  ) => {
    if (target === "backend") {
      setBackendDraft((prev) => ({ ...prev, [key]: value }));
    } else {
      setFrontendDraft((prev) => ({ ...prev, [key]: value }));
    }
    setSettingsDirty((prev) => ({ ...prev, [target]: true }));
  };

  const handleSaveSettingsSection = async (target: "backend" | "frontend") => {
    const original = target === "backend" ? envSettings?.backend : envSettings?.frontend;
    const draft = target === "backend" ? backendDraft : frontendDraft;
    const changed = Object.fromEntries(
      Object.entries(draft).filter(([k, v]) => (original?.[k] ?? "") !== v),
    );

    if (Object.keys(changed).length === 0) {
      setActionMsg({
        type: "success",
        text: `No ${target} setting changes to apply.`,
      });
      setSettingsDirty((prev) => ({ ...prev, [target]: false }));
      return;
    }

    setSettingsSaving(target);
    setActionMsg(null);
    try {
      await updateEnvSettings({
        [target]: changed,
      });
      await loadEnvSettings();
      setSettingsDirty((prev) => ({ ...prev, [target]: false }));
      setActionMsg({
        type: "success",
        text:
          target === "backend"
            ? "Backend settings applied successfully."
            : "Frontend settings saved. Rebuild frontend container to apply at runtime.",
      });
    } catch (e: any) {
      setActionMsg({
        type: "error",
        text:
          e?.name === "AbortError"
            ? `Request timed out while updating ${target} settings. Try again.`
            : (e?.message ?? `${target} settings update failed.`),
      });
    } finally {
      setSettingsSaving(null);
    }
  };

  const loadStats = useCallback(async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch {
      // ignore
    }
  }, []);

  const loadUsers = useCallback(async () => {
    try {
      const data = await getAllUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch {
      setUsers([]);
    }
  }, []);

  const loadInteractions = useCallback(async () => {
    try {
      const data = await getAllInteractions();
      setInteractions(Array.isArray(data) ? data : []);
    } catch {
      setInteractions([]);
    }
  }, []);

  const loadGifts = useCallback(async () => {
    try {
      const data = await listGifts(50);
      setGifts(Array.isArray(data) ? data : []);
    } catch {
      setGifts([]);
    }
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const data = await listCategories();
      setCategories(Array.isArray(data) ? data : []);
    } catch {
      setCategories([]);
    }
  }, []);

  const loadDatasetInfo = useCallback(async () => {
    try {
      const data = await getDatasetMetadata();
      setDatasetInfo(data);
    } catch {
      setDatasetInfo(null);
    }
  }, []);

  const loadDatabaseSchema = useCallback(async () => {
    setSchemaStatus("loading");
    setSchemaError(null);
    try {
      const data = await getDatabaseSchema();
      setDbSchema(data);
      setSchemaStatus("idle");
      setSchemaError(null);
    } catch (err: any) {
      setDbSchema(null);
      setSchemaStatus("error");
      setSchemaError(err?.message || "Failed to load schema.");
    }
  }, []);

  const handleLoadSchema = async () => {
    await loadDatabaseSchema();
  };

  const handleRunQuery = async () => {
    if (!queryText.trim()) return;
    setQueryStatus("loading");
    setQueryError(null);
    try {
      const result = await runAdminQuery({
        sql: queryText,
        max_rows: queryLimit,
      });
      setQueryResult(result);
      setQueryStatus("idle");
      setQueryError(null);
    } catch (err: any) {
      setQueryResult(null);
      setQueryStatus("error");
      setQueryError(err?.message || "Query failed.");
    }
  };

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    if (activeTab === "users") loadUsers();
    if (activeTab === "interactions") loadInteractions();
    if (activeTab === "gifts") {
      loadGifts();
      loadCategories();
    }
    if (activeTab === "data") {
      loadDatasetInfo();
      loadDatabaseSchema();
    }
    if (activeTab === "settings") {
      loadEnvSettings();
    }
  }, [
    activeTab,
    loadUsers,
    loadInteractions,
    loadGifts,
    loadCategories,
    loadDatasetInfo,
    loadDatabaseSchema,
    loadEnvSettings,
  ]);

  useEffect(() => {
    if (!envSettings?.backend) return;
    const next: Record<TuningKey, number> = { ...TUNING_DEFAULTS };
    for (const { key } of TUNING_BOOSTS) {
      const raw = Number(envSettings.backend[key]);
      next[key] = Number.isFinite(raw) ? raw : TUNING_DEFAULTS[key];
    }
    setTuningValues(next);
    setTuningDirty(false);
  }, [envSettings]);

  useEffect(() => {
    if (!envSettings) return;
    setBackendDraft(envSettings.backend ?? {});
    setFrontendDraft(envSettings.frontend ?? {});
    setSettingsDirty({ backend: false, frontend: false });
  }, [envSettings]);

  const handleDeleteUser = async (userId: number) => {
    setLoading(true);
    setActionMsg(null);
    try {
      await deleteUser(userId);
      await loadUsers();
      setActionMsg({ type: "success", text: "User removed." });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Delete failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateUserRole = async (userId: number, role: string) => {
    setLoading(true);
    setActionMsg(null);
    try {
      await updateUserRole(userId, role);
      await loadUsers();
      setActionMsg({ type: "success", text: `Role updated to ${role}.` });
    } catch (e: any) {
      setActionMsg({
        type: "error",
        text: e?.message ?? "Role update failed.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteInteraction = async (interactionId: number) => {
    setLoading(true);
    setActionMsg(null);
    try {
      await deleteInteraction(interactionId);
      await loadInteractions();
      setActionMsg({ type: "success", text: "Interaction removed." });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Delete failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCategory = async () => {
    if (!newCategory.trim()) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await createCategory(newCategory.trim());
      setNewCategory("");
      await loadCategories();
      setActionMsg({ type: "success", text: "Category created." });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Create failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGift = async () => {
    if (!newGift.title || !newGift.category_id) return;
    setLoading(true);
    setActionMsg(null);
    try {
      await createGift({
        ...newGift,
        price: Number(newGift.price),
      });
      setNewGift({
        title: "",
        description: "",
        category_id: newGift.category_id,
        price: 0,
        occasion: "",
        relationship: "",
        image_url: "",
        product_url: "",
      });
      await loadGifts();
      setActionMsg({ type: "success", text: "Gift created." });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Create failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadMetadata = () => {
    if (!datasetInfo) return;
    const blob = new Blob([JSON.stringify(datasetInfo, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "gifts_50k_metadata.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleDeleteGift = async (giftId: number) => {
    setLoading(true);
    setActionMsg(null);
    try {
      await deleteGift(giftId);
      await loadGifts();
      setActionMsg({ type: "success", text: "Gift removed." });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Delete failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    setLoading(true);
    setActionMsg(null);
    try {
      const res = await importGifts(importLimit, importForce);
      await loadGifts();
      setActionMsg({
        type: "success",
        text: `${res.message}. Created: ${res.created}, Skipped: ${res.skipped}`,
      });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Import failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleEmbed = async () => {
    setLoading(true);
    setActionMsg(null);
    try {
      const res = await embedGifts();
      setActionMsg({
        type: "success",
        text: res.message ?? "Embeddings updated.",
      });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Embedding failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleResetCatalog = async () => {
    setLoading(true);
    setActionMsg(null);
    try {
      const res = await resetCatalog(
        resetLimit === "" ? undefined : Number(resetLimit),
        resetEmbedBatch,
      );
      await loadGifts();
      setActionMsg({
        type: "success",
        text: res.message ?? "Catalog reset completed.",
      });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Reset failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleIngestWeb = async () => {
    if (!webQuery.trim()) return;
    setLoading(true);
    setActionMsg(null);
    try {
      const result = await ingestWebGifts(webQuery.trim(), webLimit);
      setActionMsg({
        type: "success",
        text: `Web gifts ingested. Created ${result.created}, skipped ${result.skipped}.`,
      });
      setWebQuery("");
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Web ingest failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleRetrain = async () => {
    setLoading(true);
    setActionMsg(null);
    try {
      await retrainModel();
      setActionMsg({
        type: "success",
        text: "Model retrained successfully.",
      });
    } catch (e: any) {
      setActionMsg({
        type: "error",
        text:
          e?.name === "AbortError"
            ? "Request timed out while retraining. Try again."
            : (e?.message ?? "Retrain failed."),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluate = async () => {
    setLoading(true);
    setActionMsg(null);
    try {
      const result = await evaluateModel();
      const rows = Array.isArray((result as any)?.results)
        ? (result as any).results
        : [];
      const best = [...rows]
        .filter((r: any) => typeof r?.f1_score === "number")
        .sort((a: any, b: any) => (b.f1_score ?? 0) - (a.f1_score ?? 0))[0];
      setActionMsg({
        type: "success",
        text:
          rows.length > 0
            ? `Evaluation complete for ${rows.length} models (${result.users_evaluated} users). Best F1: ${best?.model_name ?? "n/a"} ${typeof best?.f1_score === "number" ? `(${best.f1_score.toFixed(4)})` : ""}`
            : (result?.message ?? "Evaluation complete."),
      });
    } catch (e: any) {
      setActionMsg({ type: "error", text: e?.message ?? "Evaluation failed." });
    } finally {
      setLoading(false);
    }
  };

  const handleApplyTuning = async () => {
    setTuningSaving(true);
    setActionMsg(null);
    try {
      const payload: Record<string, string> = {};
      for (const { key } of TUNING_BOOSTS) {
        payload[key] = tuningValues[key].toFixed(2);
      }
      await updateEnvSettings({ backend: payload });
      await loadEnvSettings();
      setTuningDirty(false);
      setActionMsg({
        type: "success",
        text: "Tuning weights updated successfully.",
      });
    } catch (e: any) {
      setActionMsg({
        type: "error",
        text:
          e?.name === "AbortError"
            ? "Request timed out while applying tuning. Try again."
            : (e?.message ?? "Tuning update failed."),
      });
    } finally {
      setTuningSaving(false);
    }
  };


  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "Overview", icon: <BarChart3 size={18} /> },
    { id: "users", label: "Users", icon: <Users size={18} /> },
    { id: "interactions", label: "Interactions", icon: <Activity size={18} /> },
    { id: "gifts", label: "Gifts", icon: <Gift size={18} /> },
    { id: "data", label: "Data Tools", icon: <Database size={18} /> },
    { id: "model", label: "Model", icon: <RefreshCw size={18} /> },
    { id: "tuning", label: "Tuning", icon: <Activity size={18} /> },
    { id: "settings", label: "Settings", icon: <Settings size={18} /> },
  ];

  return (
    <div className="min-h-screen bg-linear-to-br from-stone-50 via-rose-50 to-orange-50 flex flex-col">
      <Navbar
        onLogoClick={onLogoClick}
        showAuthButtons={false}
        showNavLinks={false}
      />

      <div className="flex-1 max-w-7xl mx-auto px-6 py-10 w-full">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 flex items-center gap-4"
        >
          <Button variant="ghost" onClick={onBack} className="gap-2">
            <ArrowLeft size={18} />
            Back
          </Button>
          <div>
            <h1 className="text-4xl font-bold bg-linear-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
              Admin Dashboard
            </h1>
            <p className="text-gray-500 mt-1">
              Manage gifts, users, and model performance
            </p>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-8 flex-wrap">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium text-sm transition-all ${
                activeTab === tab.id
                  ? "bg-linear-to-r from-rose-500 to-orange-500 text-white shadow-lg"
                  : "bg-white text-gray-600 hover:bg-rose-50 border border-rose-100"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {actionMsg && (
          <div
            className={`mb-6 flex items-center gap-3 p-4 rounded-xl text-sm border ${
              actionMsg.type === "success"
                ? "bg-green-50 text-green-700 border-green-200"
                : "bg-red-50 text-red-700 border-red-200"
            }`}
          >
            {actionMsg.type === "success" ? (
              <CheckCircle2 size={18} />
            ) : (
              <AlertCircle size={18} />
            )}
            {actionMsg.text}
          </div>
        )}

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-6"
          >
            {stats ? (
              <div className="contents">
                {[
                  { label: "Total Users", value: stats.total_users },
                  { label: "Total Gifts", value: stats.total_gifts },
                  {
                    label: "Total Interactions",
                    value: stats.total_interactions,
                  },
                  {
                    label: "Total Recommendations",
                    value: stats.total_recommendations,
                  },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="bg-white rounded-2xl p-6 shadow-md border border-rose-100 flex flex-col gap-2"
                  >
                    <span className="text-sm text-gray-500">{label}</span>
                    <span className="text-3xl font-bold text-rose-600">
                      {value?.toLocaleString() ?? "—"}
                    </span>
                  </div>
                ))}
                {stats.interaction_breakdown &&
                  Object.entries(stats.interaction_breakdown).map(([k, v]) => (
                    <div
                      key={k}
                      className="bg-white rounded-2xl p-6 shadow-md border border-rose-100 flex flex-col gap-2"
                    >
                      <span className="text-sm text-gray-500 capitalize">
                        {k}
                      </span>
                      <span className="text-3xl font-bold text-orange-500">
                        {v}
                      </span>
                    </div>
                  ))}

                {/* Popular Categories */}
                {stats.popular_categories && stats.popular_categories.length > 0 && (
                  <div className="col-span-2 md:col-span-4 bg-white rounded-2xl p-6 shadow-md border border-rose-100">
                    <h4 className="text-sm font-semibold text-gray-600 mb-4">Popular Categories</h4>
                    <div className="space-y-3">
                      {stats.popular_categories.map((cat: any) => {
                        const maxCount = Math.max(...stats.popular_categories.map((c: any) => c.count || 0), 1);
                        const pct = Math.round(((cat.count || 0) / maxCount) * 100);
                        return (
                          <div key={cat.name} className="flex items-center gap-3">
                            <span className="text-sm text-gray-700 w-32 truncate" title={cat.name}>{cat.name}</span>
                            <div className="flex-1 bg-rose-100 rounded-full h-4 overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-rose-500 to-orange-400 rounded-full transition-all duration-500"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-sm font-medium text-rose-600 w-12 text-right">{cat.count}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              </div>
            ) : (
              <div className="col-span-4 flex items-center justify-center py-20 text-gray-400 gap-3">
                <Loader2 className="animate-spin" size={24} />
                Loading stats…
              </div>
            )}
          </motion.div>
        )}

        {/* Users Tab */}
        {activeTab === "users" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="bg-white rounded-2xl shadow-md border border-rose-100 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-rose-50 text-rose-700">
                  <tr>
                    <th className="text-left px-6 py-4">ID</th>
                    <th className="text-left px-6 py-4">Name</th>
                    <th className="text-left px-6 py-4">Email</th>
                    <th className="text-left px-6 py-4">Role</th>
                    <th className="text-left px-6 py-4">Joined</th>
                    <th className="text-left px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="text-center py-12 text-gray-400"
                      >
                        No users found
                      </td>
                    </tr>
                  ) : (
                    users.map((u: any, i) => (
                      <tr
                        key={u.id ?? i}
                        className="border-t border-rose-50 hover:bg-rose-50/40 transition-colors"
                      >
                        <td className="px-6 py-4 text-gray-400 font-mono text-xs">
                          {u.id}
                        </td>
                        <td className="px-6 py-4 font-medium">
                          {u.name ?? u.full_name ?? "—"}
                        </td>
                        <td className="px-6 py-4">{u.email}</td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-semibold ${
                              u.role === "admin"
                                ? "bg-rose-100 text-rose-700"
                                : "bg-gray-100 text-gray-600"
                            }`}
                          >
                            {u.role ?? "user"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-400">
                          {u.created_at
                            ? new Date(u.created_at).toLocaleDateString()
                            : "—"}
                        </td>
                        <td className="px-6 py-4">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDeleteUser(u.id)}
                            className="border-red-200 text-red-600 hover:bg-red-50"
                          >
                            <Trash2 size={14} className="mr-1" />
                            Remove
                          </Button>
                          {u.role !== "admin" ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                handleUpdateUserRole(u.id, "admin")
                              }
                              className="ml-2 border-rose-200 text-rose-600 hover:bg-rose-50"
                            >
                              Promote
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleUpdateUserRole(u.id, "user")}
                              className="ml-2 border-gray-200 text-gray-600 hover:bg-gray-50"
                            >
                              Demote
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* Interactions Tab */}
        {activeTab === "interactions" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="bg-white rounded-2xl shadow-md border border-rose-100 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-rose-50 text-rose-700">
                  <tr>
                    <th className="text-left px-6 py-4">User</th>
                    <th className="text-left px-6 py-4">Gift ID</th>
                    <th className="text-left px-6 py-4">Type</th>
                    <th className="text-left px-6 py-4">Rating</th>
                    <th className="text-left px-6 py-4">Date</th>
                    <th className="text-left px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {interactions.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="text-center py-12 text-gray-400"
                      >
                        <Gift className="mx-auto mb-3 opacity-30" size={32} />
                        No interactions yet
                      </td>
                    </tr>
                  ) : (
                    interactions.map((it: any, i) => (
                      <tr
                        key={it.id ?? i}
                        className="border-t border-rose-50 hover:bg-rose-50/40 transition-colors"
                      >
                        <td className="px-6 py-4 text-gray-500 font-mono text-xs">
                          {it.user_id}
                        </td>
                        <td className="px-6 py-4 text-gray-500 font-mono text-xs">
                          {it.gift_id}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2 py-1 rounded-full bg-orange-100 text-orange-700 text-xs font-semibold">
                            {it.interaction_type ?? it.type}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {it.rating != null ? (
                            <span className="font-medium">{it.rating} ⭐</span>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-gray-400">
                          {it.timestamp
                            ? new Date(it.timestamp).toLocaleDateString()
                            : "—"}
                        </td>
                        <td className="px-6 py-4">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDeleteInteraction(it.id)}
                            className="border-red-200 text-red-600 hover:bg-red-50"
                          >
                            <Trash2 size={14} className="mr-1" />
                            Remove
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* Gifts Tab */}
        {activeTab === "gifts" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid lg:grid-cols-[360px_1fr] gap-6"
          >
            <div className="bg-white rounded-2xl shadow-md border border-rose-100 p-6 space-y-4">
              <h3 className="font-semibold text-lg text-gray-800 flex items-center gap-2">
                <Plus size={18} className="text-rose-500" />
                Add Gift
              </h3>
              <div className="space-y-3">
                <div>
                  <Label>Title</Label>
                  <Input
                    value={newGift.title}
                    onChange={(e) =>
                      setNewGift({ ...newGift, title: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Description</Label>
                  <textarea
                    value={newGift.description ?? ""}
                    onChange={(e) =>
                      setNewGift({ ...newGift, description: e.target.value })
                    }
                    className="w-full rounded-lg border border-rose-100 px-3 py-2 text-sm"
                    rows={3}
                  />
                </div>
                <div>
                  <Label>Category</Label>
                  <select
                    value={newGift.category_id}
                    onChange={(e) =>
                      setNewGift({
                        ...newGift,
                        category_id: Number(e.target.value),
                      })
                    }
                    className="w-full rounded-lg border border-rose-100 px-3 py-2 text-sm"
                  >
                    <option value={0}>Select category</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label>Price</Label>
                  <Input
                    type="number"
                    value={newGift.price}
                    onChange={(e) =>
                      setNewGift({
                        ...newGift,
                        price: Number(e.target.value),
                      })
                    }
                  />
                </div>
                <div>
                  <Label>Occasion</Label>
                  <Input
                    value={newGift.occasion ?? ""}
                    onChange={(e) =>
                      setNewGift({ ...newGift, occasion: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Relationship</Label>
                  <Input
                    value={newGift.relationship ?? ""}
                    onChange={(e) =>
                      setNewGift({ ...newGift, relationship: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Image URL</Label>
                  <Input
                    value={newGift.image_url ?? ""}
                    onChange={(e) =>
                      setNewGift({ ...newGift, image_url: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Product URL</Label>
                  <Input
                    value={newGift.product_url ?? ""}
                    onChange={(e) =>
                      setNewGift({ ...newGift, product_url: e.target.value })
                    }
                  />
                </div>
                <Button
                  onClick={handleCreateGift}
                  disabled={loading || !newGift.title || !newGift.category_id}
                  className="w-full bg-linear-to-r from-rose-500 to-orange-500 text-white"
                >
                  {loading ? (
                    <Loader2 className="animate-spin mr-2" size={16} />
                  ) : (
                    <Plus size={16} className="mr-2" />
                  )}
                  Create Gift
                </Button>
              </div>

              <div className="border-t border-rose-100 pt-4 space-y-3">
                <h4 className="font-semibold text-gray-700">Add Category</h4>
                <Input
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  placeholder="Category name"
                />
                <Button
                  variant="outline"
                  onClick={handleCreateCategory}
                  disabled={loading || !newCategory.trim()}
                  className="w-full"
                >
                  <Plus size={16} className="mr-2" />
                  Create Category
                </Button>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-md border border-rose-100 overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-rose-100">
                <h3 className="font-semibold text-gray-800">Gift Catalog</h3>
                <Button variant="outline" onClick={loadGifts}>
                  Refresh
                </Button>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-rose-50 text-rose-700">
                  <tr>
                    <th className="text-left px-6 py-4">Title</th>
                    <th className="text-left px-6 py-4">Category</th>
                    <th className="text-left px-6 py-4">Price</th>
                    <th className="text-left px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {gifts.length === 0 ? (
                    <tr>
                      <td
                        colSpan={4}
                        className="text-center py-12 text-gray-400"
                      >
                        No gifts loaded
                      </td>
                    </tr>
                  ) : (
                    gifts.map((g) => (
                      <tr
                        key={g.id}
                        className="border-t border-rose-50 hover:bg-rose-50/40 transition-colors"
                      >
                        <td className="px-6 py-4 font-medium">{g.title}</td>
                        <td className="px-6 py-4 text-gray-500">
                          {g.category?.name ?? g.category_id}
                        </td>
                        <td className="px-6 py-4 text-gray-500">
                          ${g.price.toFixed(2)}
                        </td>
                        <td className="px-6 py-4">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDeleteGift(g.id)}
                            className="border-red-200 text-red-600 hover:bg-red-50"
                          >
                            <Trash2 size={14} className="mr-1" />
                            Remove
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* Data Tools Tab */}
        {activeTab === "data" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl"
          >
            <div className="bg-white rounded-2xl p-8 shadow-md border border-rose-100 space-y-6">
              <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                <Database className="text-rose-500" size={20} />
                Data Tools
              </h2>

              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                Fresh loads should use <strong>Reset Catalog</strong> to clear
                existing gifts before importing the new data file.
              </div>

              <div className="rounded-xl border border-rose-100 bg-white px-4 py-3 text-sm text-gray-600">
                Dataset source: <code>gift/data/gifts_50k.json</code> (JSON
                import).
              </div>

              {datasetInfo && (
                <div className="rounded-xl border border-rose-100 bg-white px-5 py-4 text-sm text-gray-600 space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-semibold text-gray-800">
                      Dataset Overview
                    </span>
                    <span className="text-xs text-rose-600 bg-rose-50 px-2 py-1 rounded-full">
                      Schema {datasetInfo.schema_version ?? "n/a"}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleDownloadMetadata}
                      className="ml-auto border-rose-200 text-rose-600 hover:bg-rose-50"
                    >
                      Download metadata
                    </Button>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400">
                        Total products
                      </p>
                      <p className="text-lg font-semibold text-gray-800">
                        {datasetInfo.total_products.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400">
                        Total users
                      </p>
                      <p className="text-lg font-semibold text-gray-800">
                        {datasetInfo.total_users?.toLocaleString() ?? "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400">
                        Categories
                      </p>
                      <p className="text-base font-medium text-gray-700">
                        {datasetInfo.categories.length}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400">
                        Occasions
                      </p>
                      <p className="text-base font-medium text-gray-700">
                        {datasetInfo.occasions.length}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400">
                        Generator
                      </p>
                      <p className="text-base font-medium text-gray-700">
                        {datasetInfo.generator_version ?? "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400">
                        Image source
                      </p>
                      <p className="text-base font-medium text-gray-700">
                        {datasetInfo.image_source ?? "—"}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                      Dataset path
                    </p>
                    <p className="text-xs text-gray-600 break-all">
                      {datasetInfo.file_path}
                    </p>
                  </div>
                  {datasetInfo.image_license && (
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                        Image license
                      </p>
                      <p className="text-xs text-gray-600">
                        {datasetInfo.image_license}
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                      Sample product fields
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {datasetInfo.product_fields.slice(0, 10).map((field) => (
                        <span
                          key={field}
                          className="px-2 py-1 text-xs bg-rose-50 text-rose-600 rounded-full"
                        >
                          {field}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                        Categories
                      </p>
                      <div className="max-h-32 overflow-y-auto rounded-lg border border-rose-100 bg-rose-50/40 p-3 text-xs text-gray-600 space-y-1">
                        {datasetInfo.categories.map((cat) => (
                          <div key={cat}>{cat}</div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                        Occasions
                      </p>
                      <div className="max-h-32 overflow-y-auto rounded-lg border border-rose-100 bg-rose-50/40 p-3 text-xs text-gray-600 space-y-1">
                        {datasetInfo.occasions.map((occasion) => (
                          <div key={occasion}>{occasion}</div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-rose-100 bg-white px-5 py-4 text-sm text-gray-600 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-gray-800">
                      Database Schema
                    </h3>
                    <p className="text-xs text-gray-400">
                      {dbSchema
                        ? `${dbSchema.tables.length} tables`
                        : "Load the current database structure"}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleLoadSchema}
                    disabled={schemaStatus === "loading"}
                    className="border-rose-200 text-rose-600 hover:bg-rose-50 gap-2"
                  >
                    {schemaStatus === "loading" ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <RefreshCw size={16} />
                    )}
                    {dbSchema ? "Refresh schema" : "Load schema"}
                  </Button>
                </div>

                {schemaStatus === "loading" && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Loader2 className="animate-spin" size={14} />
                    Loading database schema…
                  </div>
                )}

                {schemaStatus === "error" && (
                  <div className="rounded-lg border border-rose-100 bg-rose-50/40 px-4 py-3 text-xs text-rose-700">
                    {schemaError ||
                      "Unable to load the schema. Make sure you are logged in as an admin and the backend is running, then try again."}
                  </div>
                )}

                {dbSchema && (
                  <div className="space-y-3">
                    {dbSchema.tables.map((table) => (
                      <details
                        key={table.name}
                        className="rounded-lg border border-rose-100 bg-rose-50/40 p-3"
                      >
                        <summary className="cursor-pointer text-sm font-semibold text-rose-700 flex items-center justify-between">
                          <span>{table.name}</span>
                          <span className="text-xs text-gray-500">
                            {table.columns.length} columns
                          </span>
                        </summary>
                        <div className="mt-3 overflow-x-auto">
                          <table className="w-full text-xs text-gray-600">
                            <thead className="text-gray-400">
                              <tr>
                                <th className="text-left py-1 pr-2">Column</th>
                                <th className="text-left py-1 pr-2">Type</th>
                                <th className="text-left py-1 pr-2">
                                  Nullable
                                </th>
                                <th className="text-left py-1">Default</th>
                              </tr>
                            </thead>
                            <tbody>
                              {table.columns.map((column) => (
                                <tr key={`${table.name}-${column.name}`}>
                                  <td className="py-1 pr-2 font-medium text-gray-700">
                                    {column.name}
                                  </td>
                                  <td className="py-1 pr-2">{column.type}</td>
                                  <td className="py-1 pr-2">
                                    {column.nullable ? "Yes" : "No"}
                                  </td>
                                  <td className="py-1">
                                    {column.default ?? "—"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        {table.foreign_keys.length > 0 && (
                          <div className="mt-3 text-xs text-gray-500">
                            <p className="font-semibold text-gray-600 mb-1">
                              Foreign keys
                            </p>
                            <ul className="list-disc list-inside space-y-1">
                              {table.foreign_keys.map((fk, idx) => (
                                <li key={`${table.name}-fk-${idx}`}>
                                  {fk.constrained_columns.join(", ")} →{" "}
                                  {fk.referred_table}(
                                  {fk.referred_columns.join(", ")})
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </details>
                    ))}
                  </div>
                )}

                {!dbSchema && schemaStatus === "idle" && (
                  <div className="rounded-lg border border-rose-100 bg-rose-50/40 px-4 py-3 text-xs text-gray-600">
                    Database schema is not available yet. Use the “Load schema”
                    button above to fetch the latest table definitions.
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-rose-100 bg-white px-5 py-4 text-sm text-gray-600 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-gray-800">
                      Run SQL Query
                    </h3>
                    <p className="text-xs text-gray-400">
                      Read-only (SELECT/CTE)
                    </p>
                  </div>
                </div>
                <textarea
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  className="w-full rounded-lg border border-rose-100 px-3 py-2 text-xs font-mono text-gray-700"
                  rows={4}
                />
                <div className="flex flex-wrap items-end gap-3">
                  <div>
                    <Label>Max rows</Label>
                    <Input
                      type="number"
                      value={queryLimit}
                      onChange={(e) => setQueryLimit(Number(e.target.value))}
                    />
                  </div>
                  <Button
                    onClick={handleRunQuery}
                    disabled={queryStatus === "loading"}
                    className="bg-linear-to-r from-rose-500 to-orange-500 text-white gap-2"
                  >
                    {queryStatus === "loading" ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <Database size={16} />
                    )}
                    Run Query
                  </Button>
                </div>
                {queryStatus === "error" && (
                  <div className="text-xs text-red-600">
                    {queryError ||
                      "Query failed. Only SELECT/CTE queries are allowed."}
                  </div>
                )}
                {queryResult && (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-xs text-gray-600">
                      <thead className="text-gray-400">
                        <tr>
                          {queryResult.columns.map((col) => (
                            <th key={col} className="text-left py-1 pr-3">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {queryResult.rows.map((row, idx) => (
                          <tr key={`row-${idx}`}>
                            {row.map((cell, cellIdx) => (
                              <td
                                key={`${idx}-${cellIdx}`}
                                className="py-1 pr-3"
                              >
                                {cell === null ? "—" : String(cell)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="mt-2 text-xs text-gray-400">
                      Showing {queryResult.row_count} rows
                    </p>
                  </div>
                )}
              </div>

              <div className="border border-rose-100 rounded-xl p-6 space-y-4">
                <h3 className="font-semibold text-lg">Import from JSON</h3>
                <p className="text-gray-500 text-sm">
                  Populate gifts from <code>gift/data/gifts_50k.json</code>. Use
                  the reset option below when you need a clean reload.
                </p>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <Label>Limit</Label>
                    <Input
                      type="number"
                      value={importLimit}
                      onChange={(e) => setImportLimit(Number(e.target.value))}
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm mt-6">
                    <input
                      type="checkbox"
                      checked={importForce}
                      onChange={(e) => setImportForce(e.target.checked)}
                    />
                    Force import (not recommended if data already exists)
                  </label>
                </div>
                <Button
                  onClick={handleImport}
                  disabled={loading}
                  className="bg-linear-to-r from-rose-500 to-orange-500 text-white gap-2"
                >
                  {loading ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <UploadCloud size={16} />
                  )}
                  Import Gifts
                </Button>
              </div>

              <div className="border border-rose-100 rounded-xl p-6 space-y-4">
                <h3 className="font-semibold text-lg">Reset Catalog</h3>
                <p className="text-gray-500 text-sm">
                  Wipe gifts, re-import <code>gift/data/gifts_50k.json</code>,
                  embed, and retrain.
                </p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <Label>Limit (optional)</Label>
                    <Input
                      type="number"
                      value={resetLimit}
                      onChange={(e) =>
                        setResetLimit(
                          e.target.value ? Number(e.target.value) : "",
                        )
                      }
                      placeholder="e.g. 1000"
                    />
                  </div>
                  <div>
                    <Label>Embed batch size</Label>
                    <Input
                      type="number"
                      value={resetEmbedBatch}
                      onChange={(e) =>
                        setResetEmbedBatch(Number(e.target.value))
                      }
                    />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm text-rose-600">
                  <input
                    type="checkbox"
                    checked={resetConfirm}
                    onChange={(e) => setResetConfirm(e.target.checked)}
                  />
                  I understand this will delete existing gift data first
                </label>
                <Button
                  onClick={handleResetCatalog}
                  disabled={loading || !resetConfirm}
                  variant="outline"
                  className="gap-2 border-rose-200 text-rose-600 hover:bg-rose-50"
                >
                  {loading ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <Trash2 size={16} />
                  )}
                  Reset Catalog
                </Button>
              </div>

              <div className="border border-rose-100 rounded-xl p-6 space-y-4">
                <h3 className="font-semibold text-lg">Generate Embeddings</h3>
                <p className="text-gray-500 text-sm">
                  Create embeddings for gifts missing vectors.
                </p>
                <Button
                  onClick={handleEmbed}
                  disabled={loading}
                  variant="outline"
                  className="gap-2"
                >
                  {loading ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <Database size={16} />
                  )}
                  Generate Embeddings
                </Button>
              </div>

              <div className="border border-rose-100 rounded-xl p-6 space-y-4">
                <h3 className="font-semibold text-lg">Ingest Web Gifts</h3>
                <p className="text-gray-500 text-sm">
                  Fetch new gifts from the web, store in the web table, and
                  embed them.
                </p>
                <div className="space-y-3">
                  <div>
                    <Label>Search Query</Label>
                    <Input
                      value={webQuery}
                      onChange={(e) => setWebQuery(e.target.value)}
                      placeholder="e.g., gifts for hikers under $50"
                    />
                  </div>
                  <div>
                    <Label>Limit</Label>
                    <Input
                      type="number"
                      value={webLimit}
                      onChange={(e) => setWebLimit(Number(e.target.value))}
                    />
                  </div>
                </div>
                <Button
                  onClick={handleIngestWeb}
                  disabled={loading || !webQuery.trim()}
                  className="bg-linear-to-r from-rose-500 to-orange-500 text-white gap-2"
                >
                  {loading ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <UploadCloud size={16} />
                  )}
                  Ingest Web Gifts
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Model Tab */}
        {activeTab === "model" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-xl"
          >
            <div className="bg-white rounded-2xl p-8 shadow-md border border-rose-100 space-y-6">
              <h2 className="text-2xl font-bold text-gray-800">
                Model Management
              </h2>

              <div className="space-y-4">
                <div className="border border-rose-100 rounded-xl p-6">
                  <h3 className="font-semibold text-lg mb-2 flex items-center gap-2">
                    <RefreshCw className="text-rose-500" size={18} />
                    Retrain Model
                  </h3>
                  <p className="text-gray-500 text-sm mb-4">
                    Trigger a full model retraining using the latest interaction
                    data. This may take a few minutes.
                  </p>
                  <Button
                    onClick={handleRetrain}
                    disabled={loading}
                    className="bg-linear-to-r from-rose-500 to-orange-500 text-white gap-2"
                  >
                    {loading ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <RefreshCw size={16} />
                    )}
                    {loading ? "Running…" : "Start Retrain"}
                  </Button>
                </div>

                <div className="border border-rose-100 rounded-xl p-6">
                  <h3 className="font-semibold text-lg mb-2 flex items-center gap-2">
                    <FlaskConical className="text-pink-500" size={18} />
                    Evaluate Model
                  </h3>
                  <p className="text-gray-500 text-sm mb-4">
                    Evaluate all 5 models using stored user profile context
                    (age, gender, hobbies, occasion, relationship, budget)
                    from the database and refresh metrics.
                  </p>
                  <Button
                    onClick={handleEvaluate}
                    disabled={loading}
                    variant="outline"
                    className="border-rose-300 hover:bg-rose-50 gap-2"
                  >
                    {loading ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <FlaskConical size={16} />
                    )}
                    {loading ? "Running…" : "Evaluate"}
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Tuning Tab */}
        {activeTab === "tuning" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-3xl"
          >
            <div className="bg-white rounded-2xl p-8 shadow-md border border-rose-100 space-y-8">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                  <Activity className="text-rose-500" size={20} />
                  Recommender Tuning
                </h2>
                <div className="flex items-center gap-2 text-xs text-gray-400 bg-stone-50 px-3 py-1.5 rounded-full border border-stone-100">
                  <AlertCircle size={14} />
                  Changes take effect immediately
                </div>
              </div>

              <div className="grid gap-8">
                {TUNING_BOOSTS.map((boost) => (
                  <div key={boost.key} className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{boost.icon}</span>
                        <Label className="text-sm font-semibold text-gray-700">
                          {boost.label}
                        </Label>
                      </div>
                      <span className="text-sm font-bold text-rose-600 font-mono bg-rose-50 px-2 py-0.5 rounded">
                        {Math.round((tuningValues[boost.key] ?? 0) * 100)}%
                      </span>
                    </div>
                    <Slider
                      value={[Math.round((tuningValues[boost.key] ?? 0) * 100)]}
                      max={100}
                      step={1}
                      onValueChange={([val]) => {
                        setTuningValues((prev) => ({
                          ...prev,
                          [boost.key]: val / 100,
                        }));
                        setTuningDirty(true);
                      }}
                      className="w-full"
                    />
                    <p className="text-[10px] text-gray-400 leading-tight">
                      Influence of {boost.label.toLowerCase()} on the final recommendation score.
                    </p>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-rose-50 flex justify-between items-center text-xs text-gray-500 gap-3">
                <p>Drag the sliders to adjust how much each factor influences the "Perfect Gift" calculation.</p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-rose-500 hover:text-rose-600 hover:bg-rose-50 h-7"
                    onClick={() => {
                      setTuningValues({ ...TUNING_DEFAULTS });
                      setTuningDirty(true);
                    }}
                  >
                    <RefreshCw size={12} className="mr-1" />
                    Reset Defaults
                  </Button>
                  <Button
                    size="sm"
                    disabled={!tuningDirty || tuningSaving}
                    onClick={handleApplyTuning}
                    className="h-7 bg-linear-to-r from-rose-500 to-orange-500 text-white"
                  >
                    {tuningSaving ? (
                      <Loader2 size={12} className="mr-1 animate-spin" />
                    ) : (
                      <Save size={12} className="mr-1" />
                    )}
                    Apply Tuning
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
        {activeTab === "settings" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            {envSettings ? (
              <div className="grid md:grid-cols-2 gap-8">
                {/* Backend Settings */}
                <div className="bg-white rounded-2xl p-6 shadow-md border border-rose-100 flex flex-col h-full">
                  <div className="flex items-start justify-between gap-3 mb-6">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-rose-100 rounded-lg text-rose-600">
                        <Database size={20} />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-gray-800">
                          Backend Environment
                        </h3>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Changes apply immediately after clicking save.
                        </p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleSaveSettingsSection("backend")}
                      disabled={!settingsDirty.backend || settingsSaving !== null}
                      className="h-8 bg-linear-to-r from-rose-500 to-orange-500 text-white"
                    >
                      {settingsSaving === "backend" ? (
                        <Loader2 size={12} className="mr-1 animate-spin" />
                      ) : (
                        <Save size={12} className="mr-1" />
                      )}
                      Apply Backend
                    </Button>
                  </div>
                  <div className="space-y-4 flex-1">
                    {Object.entries(backendDraft).map(([k, v]) => (
                      <div key={k} className="space-y-1.5">
                        <Label className="text-xs text-gray-400 font-mono">
                          {k}
                        </Label>
                        <div className="flex gap-2">
                          <Input
                            value={v}
                            className="font-mono text-sm bg-stone-50"
                            onChange={(e) =>
                              handleSettingChange("backend", k, e.target.value)
                            }
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Frontend Settings */}
                <div className="bg-white rounded-2xl p-6 shadow-md border border-rose-100 flex flex-col h-full">
                  <div className="flex items-start justify-between gap-3 mb-6">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-orange-100 rounded-lg text-orange-600">
                        <UploadCloud size={20} />
                      </div>
                      <h3 className="text-xl font-bold text-gray-800">
                        Frontend Environment
                      </h3>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleSaveSettingsSection("frontend")}
                      disabled={!settingsDirty.frontend || settingsSaving !== null}
                      className="h-8 bg-linear-to-r from-amber-500 to-orange-500 text-white"
                    >
                      {settingsSaving === "frontend" ? (
                        <Loader2 size={12} className="mr-1 animate-spin" />
                      ) : (
                        <Save size={12} className="mr-1" />
                      )}
                      Apply Frontend
                    </Button>
                  </div>
                  <div className="bg-orange-50/50 p-4 rounded-xl border border-orange-100 mb-6 flex items-start gap-3">
                    <AlertCircle className="text-orange-500 mt-0.5" size={18} />
                    <p className="text-xs text-orange-800 leading-relaxed">
                      Frontend variables are baked in at build time. Changing
                      these will update the <code className="bg-white px-1 font-bold">.env</code> file, but a container rebuild
                      is required for changes to take effect on the live site.
                    </p>
                  </div>
                  <div className="space-y-4 flex-1">
                    {Object.entries(frontendDraft).map(([k, v]) => (
                      <div key={k} className="space-y-1.5">
                        <Label className="text-xs text-gray-400 font-mono">
                          {k}
                        </Label>
                        <div className="flex gap-2">
                          <Input
                            value={v}
                            className="font-mono text-sm bg-stone-50"
                            onChange={(e) =>
                              handleSettingChange("frontend", k, e.target.value)
                            }
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-gray-400 gap-4">
                <Loader2 className="animate-spin" size={32} />
                <p>Loading environment configurations…</p>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
