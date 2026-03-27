import { motion } from "motion/react";
import {
  Gift,
  Sparkles,
  Heart,
  Star,
  Zap,
  Award,
  Users,
  ArrowRight,
  Mail,
  Phone,
  MapPin,
  Facebook,
  Twitter,
  Instagram,
  Linkedin,
  CheckCircle,
  Search,
  Wand2,
} from "lucide-react";
import { Button } from "./ui/button";
import { Navbar } from "./Navbar";
import { useEffect, useState } from "react";
import {
  getHomeRecommendations,
  getPublicReviews,
  type PublicReview,
} from "@/lib/api/users";
import {
  getRecommendations,
  type RecommendationWithGift,
} from "@/lib/api/recommendations";
import { ProfileModal } from "./ProfileModal";

interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
  onSignUp: () => void;
  onSelectGift?: (gift: RecommendationWithGift) => void;
  isLoggedIn?: boolean;
  userName?: string;
  onAdminClick?: () => void;
  isAdmin?: boolean;
  refreshKey?: number;
  onProfileUpdated?: () => void;
}

export function LandingPage({
  onGetStarted,
  onSignIn,
  onSignUp,
  onSelectGift,
  isLoggedIn,
  userName,
  onAdminClick,
  isAdmin,
  refreshKey,
  onProfileUpdated,
}: LandingPageProps) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [homeGifts, setHomeGifts] = useState<RecommendationWithGift[]>([]);
  const [homeLoading, setHomeLoading] = useState(false);
  const [publicReviews, setPublicReviews] = useState<PublicReview[]>([]);
  const [publicReviewsLoading, setPublicReviewsLoading] = useState(false);

  useEffect(() => {
    if (!isLoggedIn || isAdmin) return;
    let cancelled = false;
    setHomeLoading(true);
    (async () => {
      try {
        const personalized = await getHomeRecommendations();
        if (cancelled) return;
        if (Array.isArray(personalized) && personalized.length > 0) {
          setHomeGifts(personalized);
          return;
        }

        const fallback = await getRecommendations(
          { top_n: 8 },
          { timeoutMs: 30000, retry: { attempts: 1 } },
        );
        if (!cancelled) setHomeGifts(Array.isArray(fallback) ? fallback : []);
      } catch {
        if (cancelled) return;
        try {
          const fallback = await getRecommendations(
            { top_n: 8 },
            { timeoutMs: 30000, retry: { attempts: 1 } },
          );
          if (!cancelled) setHomeGifts(Array.isArray(fallback) ? fallback : []);
        } catch {
          if (!cancelled) setHomeGifts([]);
        }
      } finally {
        if (!cancelled) setHomeLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isLoggedIn, isAdmin, refreshKey]);

  useEffect(() => {
    setPublicReviewsLoading(true);
    getPublicReviews(6)
      .then((rows) => setPublicReviews(Array.isArray(rows) ? rows : []))
      .catch(() => setPublicReviews([]))
      .finally(() => setPublicReviewsLoading(false));
  }, []);

  const fallbackReviews: PublicReview[] = [
    {
      name: "Sarah J.",
      role: "Gift Enthusiast",
      avatar: "S",
      rating: 5,
      review:
        "Upahaar helped me find the perfect gift for my sister's birthday! The AI recommendations were spot-on.",
      reviewed_at: new Date().toISOString(),
    },
    {
      name: "Michael C.",
      role: "Busy Professional",
      avatar: "M",
      rating: 5,
      review:
        "As someone who struggles with gift ideas, this platform is a lifesaver.",
      reviewed_at: new Date().toISOString(),
    },
    {
      name: "Priya S.",
      role: "Mother of Two",
      avatar: "P",
      rating: 5,
      review:
        "I love how easy it is to create thoughtful gifts for family and friends.",
      reviewed_at: new Date().toISOString(),
    },
  ];
  const reviewCards =
    publicReviews.length > 0 ? publicReviews.slice(0, 6) : fallbackReviews;

  return (
    <div
      id="home"
      className="min-h-screen bg-gradient-to-br from-stone-50 via-rose-50 to-orange-50 relative overflow-hidden"
    >
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(25)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute"
            initial={{
              x:
                Math.random() *
                (typeof window !== "undefined" ? window.innerWidth : 1000),
              y:
                Math.random() *
                (typeof window !== "undefined" ? window.innerHeight : 1000),
              scale: 0,
              opacity: 0,
            }}
            animate={{
              y: [
                null,
                Math.random() *
                  (typeof window !== "undefined" ? window.innerHeight : 1000),
              ],
              scale: [0, 1, 0],
              opacity: [0, 0.7, 0],
              rotate: [0, 360],
            }}
            transition={{
              duration: 4 + Math.random() * 3,
              repeat: Infinity,
              delay: Math.random() * 3,
            }}
          >
            {i % 5 === 0 ? (
              <Sparkles className="text-amber-400" size={24} />
            ) : i % 5 === 1 ? (
              <Heart className="text-rose-400" size={24} />
            ) : i % 5 === 2 ? (
              <Star className="text-pink-400" size={24} />
            ) : i % 5 === 3 ? (
              <Gift className="text-orange-400" size={24} />
            ) : (
              <Zap className="text-red-400" size={24} />
            )}
          </motion.div>
        ))}
      </div>

      {/* Navbar */}
      <Navbar
        onSignIn={onSignIn}
        onSignUp={onSignUp}
        showAuthButtons={true}
        onLogoClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        onAdminClick={onAdminClick}
        onProfileClick={() => setProfileOpen(true)}
      />

      <ProfileModal
        isOpen={profileOpen}
        onClose={() => setProfileOpen(false)}
        onProfileUpdated={onProfileUpdated}
      />

      {/* Hero Section */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 pt-32 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-center"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="inline-flex items-center gap-2 bg-rose-100 px-6 py-3 rounded-full mb-6"
          >
            <Sparkles className="text-rose-600" size={20} />
            <span className="text-rose-700 font-medium">
              AI-Powered Gift Discovery
            </span>
          </motion.div>

          <motion.h1
            className="text-7xl md:text-8xl mb-6 leading-tight"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            Discover{" "}
            <motion.span
              className="bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent inline-block"
              animate={{
                backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
              }}
              transition={{ duration: 5, repeat: Infinity }}
              style={{ backgroundSize: "200% auto" }}
            >
              Perfect Gifts
            </motion.span>
            <br />
            With Heart ❤️
          </motion.h1>

          <motion.p
            className="text-2xl text-gray-600 mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            Let our AI create personalized gift recommendations with beautiful
            greeting cards, heartfelt letters, and stunning virtual packaging.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.8 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Button
              size="lg"
              onClick={onGetStarted}
              className="bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 text-xl px-14 py-8 rounded-2xl shadow-2xl hover:shadow-rose-500/50 transition-all transform hover:scale-105"
            >
              <Gift className="mr-3" size={28} />
              Start Your Journey
              <ArrowRight className="ml-3" size={24} />
            </Button>
            {isLoggedIn && (
              <div className="text-lg text-rose-600 font-medium">
                Welcome back{userName ? `, ${userName}` : ""}!
              </div>
            )}
          </motion.div>
        </motion.div>

        {isLoggedIn && !isAdmin && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.1 }}
            className="mt-16 bg-white/70 backdrop-blur-xl rounded-3xl p-8 shadow-xl border border-white/50"
          >
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-semibold text-rose-700">
                  Gifts you may like{userName ? `, ${userName}` : ""}
                </h3>
                <p className="text-gray-600">
                  Based on your profile and recent selections.
                </p>
              </div>
            </div>

            {homeLoading ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {[...Array(4)].map((_, index) => (
                  <div
                    key={`loading-card-${index}`}
                    className="bg-white/80 rounded-2xl border border-rose-100 shadow-sm overflow-hidden animate-pulse"
                  >
                    <div className="h-40 bg-gradient-to-r from-rose-100 via-pink-100 to-orange-100" />
                    <div className="p-4 space-y-3">
                      <div className="h-4 bg-rose-100 rounded-full w-3/4" />
                      <div className="h-3 bg-rose-100 rounded-full w-full" />
                      <div className="h-3 bg-rose-100 rounded-full w-2/3" />
                      <div className="h-5 bg-pink-200 rounded-full w-1/3" />
                      <div className="h-9 bg-gradient-to-r from-rose-200 to-orange-200 rounded-xl" />
                    </div>
                  </div>
                ))}
              </div>
            ) : homeGifts.length === 0 ? (
              <p className="text-gray-500">
                No personalized gifts yet. Interact with gifts or update your
                profile to improve suggestions.
              </p>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {homeGifts.map((gift) => (
                  <div
                    key={gift.gift_id}
                    className="bg-white rounded-2xl border border-rose-100 shadow-sm overflow-hidden"
                  >
                    {gift.image_url && (
                      <img
                        src={gift.image_url}
                        alt={gift.title}
                        className="w-full h-40 object-cover"
                      />
                    )}
                    <div className="p-4">
                      <h4 className="font-semibold text-gray-800 line-clamp-2">
                        {gift.title}
                      </h4>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {gift.description}
                      </p>
                      <p className="text-rose-600 font-semibold mt-2">
                        ${gift.price}
                      </p>
                      {onSelectGift && (
                        <Button
                          size="sm"
                          onClick={() => onSelectGift(gift)}
                          className="mt-3 w-full bg-gradient-to-r from-rose-600 to-orange-500"
                        >
                          Choose this gift
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* Feature Cards */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1 }}
          className="grid md:grid-cols-4 gap-6 mt-24"
        >
          {[
            {
              icon: <Sparkles className="text-amber-500" size={36} />,
              title: "Smart AI",
              description:
                "Advanced algorithms analyze preferences for perfect matches",
              color: "from-amber-400 to-orange-400",
            },
            {
              icon: <Heart className="text-rose-500" size={36} />,
              title: "Personal Touch",
              description:
                "Custom greeting cards and heartfelt letter templates",
              color: "from-rose-400 to-pink-400",
            },
            {
              icon: <Gift className="text-pink-500" size={36} />,
              title: "Virtual Magic",
              description: "Watch gifts wrapped with stunning 3D animations",
              color: "from-pink-400 to-rose-400",
            },
            {
              icon: <Award className="text-orange-500" size={36} />,
              title: "Premium Quality",
              description: "Curated selection of high-quality gift options",
              color: "from-orange-400 to-red-400",
            },
          ].map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 1.2 + index * 0.15 }}
              whileHover={{ scale: 1.05, y: -10 }}
              className="bg-white/70 backdrop-blur-xl rounded-3xl p-8 shadow-xl hover:shadow-2xl transition-all border border-white/50"
            >
              <motion.div
                animate={{
                  rotate: [0, 10, -10, 0],
                  scale: [1, 1.1, 1],
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  delay: index * 0.5,
                }}
                className="mb-5"
              >
                {feature.icon}
              </motion.div>
              <h3 className="text-xl mb-3 font-semibold">{feature.title}</h3>
              <p className="text-gray-600 leading-relaxed">
                {feature.description}
              </p>
              <div
                className={`mt-4 h-1 bg-gradient-to-r ${feature.color} rounded-full`}
              />
            </motion.div>
          ))}
        </motion.div>

        {/* Stats Section - REMOVED */}
      </div>

      {/* About Us Section */}
      <section
        id="about"
        className="relative z-10 bg-white/60 backdrop-blur-lg py-20 px-4"
      >
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-bold bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent mb-6">
              About Upahaar
            </h2>
            <p className="text-xl text-gray-700 leading-relaxed max-w-4xl mx-auto">
              Upahaar (उपहार) means "gift" in Nepali. We believe that every gift
              should be special, thoughtful, and memorable. Our AI-powered
              platform helps you discover the perfect gift for your loved ones
              by understanding their personality, interests, and your
              relationship. We combine technology with heart to make gift-giving
              a joyful experience.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: <Heart size={48} />,
                title: "Our Mission",
                text: "To make every gift-giving moment special by providing personalized recommendations that come from the heart.",
              },
              {
                icon: <Sparkles size={48} />,
                title: "Our Vision",
                text: "To become the most trusted platform for thoughtful gifting, bringing joy to millions worldwide.",
              },
              {
                icon: <Users size={48} />,
                title: "Our Values",
                text: "Authenticity, thoughtfulness, and innovation guide everything we do to serve you better.",
              },
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.2 }}
                className="bg-gradient-to-br from-rose-50 to-orange-50 rounded-2xl p-8 text-center"
              >
                <div className="text-rose-600 flex justify-center mb-4">
                  {item.icon}
                </div>
                <h3 className="text-2xl font-semibold mb-3">{item.title}</h3>
                <p className="text-gray-700 leading-relaxed">{item.text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="relative z-10 py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-bold bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent mb-6">
              How It Works
            </h2>
            <p className="text-xl text-gray-700">
              Simple steps to find the perfect gift
            </p>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              {
                step: "1",
                icon: <Search size={40} />,
                title: "Tell Us About Them",
                text: "Share details about the recipient, occasion, and preferences",
              },
              {
                step: "2",
                icon: <Wand2 size={40} />,
                title: "AI Recommends",
                text: "Our smart algorithm suggests perfect gifts tailored to them",
              },
              {
                step: "3",
                icon: <Heart size={40} />,
                title: "Personalize",
                text: "Add greeting cards and heartfelt letters to make it special",
              },
              {
                step: "4",
                icon: <Gift size={40} />,
                title: "Share Joy",
                text: "Download, share, or save your beautifully packaged gift",
              },
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.15 }}
                className="relative"
              >
                <div className="bg-white/70 backdrop-blur-lg rounded-2xl p-8 text-center shadow-lg">
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 w-12 h-12 bg-gradient-to-br from-rose-600 to-orange-600 rounded-full flex items-center justify-center text-white font-bold text-xl shadow-lg">
                    {item.step}
                  </div>
                  <div className="text-rose-600 flex justify-center mb-4 mt-4">
                    {item.icon}
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
                  <p className="text-gray-700 leading-relaxed">{item.text}</p>
                </div>
                {index < 3 && (
                  <div className="hidden md:block absolute top-1/2 -right-4 text-rose-300">
                    <ArrowRight size={32} />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Reviews Section */}
      <section className="relative z-10 py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-bold bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent mb-6">
              What Our Users Say
            </h2>
            <p className="text-xl text-gray-600">
              Real experiences from real people
            </p>
          </motion.div>

          {publicReviewsLoading && (
            <div className="text-center text-gray-500 mb-6">
              Loading recent reviews...
            </div>
          )}

          <div className="grid md:grid-cols-3 gap-8">
            {reviewCards.map((review, index) => (
              <motion.div
                key={`${review.name}-${index}`}
                initial={{ opacity: 0, y: 40, rotateY: -10 }}
                whileInView={{ opacity: 1, y: 0, rotateY: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.2, type: "spring" }}
                whileHover={{ scale: 1.05, y: -10 }}
                className="bg-white/80 backdrop-blur-lg rounded-3xl p-8 shadow-xl hover:shadow-2xl transition-all"
              >
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-rose-200 to-orange-200 flex items-center justify-center text-2xl font-bold text-rose-700">
                    {review.avatar}
                  </div>
                  <div>
                    <h3 className="font-semibold text-xl text-gray-800">
                      {review.name}
                    </h3>
                    <p className="text-sm text-gray-600">{review.role}</p>
                  </div>
                </div>

                <div className="flex gap-1 mb-4">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Star
                      key={i}
                      className={
                        i <= review.rating
                          ? "text-amber-400 fill-amber-400"
                          : "text-gray-300"
                      }
                      size={20}
                    />
                  ))}
                </div>

                <p className="text-gray-700 leading-relaxed italic">
                  "{review.review}"
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQs Section */}
      <section
        id="faqs"
        className="relative z-10 bg-white/60 backdrop-blur-lg py-20 px-4"
      >
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-bold bg-gradient-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent mb-6">
              Frequently Asked Questions
            </h2>
          </motion.div>

          <div className="space-y-6">
            {[
              {
                q: "How does the AI recommendation work?",
                a: "Our AI analyzes the information you provide about the recipient including their age, interests, hobbies, and your relationship to suggest the most suitable gifts from our curated collection.",
              },
              {
                q: "Is the service free?",
                a: "Yes! Upahaar is completely free to use. You can create unlimited gift recommendations, cards, and letters without any cost.",
              },
              {
                q: "Can I customize the greeting cards and letters?",
                a: "Absolutely! We provide beautiful templates that you can fully customize with your own messages, names, and personal touches.",
              },
              {
                q: "Do you ship physical gifts?",
                a: "Currently, Upahaar provides gift recommendations and virtual packaging. We show you the best options and where to purchase them.",
              },
              {
                q: "Can I save my gift recommendations?",
                a: "Yes! You can download your complete gift package including the card, letter, and recommendations as a PDF to share or keep.",
              },
            ].map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-gradient-to-br from-rose-50 to-orange-50 rounded-2xl p-6 shadow-lg"
              >
                <div className="flex items-start gap-4">
                  <CheckCircle
                    className="text-rose-600 mt-1 flex-shrink-0"
                    size={24}
                  />
                  <div>
                    <h3 className="text-xl font-semibold mb-2">{faq.q}</h3>
                    <p className="text-gray-700 leading-relaxed">{faq.a}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 2.5 }}
        className="relative z-10 bg-gradient-to-br from-rose-900 via-pink-900 to-orange-900 text-white mt-24"
      >
        <div className="max-w-full mx-auto px-4 py-16">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            {/* Brand */}
            <div className="md:col-span-2">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-rose-400 to-orange-400 rounded-2xl flex items-center justify-center">
                  <Gift className="text-white" size={28} />
                </div>
                <span className="text-3xl font-bold">Upahaar</span>
              </div>
              <p className="text-rose-200 leading-relaxed mb-6">
                Making every gift special with AI-powered recommendations,
                personalized cards, and beautiful presentation. Your one-stop
                solution for thoughtful gifting.
              </p>
              <div className="flex gap-4">
                {[
                  {
                    icon: <Facebook size={20} />,
                    name: "Facebook",
                    url: "https://facebook.com",
                  },
                  {
                    icon: <Twitter size={20} />,
                    name: "Twitter",
                    url: "https://twitter.com",
                  },
                  {
                    icon: <Instagram size={20} />,
                    name: "Instagram",
                    url: "https://instagram.com",
                  },
                  {
                    icon: <Linkedin size={20} />,
                    name: "LinkedIn",
                    url: "https://linkedin.com",
                  },
                ].map((social) => (
                  <motion.a
                    key={social.name}
                    href={social.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    whileHover={{ scale: 1.2, rotate: 10 }}
                    whileTap={{ scale: 0.9 }}
                    className="w-10 h-10 bg-rose-700 rounded-full flex items-center justify-center hover:bg-rose-600 transition-colors"
                    aria-label={social.name}
                  >
                    {social.icon}
                  </motion.a>
                ))}
              </div>
            </div>

            {/* Quick Links */}
            <div>
              <h4 className="text-xl font-semibold mb-4">Quick Links</h4>
              <ul className="space-y-3">
                {[
                  { name: "About Us", id: "about" },
                  { name: "How It Works", id: "how-it-works" },
                  { name: "FAQs", id: "faqs" },
                ].map((link) => (
                  <li key={link.name}>
                    <button
                      onClick={() => {
                        const element = document.getElementById(link.id);
                        if (element) {
                          element.scrollIntoView({ behavior: "smooth" });
                        }
                      }}
                      className="text-rose-200 hover:text-white transition-colors flex items-center gap-2"
                    >
                      <ArrowRight size={16} />
                      {link.name}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h4 className="text-xl font-semibold mb-4">Contact</h4>
              <ul className="space-y-3">
                <li className="flex items-center gap-3 text-rose-200">
                  <Mail size={18} />
                  <span>hello@upahaar.com</span>
                </li>
                <li className="flex items-center gap-3 text-rose-200">
                  <Phone size={18} />
                  <span>+1 (555) 123-4567</span>
                </li>
                <li className="flex items-center gap-3 text-rose-200">
                  <MapPin size={18} />
                  <span>San Francisco, CA</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="border-t border-rose-700 pt-8 flex flex-col md:flex-row justify-between items-center">
            <p className="text-rose-300">
              © 2026 Upahaar. All rights reserved.
            </p>
            <div className="flex gap-6 mt-4 md:mt-0">
              <a
                href="#"
                className="text-rose-300 hover:text-white transition-colors"
              >
                Privacy Policy
              </a>
              <a
                href="#"
                className="text-rose-300 hover:text-white transition-colors"
              >
                Terms of Service
              </a>
              <a
                href="#"
                className="text-rose-300 hover:text-white transition-colors"
              >
                Cookie Policy
              </a>
            </div>
          </div>
        </div>
      </motion.footer>
    </div>
  );
}
