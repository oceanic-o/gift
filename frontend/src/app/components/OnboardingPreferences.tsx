import { useMemo, useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { savePreferences, UserPreferencesUpdate } from "@/lib/api/users";

const CATEGORY_OPTIONS = [
  "Electronics",
  "Fashion",
  "Home & Kitchen",
  "Books",
  "Sports & Outdoors",
  "Beauty & Personal Care",
  "Toys & Games",
  "Handmade",
  "Jewelry",
  "Gadgets",
];

const OCCASION_OPTIONS = [
  "Birthday",
  "Anniversary",
  "Christmas",
  "Valentine's Day",
  "Graduation",
  "Mother's Day",
  "Father's Day",
  "Wedding",
];

const AGE_OPTIONS = ["Kids", "Teens", "18-25", "26-40", "41-60", "60+"];

const TAG_SUGGESTIONS = [
  "tech",
  "gadget",
  "travel",
  "outdoors",
  "cozy",
  "wellness",
  "gourmet",
  "fashion",
  "DIY",
  "artisan",
  "for him",
  "for her",
];

interface OnboardingPreferencesProps {
  onComplete: () => void;
  onSkip?: () => void;
}

export function OnboardingPreferences({
  onComplete,
  onSkip,
}: OnboardingPreferencesProps) {
  const [favoriteCategories, setFavoriteCategories] = useState<string[]>([]);
  const [occasions, setOccasions] = useState<string[]>([]);
  const [giftingForAges, setGiftingForAges] = useState<string[]>([]);
  const [budgetMin, setBudgetMin] = useState<number | null>(10);
  const [budgetMax, setBudgetMax] = useState<number | null>(500);
  const [interests, setInterests] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredSuggestions = useMemo(() => {
    const q = tagInput.trim().toLowerCase();
    if (!q) return TAG_SUGGESTIONS.filter((t) => !interests.includes(t));
    return TAG_SUGGESTIONS.filter(
      (t) => t.toLowerCase().includes(q) && !interests.includes(t),
    );
  }, [tagInput, interests]);

  const toggleValue = (
    list: string[],
    value: string,
    setter: (next: string[]) => void,
  ) => {
    setter(
      list.includes(value) ? list.filter((v) => v !== value) : [...list, value],
    );
  };

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (!trimmed || interests.includes(trimmed)) return;
    setInterests((prev) => [...prev, trimmed]);
    setTagInput("");
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const payload: UserPreferencesUpdate = {
        favorite_categories: favoriteCategories,
        occasions,
        gifting_for_ages: giftingForAges,
        budget_min: budgetMin,
        budget_max: budgetMax,
        interests,
      };
      await savePreferences(payload);
      onComplete();
    } catch (err: any) {
      setError(err.message ?? "Failed to save preferences");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-rose-50 to-orange-50 flex items-center justify-center px-4 py-12">
      <div className="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-rose-100 w-full max-w-3xl p-8 space-y-8">
        <div>
          <h2 className="text-3xl font-semibold text-rose-700">
            Complete your preferences
          </h2>
          <p className="text-gray-500 text-sm mt-2">
            Help us personalize your gift recommendations.
          </p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <section className="space-y-3">
          <Label className="text-rose-700">Favorite Categories</Label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {CATEGORY_OPTIONS.map((c) => (
              <Button
                key={c}
                variant={favoriteCategories.includes(c) ? "default" : "outline"}
                onClick={() =>
                  toggleValue(favoriteCategories, c, setFavoriteCategories)
                }
              >
                {c}
              </Button>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <Label className="text-rose-700">Primary Occasions</Label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {OCCASION_OPTIONS.map((o) => (
              <Button
                key={o}
                variant={occasions.includes(o) ? "default" : "outline"}
                onClick={() => toggleValue(occasions, o, setOccasions)}
              >
                {o}
              </Button>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <Label className="text-rose-700">Gifting For (Age Groups)</Label>
          <div className="flex flex-wrap gap-2">
            {AGE_OPTIONS.map((a) => (
              <Button
                key={a}
                variant={giftingForAges.includes(a) ? "default" : "outline"}
                onClick={() =>
                  toggleValue(giftingForAges, a, setGiftingForAges)
                }
              >
                {a}
              </Button>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <Label className="text-rose-700">
            Typical Price Range ($10 - $500)
          </Label>
          <div className="grid grid-cols-2 gap-3">
            <Input
              type="number"
              min={10}
              max={500}
              value={budgetMin ?? ""}
              onChange={(e) =>
                setBudgetMin(e.target.value ? Number(e.target.value) : null)
              }
              placeholder="Min"
            />
            <Input
              type="number"
              min={10}
              max={500}
              value={budgetMax ?? ""}
              onChange={(e) =>
                setBudgetMax(e.target.value ? Number(e.target.value) : null)
              }
              placeholder="Max"
            />
          </div>
        </section>

        <section className="space-y-3">
          <Label className="text-rose-700">Interests / Tags</Label>
          <div className="flex gap-2">
            <Input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addTag(tagInput)}
              placeholder="Add a tag (press Enter)"
            />
            <Button variant="outline" onClick={() => addTag(tagInput)}>
              Add
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {interests.map((t) => (
              <Button
                key={t}
                variant="secondary"
                onClick={() => toggleValue(interests, t, setInterests)}
              >
                {t}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {filteredSuggestions.map((s) => (
              <Button key={s} variant="ghost" onClick={() => addTag(s)}>
                {s}
              </Button>
            ))}
          </div>
        </section>

        <div className="flex items-center justify-end gap-3">
          {onSkip && (
            <Button variant="ghost" onClick={onSkip}>
              Skip for now
            </Button>
          )}
          <Button onClick={save} disabled={saving}>
            Save Preferences
          </Button>
        </div>
      </div>
    </div>
  );
}
