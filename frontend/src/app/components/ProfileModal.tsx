import { motion, AnimatePresence } from "motion/react";
import { X, Save, KeyRound, Eye, EyeOff } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { useEffect, useState } from "react";
import {
  changePassword,
  getProfile,
  updateProfile,
  UserProfile,
} from "@/lib/api/users";
import { listHobbies } from "@/lib/api/taxonomy";
import { MultiSelect } from "./ui/multi-select";

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProfileUpdated?: () => void;
}

const emptyProfile: UserProfile = {
  id: 0,
  user_id: 0,
  age: "",
  gender: "",
  hobbies: "",
  relationship: "",
  occasion: "",
  budget_min: null,
  budget_max: null,
  updated_at: "",
};

export function ProfileModal({ isOpen, onClose, onProfileUpdated }: ProfileModalProps) {
  const [profile, setProfile] = useState<UserProfile>(emptyProfile);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [hobbiesList, setHobbiesList] = useState<string[]>([]);
  const [selectedHobbies, setSelectedHobbies] = useState<string[]>([]);

  useEffect(() => {
    listHobbies().then(setHobbiesList).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    setSuccess(null);
    setLoading(true);
    getProfile()
      .then((res) => {
        if (res) {
          setProfile(res);
          setSelectedHobbies(
            res.hobbies ? res.hobbies.split(",").map((h) => h.trim()).filter(Boolean) : []
          );
        } else {
          setProfile(emptyProfile);
          setSelectedHobbies([]);
        }
      })
      .catch((err: any) => setError(err.message ?? "Failed to load profile"))
      .finally(() => setLoading(false));
  }, [isOpen]);

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const updated = await updateProfile({
        age: profile.age || null,
        gender: profile.gender || null,
        hobbies: selectedHobbies.join(", ") || null,
        relationship: profile.relationship || null,
        occasion: profile.occasion || null,
        budget_min: profile.budget_min ?? null,
        budget_max: profile.budget_max ?? null,
      });
      setProfile(updated);
      setSuccess("Profile updated.");
      onProfileUpdated?.();
    } catch (err: any) {
      setError(err.message ?? "Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  const handlePassword = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await changePassword({
        old_password: oldPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess("Password updated.");
    } catch (err: any) {
      setError(err.message ?? "Failed to update password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-md z-50"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 60 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 60 }}
            transition={{ type: "spring", damping: 24, stiffness: 260 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-white rounded-3xl p-8 max-w-2xl w-full shadow-2xl border border-rose-100">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-semibold text-rose-700">
                  Your Profile
                </h3>
                <button
                  onClick={onClose}
                  className="p-2 rounded-full bg-rose-100 hover:bg-rose-200"
                >
                  <X size={20} className="text-rose-700" />
                </button>
              </div>

              {error && <p className="text-red-600 mb-4 text-sm">{error}</p>}
              {success && (
                <p className="text-emerald-600 mb-4 text-sm">{success}</p>
              )}

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label>Age</Label>
                  <Input
                    value={profile.age ?? ""}
                    onChange={(e) =>
                      setProfile({ ...profile, age: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Gender</Label>
                  <Input
                    value={profile.gender ?? ""}
                    onChange={(e) =>
                      setProfile({ ...profile, gender: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Hobbies & Interests</Label>
                  <MultiSelect
                    options={hobbiesList}
                    selected={selectedHobbies}
                    onChange={setSelectedHobbies}
                    placeholder="Select hobbies..."
                  />
                </div>
                <div>
                  <Label>Relationship</Label>
                  <Input
                    value={profile.relationship ?? ""}
                    onChange={(e) =>
                      setProfile({ ...profile, relationship: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Occasion</Label>
                  <Input
                    value={profile.occasion ?? ""}
                    onChange={(e) =>
                      setProfile({ ...profile, occasion: e.target.value })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Budget Min</Label>
                    <Input
                      type="number"
                      value={profile.budget_min ?? ""}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          budget_min: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                    />
                  </div>
                  <div>
                    <Label>Budget Max</Label>
                    <Input
                      type="number"
                      value={profile.budget_max ?? ""}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          budget_max: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <Button
                  onClick={handleSave}
                  disabled={loading}
                  className="bg-gradient-to-r from-rose-600 to-orange-500"
                >
                  <Save className="mr-2" size={18} />
                  Save Profile
                </Button>
              </div>

              <div className="mt-8 border-t border-rose-100 pt-6">
                <h4 className="text-lg font-semibold text-rose-700 mb-4">
                  Change Password
                </h4>
                <div className="grid md:grid-cols-3 gap-4">
                  <div>
                    <Label>Old Password</Label>
                    <div className="relative">
                      <Input
                        type={showOld ? "text" : "password"}
                        value={oldPassword}
                        onChange={(e) => setOldPassword(e.target.value)}
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowOld((s) => !s)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-rose-600 hover:text-rose-800"
                        aria-label={
                          showOld ? "Hide old password" : "Show old password"
                        }
                      >
                        {showOld ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <Label>New Password</Label>
                    <div className="relative">
                      <Input
                        type={showNew ? "text" : "password"}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNew((s) => !s)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-rose-600 hover:text-rose-800"
                        aria-label={
                          showNew ? "Hide new password" : "Show new password"
                        }
                      >
                        {showNew ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <Label>Confirm Password</Label>
                    <div className="relative">
                      <Input
                        type={showConfirm ? "text" : "password"}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirm((s) => !s)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-rose-600 hover:text-rose-800"
                        aria-label={
                          showConfirm
                            ? "Hide confirm password"
                            : "Show confirm password"
                        }
                      >
                        {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>
                </div>
                <div className="flex justify-end mt-4">
                  <Button
                    variant="outline"
                    onClick={handlePassword}
                    disabled={loading}
                  >
                    <KeyRound className="mr-2" size={18} />
                    Update Password
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
