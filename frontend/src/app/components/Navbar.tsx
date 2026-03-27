import { motion } from "motion/react";
import { Gift, LogOut, LayoutDashboard } from "lucide-react";
import { Button } from "./ui/button";
import { useAuth } from "../../lib/store/auth";

interface NavbarProps {
  onSignIn?: () => void;
  onSignUp?: () => void;
  showAuthButtons?: boolean;
  showNavLinks?: boolean;
  onLogoClick: () => void;
  onAdminClick?: () => void;
  onProfileClick?: () => void;
}

export function Navbar({
  onSignIn,
  onSignUp,
  showAuthButtons = true,
  showNavLinks = true,
  onLogoClick,
  onAdminClick,
  onProfileClick,
}: NavbarProps) {
  const { user, isLoggedIn, isAdmin, logout } = useAuth();

  const handleAdminClick = () => {
    if (onAdminClick) {
      onAdminClick();
      return;
    }
    window.dispatchEvent(new Event("nav:admin"));
  };

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      onLogoClick();
    }
  };

  return (
    <motion.nav
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, type: "spring" }}
      className="sticky top-0 left-0 right-0 z-50 bg-white/40 backdrop-blur-lg border-b border-rose-100 shadow-lg"
    >
      <div className="max-w-full mx-auto px-4 py-3 flex justify-between items-center">
        <button
          onClick={onLogoClick}
          className="flex items-center gap-3 hover:opacity-80 transition-opacity"
        >
          <motion.div
            animate={{
              rotate: [0, 15, -15, 0],
              scale: [1, 1.1, 1],
            }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="relative"
          >
            <div className="w-12 h-12 bg-gradient-to-br from-rose-500 via-pink-500 to-orange-500 rounded-2xl flex items-center justify-center shadow-lg">
              <Gift className="text-white" size={28} />
            </div>
            <motion.div
              animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="absolute inset-0 bg-gradient-to-br from-rose-500 to-orange-500 rounded-2xl"
            />
          </motion.div>
          <div>
            <span className="text-3xl font-bold bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
              Upahaar
            </span>
            <p className="text-xs text-gray-600">
              Thoughtful Gifting Made Easy
            </p>
          </div>
        </button>

        <div className="flex items-center gap-6">
          {showNavLinks && (
            <>
              <button
                onClick={() => scrollToSection("about")}
                className="text-gray-700 hover:text-rose-600 transition-colors font-medium"
              >
                About Us
              </button>
              <button
                onClick={() => scrollToSection("how-it-works")}
                className="text-gray-700 hover:text-rose-600 transition-colors font-medium"
              >
                How It Works
              </button>
              <button
                onClick={() => scrollToSection("faqs")}
                className="text-gray-700 hover:text-rose-600 transition-colors font-medium"
              >
                FAQs
              </button>
            </>
          )}

          {isLoggedIn ? (
            <div className="flex items-center gap-3">
              {isAdmin && (
                <Button
                  variant="ghost"
                  onClick={handleAdminClick}
                  className="hover:bg-rose-100 hover:text-rose-700 transition-all flex items-center gap-2"
                >
                  <LayoutDashboard size={16} />
                  Admin
                </Button>
              )}
              {onProfileClick ? (
                <button
                  onClick={onProfileClick}
                  className="text-gray-700 font-medium hover:text-rose-600 transition-colors"
                >
                  👋 {user?.name}
                </button>
              ) : (
                <span className="text-gray-700 font-medium">
                  👋 {user?.name}
                </span>
              )}
              <Button
                variant="ghost"
                onClick={logout}
                className="hover:bg-red-100 hover:text-red-700 transition-all flex items-center gap-2"
              >
                <LogOut size={16} />
                Sign Out
              </Button>
            </div>
          ) : showAuthButtons ? (
            <>
              <Button
                variant="ghost"
                onClick={onSignIn}
                className="hover:bg-rose-100 hover:text-rose-700 transition-all"
              >
                Sign In
              </Button>
              <Button
                onClick={onSignUp}
                className="bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 hover:shadow-lg hover:shadow-rose-500/50 transition-all"
              >
                Get Started
              </Button>
            </>
          ) : null}
        </div>
      </div>
    </motion.nav>
  );
}
