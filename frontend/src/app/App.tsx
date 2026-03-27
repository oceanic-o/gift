import { Suspense, lazy, useEffect, useState } from "react";
import { LoadingScreen } from "./components/LoadingScreen";
import { PackagingAnimation } from "./components/PackagingAnimation";
const LandingPage = lazy(() =>
  import("./components/LandingPage").then((m) => ({ default: m.LandingPage })),
);
const AuthModal = lazy(() =>
  import("./components/AuthModal").then((m) => ({ default: m.AuthModal })),
);
const RecommendationForm = lazy(() =>
  import("./components/RecommendationForm").then((m) => ({
    default: m.RecommendationForm,
  })),
);
const GreetingCardSelector = lazy(() =>
  import("./components/GreetingCardSelector").then((m) => ({
    default: m.GreetingCardSelector,
  })),
);
const LetterTemplate = lazy(() =>
  import("./components/LetterTemplate").then((m) => ({
    default: m.LetterTemplate,
  })),
);
const GiftRecommendation = lazy(() =>
  import("./components/GiftRecommendation").then((m) => ({
    default: m.GiftRecommendation,
  })),
);
const FinalResult = lazy(() =>
  import("./components/FinalResult").then((m) => ({ default: m.FinalResult })),
);
const OnboardingPreferences = lazy(() =>
  import("./components/OnboardingPreferences").then((m) => ({
    default: m.OnboardingPreferences,
  })),
);
const AdminDashboard = lazy(() =>
  import("./components/AdminDashboard").then((m) => ({
    default: m.AdminDashboard,
  })),
);
import { useAuth } from "@/lib/store/auth";
import type { FormOutput } from "./components/RecommendationForm";
import { recordInteraction } from "@/lib/api/recommendations";

type Step =
  | "landing"
  | "onboarding"
  | "form"
  | "card"
  | "letter"
  | "gift"
  | "packaging"
  | "result"
  | "admin";


