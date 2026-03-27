import { motion } from "motion/react";
import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { Slider } from "./ui/slider";
import { MultiSelect } from "./ui/multi-select";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Heart,
  Star,
  Loader2,
} from "lucide-react";
import { Navbar } from "./Navbar";
import { FloatingEmojiBackground } from "./FloatingEmojiBackground";
import { ProfileModal } from "./ProfileModal";
import {
  listHobbies,
  listAgeGroups,
  listRelationships,
  listOccasions,
  listGenders,
  listAgeRules,
} from "@/lib/api/taxonomy";

interface FormData {
  age: string;
  relation: string;
  occasion: string;
  hobbies: string[];
  gender: string;
  budgetMax: number;
}

// Output type sent to parent (hobbies joined as string)
export interface FormOutput {
  age: string;
  relation: string;
  occasion: string;
  hobbies: string;
  gender: string;
  budgetMax: number;
}

interface RecommendationFormProps {
  onComplete: (data: FormOutput) => void;
  onBack: () => void;
}

export function RecommendationForm({
  onComplete,
  onBack,
}: RecommendationFormProps) {
  const PRICE_MIN = 0;
  const PRICE_MAX = 7500;
  const PRICE_STEP = 50;

  const [formData, setFormData] = useState<FormData>({
    age: "",
    relation: "",
    occasion: "",
    hobbies: [],
    gender: "",
    budgetMax: 500,
  });

  const [currentField, setCurrentField] = useState<string | null>(null);

  const [isLoadingTaxonomy, setIsLoadingTaxonomy] = useState(true);
  const [hobbiesList, setHobbiesList] = useState<string[]>([]);
  const [ageGroupsList, setAgeGroupsList] = useState<string[]>([]);
  const [relationsList, setRelationsList] = useState<string[]>([]);
  const [occasionsList, setOccasionsList] = useState<string[]>([]);
  const [gendersList, setGendersList] = useState<string[]>([]);
  const [ageRulesMap, setAgeRulesMap] = useState<Record<string, string[]>>({});

  useEffect(() => {
    async function fetchTaxonomy() {
      try {
        const [
          hobs,
          ages,
          rels,
          occs,
          gens,
          rules,
        ] = await Promise.all([
          listHobbies(),
          listAgeGroups(),
          listRelationships(),
          listOccasions(),
          listGenders(),
          listAgeRules(),
        ]);
        setHobbiesList(hobs);
        setAgeGroupsList(ages);
        setRelationsList(rels);
        setOccasionsList(occs);
        setGendersList(gens);
        setAgeRulesMap(rules);
      } catch (err) {
        console.error("Failed to load taxonomy data", err);
      } finally {
        setIsLoadingTaxonomy(false);
      }
    }
    fetchTaxonomy();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onComplete({ ...formData, hobbies: formData.hobbies.join(", ") });
  };

  const fieldVariants = {
    focused: { scale: 1.02, boxShadow: "0 0 0 3px rgba(244, 63, 94, 0.2)" },
    unfocused: { scale: 1, boxShadow: "0 0 0 0px rgba(244, 63, 94, 0)" },
  };

  const disabledRelations = formData.age ? ageRulesMap[formData.age] || [] : [];

  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-rose-50 to-orange-50 relative overflow-x-hidden overflow-y-auto">
      <FloatingEmojiBackground />
      <Navbar
        showAuthButtons={false}
        showNavLinks={false}
        onLogoClick={onBack}
        onProfileClick={() => setProfileOpen(true)}
      />
      <ProfileModal isOpen={profileOpen} onClose={() => setProfileOpen(false)} />

      <div className="pt-32 pb-12 px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="bg-white/80 backdrop-blur-2xl rounded-3xl p-8 max-w-4xl mx-auto shadow-2xl border-4 border-rose-100 relative"
        >
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="relative z-10"
          >
            <div className="flex items-center justify-center gap-3 mb-3">
              <motion.div
                animate={{ rotate: [0, 360] }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              >
                <Sparkles className="text-rose-600" size={28} />
              </motion.div>
              <h2 className="text-4xl bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
                Gift Discovery
              </h2>
            </div>
            <p className="text-gray-600 text-center mb-6">
              Tell us about the special person in your life
            </p>
          </motion.div>

          {isLoadingTaxonomy ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="animate-spin text-rose-500 mb-4" size={48} />
              <p className="text-rose-600 font-medium animate-pulse">
                Loading perfect matching options...
              </p>
            </div>
          ) : (

          <form onSubmit={handleSubmit} className="space-y-4 relative z-10">
            <div className="grid md:grid-cols-2 gap-4">
              {/* Age Field */}
              <motion.div
                variants={fieldVariants}
                animate={currentField === "age" ? "focused" : "unfocused"}
                transition={{ type: "spring", stiffness: 300 }}
                className="relative bg-gradient-to-br from-rose-50 to-pink-50 rounded-xl p-4 border-2 border-rose-200"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Heart className="text-rose-600" size={18} />
                  <Label
                    htmlFor="age"
                    className="text-rose-800 font-semibold text-sm"
                  >
                    Age
                  </Label>
                </div>
                <Select
                  value={formData.age}
                  onValueChange={(value) => {
                    setFormData({ ...formData, age: value });
                    // If the current relation is disabled by the new age, clear it
                    if (ageRulesMap[value]?.includes(formData.relation)) {
                      setFormData((prev) => ({ ...prev, relation: "" }));
                    }
                  }}
                  required
                >
                  <SelectTrigger
                    className="border-0 bg-white/70 py-4"
                    onFocus={() => setCurrentField("age")}
                    onBlur={() => setCurrentField(null)}
                  >
                    <SelectValue placeholder="Select age group" />
                  </SelectTrigger>
                  <SelectContent>
                    {ageGroupsList.map((ageOption) => (
                      <SelectItem key={ageOption} value={ageOption}>
                        {ageOption}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </motion.div>

              {/* Gender Field */}
              <motion.div
                variants={fieldVariants}
                animate={currentField === "gender" ? "focused" : "unfocused"}
                transition={{ type: "spring", stiffness: 300 }}
                className="relative bg-gradient-to-br from-pink-50 to-orange-50 rounded-xl p-4 border-2 border-pink-200"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Heart className="text-pink-600" size={18} />
                  <Label
                    htmlFor="gender"
                    className="text-pink-800 font-semibold text-sm"
                  >
                    Gender
                  </Label>
                </div>
                <Select
                  value={formData.gender}
                  onValueChange={(value) =>
                    setFormData({ ...formData, gender: value })
                  }
                  required
                >
                  <SelectTrigger
                    className="border-0 bg-white/70 py-4"
                    onFocus={() => setCurrentField("gender")}
                    onBlur={() => setCurrentField(null)}
                  >
                    <SelectValue placeholder="Select gender" />
                  </SelectTrigger>
                  <SelectContent>
                    {gendersList.map((g) => (
                      <SelectItem key={g} value={g}>
                        {g}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </motion.div>
            </div>

            {/* Relation Field */}
            <motion.div
              variants={fieldVariants}
              animate={currentField === "relation" ? "focused" : "unfocused"}
              className="relative bg-gradient-to-br from-orange-50 to-rose-50 rounded-xl p-4 border-2 border-orange-200"
            >
              <div className="flex items-center gap-2 mb-1">
                <Heart className="text-orange-600" size={18} />
                <Label
                  htmlFor="relation"
                  className="text-orange-800 font-semibold text-sm"
                >
                  Your Relationship
                </Label>
              </div>
              <Select
                value={formData.relation}
                onValueChange={(value) =>
                  setFormData({ ...formData, relation: value })
                }
                required
              >
                <SelectTrigger
                  className="border-0 bg-white/70 py-4"
                  onFocus={() => setCurrentField("relation")}
                  onBlur={() => setCurrentField(null)}
                >
                  <SelectValue placeholder="Select relationship" />
                </SelectTrigger>
                <SelectContent>
                  {relationsList.map((rel) => {
                    const isDisabled = disabledRelations.includes(rel);
                    return (
                      <SelectItem
                        key={rel}
                        value={rel}
                        disabled={isDisabled}
                        title={isDisabled ? `Not typical for ${formData.age} age group` : ""}
                        className={isDisabled ? "line-through opacity-50" : ""}
                      >
                        {rel}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </motion.div>

            {/* Occasion Field */}
            <motion.div
              variants={fieldVariants}
              animate={currentField === "occasion" ? "focused" : "unfocused"}
              className="relative bg-gradient-to-br from-amber-50 to-yellow-50 rounded-xl p-4 border-2 border-amber-200"
            >
              <div className="flex items-center gap-2 mb-1">
                <Star className="text-amber-600" size={18} />
                <Label
                  htmlFor="occasion"
                  className="text-amber-800 font-semibold text-sm"
                >
                  Special Occasion
                </Label>
              </div>
              <Select
                value={formData.occasion}
                onValueChange={(value) =>
                  setFormData({ ...formData, occasion: value })
                }
                required
              >
                <SelectTrigger
                  className="border-0 bg-white/70 py-4"
                  onFocus={() => setCurrentField("occasion")}
                  onBlur={() => setCurrentField(null)}
                >
                  <SelectValue placeholder="Select occasion" />
                </SelectTrigger>
                <SelectContent>
                  {occasionsList.map((occ) => (
                    <SelectItem key={occ} value={occ}>
                      {occ}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </motion.div>

            {/* Budget Field */}
            <motion.div
              variants={fieldVariants}
              animate={currentField === "budget" ? "focused" : "unfocused"}
              className="relative bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border-2 border-green-200"
            >
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="text-green-600" size={18} />
                <Label
                  htmlFor="budget"
                  className="text-green-800 font-semibold text-sm"
                >
                  Max Budget
                </Label>
              </div>
              <div
                className="border-0 bg-white/70 rounded-md px-3 py-4"
                onFocus={() => setCurrentField("budget")}
                onBlur={() => setCurrentField(null)}
              >
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="text-gray-500">Price range</span>
                  <span className="font-semibold text-green-700">
                    ${PRICE_MIN} to ${formData.budgetMax}
                  </span>
                </div>
                <Slider
                  value={[formData.budgetMax]}
                  min={PRICE_MIN}
                  max={PRICE_MAX}
                  step={PRICE_STEP}
                  onValueChange={([val]) =>
                    setFormData((prev) => ({ ...prev, budgetMax: val }))
                  }
                />
                <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
                  <span>${PRICE_MIN}</span>
                  <span>${PRICE_MAX}</span>
                </div>
              </div>
            </motion.div>

            {/* Hobbies Field */}
            <motion.div
              variants={fieldVariants}
              animate={currentField === "hobbies" ? "focused" : "unfocused"}
              className="relative bg-gradient-to-br from-purple-50 to-indigo-50 rounded-xl p-4 border-2 border-purple-200"
            >
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="text-purple-600" size={18} />
                <Label
                  htmlFor="hobbies"
                  className="text-purple-800 font-semibold text-sm"
                >
                  Hobbies &amp; Interests
                  <span className="ml-1 text-purple-400 text-xs font-normal">(pick multiple)</span>
                </Label>
              </div>
              <MultiSelect
                options={hobbiesList}
                selected={formData.hobbies}
                onChange={(vals) => setFormData({ ...formData, hobbies: vals })}
                placeholder="Select hobbies or interests..."
                className="border-0 bg-white/70"
              />
            </motion.div>

            <div className="flex gap-4 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onBack}
                className="flex-1 py-5 border-2 border-rose-300 hover:bg-rose-50"
              >
                <ArrowLeft className="mr-2" size={18} />
                Back
              </Button>
              <Button
                type="submit"
                className="flex-1 py-5 bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 shadow-lg hover:shadow-rose-500/50 transform hover:scale-105 transition-all"
              >
                Continue
                <ArrowRight className="ml-2" size={18} />
              </Button>
            </div>
          </form>
          )}
        </motion.div>
      </div>
    </div>
  );
}
