import { motion, AnimatePresence } from "motion/react";
import { X, Mail, Lock, User, AlertCircle, Eye, EyeOff } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { useState } from "react";
import { login, register, googleLogin } from "../../lib/api/auth";
import { useAuth } from "../../lib/store/auth";
import { GoogleLogin, CredentialResponse } from "@react-oauth/google";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: "signin" | "signup";
  onSuccess: (name: string, isNewUser: boolean) => void;
  onSwitchMode?: (mode: "signin" | "signup") => void;
}

export function AuthModal({
  isOpen,
  onClose,
  mode,
  onSuccess,
  onSwitchMode,
}: AuthModalProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setUser } = useAuth();
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const googleEnabled = Boolean(googleClientId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "signup") {
        const user = await register({ name, email, password });
        // Auto-login after register
        const loginResp = await login({ email, password });
        setUser(loginResp.user);
        onSuccess(loginResp.user.name, true);
      } else {
        const loginResp = await login({ email, password });
        setUser(loginResp.user);
        onSuccess(loginResp.user.name, false);
      }
    } catch (err: any) {
      setError(err.message ?? "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (
    credentialResponse: CredentialResponse,
  ) => {
    if (!credentialResponse.credential) {
      setError("Google login failed. Please try again.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const loginResp = await googleLogin({
        token: credentialResponse.credential,
      });
      setUser(loginResp.user);
      onSuccess(loginResp.user.name, false);
    } catch (err: any) {
      setError(err.message ?? "Google login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-md z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 100 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 100 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-gradient-to-br from-white via-rose-50 to-orange-50 rounded-3xl p-8 max-w-md w-full shadow-2xl relative border-4 border-rose-100">
              <motion.button
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="absolute top-4 right-4 p-2 rounded-full bg-rose-100 hover:bg-rose-200 transition-colors"
              >
                <X size={20} className="text-rose-700" />
              </motion.button>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                {/* Logo */}
                <motion.div
                  className="flex justify-center mb-4"
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <div className="w-16 h-16 bg-gradient-to-br from-rose-500 via-pink-500 to-orange-500 rounded-2xl flex items-center justify-center shadow-lg">
                    <span className="text-3xl">🎁</span>
                  </div>
                </motion.div>

                <h2 className="text-3xl text-center mb-2 bg-gradient-to-r from-rose-600 to-orange-600 bg-clip-text text-transparent">
                  {mode === "signin" ? "Welcome Back!" : "Join Upahaar"}
                </h2>
                <p className="text-gray-600 text-center mb-6">
                  {mode === "signin"
                    ? "Continue your gifting journey"
                    : "Start discovering perfect gifts today"}
                </p>

                {/* Google Sign In */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="mb-4"
                >
                  {googleEnabled ? (
                    <div className="w-full flex justify-center">
                      <GoogleLogin
                        onSuccess={handleGoogleSuccess}
                        onError={() =>
                          setError("Google login failed. Please try again.")
                        }
                        useOneTap
                      />
                    </div>
                  ) : (
                    <Button
                      type="button"
                      variant="outline"
                      disabled
                      title="Google login requires OAuth setup"
                      className="w-full py-5 border-2 border-rose-200 opacity-60 cursor-not-allowed"
                    >
                      <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
                        <path
                          fill="#4285F4"
                          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                        />
                        <path
                          fill="#34A853"
                          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        />
                        <path
                          fill="#FBBC05"
                          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                        />
                        <path
                          fill="#EA4335"
                          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                        />
                      </svg>
                      Continue with Google (setup required)
                    </Button>
                  )}
                </motion.div>

                <div className="relative mb-4">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-300"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-4 bg-gradient-to-r from-rose-50 to-orange-50 text-gray-500">
                      Or continue with email
                    </span>
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  {mode === "signup" && (
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 }}
                    >
                      <Label htmlFor="name" className="text-rose-800">
                        Full Name
                      </Label>
                      <div className="relative mt-1">
                        <User
                          className="absolute left-3 top-1/2 -translate-y-1/2 text-rose-600"
                          size={18}
                        />
                        <Input
                          id="name"
                          type="text"
                          placeholder="John Doe"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          required
                          className="pl-10 py-5 border-2 border-rose-200 focus:border-rose-500 bg-white/50 rounded-xl"
                        />
                      </div>
                    </motion.div>
                  )}

                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: mode === "signup" ? 0.4 : 0.3 }}
                  >
                    <Label htmlFor="email" className="text-rose-800">
                      Email Address
                    </Label>
                    <div className="relative mt-1">
                      <Mail
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-rose-600"
                        size={18}
                      />
                      <Input
                        id="email"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="pl-10 py-5 border-2 border-rose-200 focus:border-rose-500 bg-white/50 rounded-xl"
                      />
                    </div>
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: mode === "signup" ? 0.5 : 0.4 }}
                  >
                    <Label htmlFor="password" className="text-rose-800">
                      Password
                    </Label>
                    <div className="relative mt-1">
                      <Lock
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-rose-600"
                        size={18}
                      />
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="pl-10 pr-10 py-5 border-2 border-rose-200 focus:border-rose-500 bg-white/50 rounded-xl"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((s) => !s)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-rose-600 hover:text-rose-800"
                        aria-label={
                          showPassword ? "Hide password" : "Show password"
                        }
                      >
                        {showPassword ? (
                          <EyeOff size={18} />
                        ) : (
                          <Eye size={18} />
                        )}
                      </button>
                    </div>

                    {/* Forgot password: keep it out of the main flow for now. */}
                    {mode === "signin" && (
                      <div className="mt-2 text-right">
                        <button
                          type="button"
                          className="text-xs text-rose-700 hover:underline opacity-70"
                          onClick={() =>
                            setError(
                              "Password reset isn’t enabled yet. You can change it from Profile after login.",
                            )
                          }
                        >
                          Forgot password?
                        </button>
                      </div>
                    )}
                  </motion.div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm"
                    >
                      <AlertCircle size={16} className="shrink-0" />
                      {error}
                    </motion.div>
                  )}

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: mode === "signup" ? 0.6 : 0.5 }}
                  >
                    <Button
                      type="submit"
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 py-6 text-lg font-semibold shadow-lg hover:shadow-rose-500/50 transition-all transform hover:scale-105 disabled:opacity-70 disabled:scale-100"
                    >
                      {loading
                        ? mode === "signin"
                          ? "Signing in…"
                          : "Creating account…"
                        : mode === "signin"
                          ? "Sign In"
                          : "Create Account"}
                    </Button>
                  </motion.div>
                </form>

                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.7 }}
                  className="text-center text-gray-600 mt-4"
                >
                  {mode === "signin"
                    ? "Don't have an account? "
                    : "Already have an account? "}
                  <button
                    onClick={() =>
                      onSwitchMode?.(mode === "signin" ? "signup" : "signin")
                    }
                    className="text-rose-600 hover:text-rose-700 font-semibold"
                  >
                    {mode === "signin" ? "Sign Up" : "Sign In"}
                  </button>
                </motion.p>
              </motion.div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