export default function App() {
  const { isLoggedIn, user } = useAuth();
  const [currentStep, setCurrentStep] = useState<Step>("landing");
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [pendingAdminRedirect, setPendingAdminRedirect] = useState(false);

  const [formData, setFormData] = useState<FormOutput | null>(null);
  const [selectedCard, setSelectedCard] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [senderName, setSenderName] = useState("");
  const [personalMessage, setPersonalMessage] = useState<string | null>(null);
  const [selectedGift, setSelectedGift] = useState<any>(null);
  const [homeRefreshKey, setHomeRefreshKey] = useState(0);

  const handleGetStarted = () => {
    if (isLoggedIn) {
      setCurrentStep("form");
    } else {
      setAuthMode("signup");
      setAuthModalOpen(true);
    }
  };

  const handleSignIn = () => {
    setAuthMode("signin");
    setAuthModalOpen(true);
  };

  const handleSignUp = () => {
    setAuthMode("signup");
    setAuthModalOpen(true);
  };

  const handleAuthSuccess = (_name: string, isNewUser: boolean) => {
    setAuthModalOpen(false);
    if (isNewUser) {
      setCurrentStep("onboarding");
    } else {
      setCurrentStep("landing");
      setPendingAdminRedirect(true);
    }
  };

  useEffect(() => {
    if (pendingAdminRedirect && user?.role === "admin") {
      setCurrentStep("admin");
    }
    if (pendingAdminRedirect) {
      setPendingAdminRedirect(false);
    }
  }, [pendingAdminRedirect, user?.role]);

  useEffect(() => {
    const handler = () => setCurrentStep("admin");
    window.addEventListener("nav:admin", handler);
    return () => window.removeEventListener("nav:admin", handler);
  }, []);

  const handleQuickGiftSelect = (gift: any) => {
    setSelectedGift(gift);
    setSelectedCard("");
    setRecipientName("");
    setSenderName("");
    setPersonalMessage(null);
    setCurrentStep("packaging");
    // Record click interaction and refresh recommendations
    if (gift?.gift_id) {
      recordInteraction(gift.gift_id, "click").catch(() => {});
    }
    setHomeRefreshKey((k) => k + 1);
  };

  const handleSwitchMode = (mode: "signin" | "signup") => {
    setAuthMode(mode);
  };

  const handleFormComplete = (data: FormOutput) => {
    setFormData(data);
    setCurrentStep("card");
  };

  const handleCardComplete = (
    cardId: string,
    recipient: string,
    sender: string,
  ) => {
    setSelectedCard(cardId);
    setRecipientName(recipient);
    setSenderName(sender);
    setCurrentStep("letter");
  };

  const handleLetterComplete = (
    message: string | null,
    _skipLetter: boolean,
  ) => {
    setPersonalMessage(message);
    setCurrentStep("gift");
  };

  const handleGiftComplete = (gift: any) => {
    setSelectedGift(gift);
    setCurrentStep("packaging");
  };

  const handlePackagingComplete = () => {
    setCurrentStep("result");
  };

  const handleStartOver = () => {
    setCurrentStep("landing");
    setFormData(null);
    setSelectedCard("");
    setRecipientName("");
    setSenderName("");
    setPersonalMessage(null);
    setSelectedGift(null);
  };

  return (
    <div className="min-h-screen">
      {currentStep === "landing" && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Loading your experience"
              detail="Getting everything ready"
            />
          }
        >
          <LandingPage
            onGetStarted={handleGetStarted}
            onSignIn={handleSignIn}
            onSignUp={handleSignUp}
            onSelectGift={handleQuickGiftSelect}
            isLoggedIn={isLoggedIn}
            userName={user?.name ?? ""}
            onAdminClick={() => setCurrentStep("admin")}
            isAdmin={user?.role === "admin"}
            refreshKey={homeRefreshKey}
            onProfileUpdated={() => setHomeRefreshKey((k) => k + 1)}
          />
          <AuthModal
            isOpen={authModalOpen}
            onClose={() => setAuthModalOpen(false)}
            mode={authMode}
            onSuccess={handleAuthSuccess}
            onSwitchMode={handleSwitchMode}
          />
        </Suspense>
      )}

      {currentStep === "form" && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Loading the gift finder"
              detail="Preparing your personalized form"
            />
          }
        >
          <RecommendationForm
            onComplete={handleFormComplete}
            onBack={() => setCurrentStep("landing")}
          />
        </Suspense>
      )}

      {currentStep === "onboarding" && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Setting up your profile"
              detail="Tuning recommendations for you"
            />
          }
        >
          <OnboardingPreferences
            onComplete={() => setCurrentStep("form")}
            onSkip={() => setCurrentStep("landing")}
          />
        </Suspense>
      )}

      {currentStep === "card" && formData && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Loading greeting cards"
              detail="Curating heartfelt designs"
            />
          }
        >
          <GreetingCardSelector
            onComplete={handleCardComplete}
            onBack={() => setCurrentStep("form")}
            occasion={formData.occasion}
          />
        </Suspense>
      )}

      {currentStep === "letter" && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Loading letter templates"
              detail="Drafting the perfect message"
            />
          }
        >
          <LetterTemplate
            onComplete={handleLetterComplete}
            onBack={() => setCurrentStep("card")}
            recipientName={recipientName}
            senderName={senderName}
            onLogoClick={handleStartOver}
          />
        </Suspense>
      )}

      {currentStep === "gift" && formData && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Loading gift ideas"
              detail="Gathering thoughtful picks"
            />
          }
        >
          <GiftRecommendation
            onComplete={handleGiftComplete}
            onBack={() => setCurrentStep("letter")}
            formData={formData}
          />
        </Suspense>
      )}

      {currentStep === "packaging" && selectedGift && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Preparing the packaging"
              detail="Wrapping your gift with care"
            />
          }
        >
          <PackagingAnimation
            gift={selectedGift}
            card={
              selectedCard
                ? { cardId: selectedCard, recipientName, senderName }
                : undefined
            }
            letter={
              personalMessage ? { letterData: personalMessage } : undefined
            }
            onComplete={handlePackagingComplete}
            onBack={() => setCurrentStep("gift")}
          />
        </Suspense>
      )}

      {currentStep === "result" && selectedGift && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Finalizing your surprise"
              detail="Almost ready to reveal"
            />
          }
        >
          <FinalResult
            gift={selectedGift}
            cardId={selectedCard}
            message={personalMessage}
            recipientName={recipientName}
            senderName={senderName}
            onStartOver={handleStartOver}
            onLogoClick={handleStartOver}
            onSignIn={handleSignIn}
            onSignUp={handleSignUp}
            showAuthButtons={!isLoggedIn}
            onAdminClick={() => setCurrentStep("admin")}
          />
        </Suspense>
      )}

      {currentStep === "admin" && (
        <Suspense
          fallback={
            <LoadingScreen
              message="Loading admin dashboard"
              detail="Fetching the latest insights"
            />
          }
        >
          <AdminDashboard
            onBack={() => setCurrentStep("landing")}
            onLogoClick={handleStartOver}
          />
        </Suspense>
      )}
    </div>
  );
}
