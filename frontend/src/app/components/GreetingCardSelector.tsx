import { motion } from "motion/react";
import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  ArrowRight,
  ArrowLeft,
  Check,
  Sparkles,
  Heart,
  Gift as GiftIcon,
} from "lucide-react";
import { Navbar } from "./Navbar";
import { FloatingEmojiBackground } from "./FloatingEmojiBackground";

interface GreetingCardSelectorProps {
  onComplete: (
    cardId: string,
    recipientName: string,
    senderName: string,
  ) => void;
  onBack: () => void;
  occasion: string;
}

const cardTemplates = [
  {
    id: "elegant-floral",
    name: "Elegant Blooms",
    gradient: "from-pink-300 via-rose-300 to-red-300",
    pattern: "🌸",
    style: "Romantic & Delicate",
  },
  {
    id: "modern-geometric",
    name: "Modern Lines",
    gradient: "from-slate-300 via-gray-300 to-zinc-300",
    pattern: "◆",
    style: "Clean & Contemporary",
  },
  {
    id: "festive-celebration",
    name: "Party Vibes",
    gradient: "from-yellow-300 via-orange-300 to-red-300",
    pattern: "🎉",
    style: "Fun & Energetic",
  },
  {
    id: "nature-zen",
    name: "Natural Harmony",
    gradient: "from-green-300 via-emerald-300 to-teal-300",
    pattern: "🌿",
    style: "Calm & Peaceful",
  },
  {
    id: "romantic-hearts",
    name: "Love & Joy",
    gradient: "from-rose-300 via-pink-300 to-fuchsia-300",
    pattern: "💕",
    style: "Warm & Affectionate",
  },
  {
    id: "luxury-gold",
    name: "Golden Elegance",
    gradient: "from-amber-300 via-yellow-300 to-orange-300",
    pattern: "⭐",
    style: "Premium & Sophisticated",
  },
  {
    id: "ocean-breeze",
    name: "Ocean Dreams",
    gradient: "from-cyan-300 via-blue-300 to-indigo-300",
    pattern: "🌊",
    style: "Fresh & Serene",
  },
  {
    id: "sunset-glow",
    name: "Sunset Magic",
    gradient: "from-purple-300 via-pink-300 to-orange-300",
    pattern: "🌅",
    style: "Dreamy & Warm",
  },
];

export function GreetingCardSelector({
  onComplete,
  onBack,
  occasion,
}: GreetingCardSelectorProps) {
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [recipientName, setRecipientName] = useState("");
  const [senderName, setSenderName] = useState("");

  const handleContinue = () => {
    if (selectedCard && recipientName && senderName) {
      onComplete(selectedCard, recipientName, senderName);
    }
  };

  const selectedCardData = cardTemplates.find((c) => c.id === selectedCard);

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-rose-50 to-orange-50 relative overflow-hidden">
      <FloatingEmojiBackground />
      <Navbar
        showAuthButtons={false}
        showNavLinks={false}
        onLogoClick={onBack}
      />

      <div className="pt-32 pb-12 px-4 relative z-10 flex items-center justify-center min-h-screen">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="bg-white/80 backdrop-blur-2xl rounded-3xl p-12 max-w-7xl w-full shadow-2xl border-4 border-rose-100"
        >
          <motion.div
            initial={{ opacity: 0, y: -30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-center mb-10"
          >
            <div className="flex items-center justify-center gap-3 mb-4">
              <motion.div
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <GiftIcon className="text-rose-600" size={40} />
              </motion.div>
              <h2 className="text-5xl bg-linear-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
                Choose a Greeting Card
              </h2>
            </div>
            <p className="text-gray-600 text-xl">
              Select the perfect card design for{" "}
              <span className="text-rose-600 font-semibold">{occasion}</span>
            </p>
          </motion.div>

          {/* Name Inputs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="grid md:grid-cols-2 gap-6 mb-10"
          >
            <div className="bg-linear-to-br from-rose-50 to-pink-50 rounded-2xl p-6 border-2 border-rose-200">
              <Label
                htmlFor="recipientName"
                className="text-rose-800 font-semibold text-lg mb-2 flex items-center gap-2"
              >
                <Heart size={20} className="text-rose-600" />
                Recipient's Name
              </Label>
              <Input
                id="recipientName"
                type="text"
                placeholder="Who is this card for?"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                required
                className="mt-2 py-6 text-lg border-2 border-rose-200 focus:border-rose-500"
              />
            </div>

            <div className="bg-linear-to-br from-pink-50 to-orange-50 rounded-2xl p-6 border-2 border-pink-200">
              <Label
                htmlFor="senderName"
                className="text-pink-800 font-semibold text-lg mb-2 flex items-center gap-2"
              >
                <Sparkles size={20} className="text-pink-600" />
                Your Name
              </Label>
              <Input
                id="senderName"
                type="text"
                placeholder="From who?"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                required
                className="mt-2 py-6 text-lg border-2 border-pink-200 focus:border-pink-500"
              />
            </div>
          </motion.div>

          {/* Card Templates */}
          <div className="grid md:grid-cols-4 gap-5 mb-10">
            {cardTemplates.map((card, index) => (
              <motion.div
                key={card.id}
                initial={{ opacity: 0, y: 40, rotateY: -20 }}
                animate={{ opacity: 1, y: 0, rotateY: 0 }}
                transition={{
                  delay: 0.4 + index * 0.08,
                  type: "spring",
                }}
                whileHover={{ scale: 1.08, y: -8, rotateY: 5 }}
                onClick={() => setSelectedCard(card.id)}
                className={`cursor-pointer rounded-2xl p-6 relative transition-all shadow-lg ${
                  selectedCard === card.id
                    ? "ring-4 ring-rose-500 shadow-2xl"
                    : ""
                }`}
                style={{ perspective: "1000px" }}
              >
                <div
                  className={`absolute inset-0 bg-linear-to-br ${card.gradient} rounded-2xl opacity-60`}
                />

                <div className="relative z-10">
                  <motion.div
                    className="text-6xl mb-4 text-center"
                    animate={
                      selectedCard === card.id ? { scale: [1, 1.2, 1] } : {}
                    }
                    transition={{ duration: 0.5 }}
                  >
                    {card.pattern}
                  </motion.div>
                  <h3 className="text-center font-semibold text-lg mb-1">
                    {card.name}
                  </h3>
                  <p className="text-center text-sm text-gray-700">
                    {card.style}
                  </p>

                  {selectedCard === card.id && (
                    <motion.div
                      initial={{ scale: 0, rotate: -180 }}
                      animate={{ scale: 1, rotate: 0 }}
                      className="absolute top-3 right-3 bg-rose-600 text-white rounded-full p-2 shadow-lg"
                    >
                      <Check size={20} />
                    </motion.div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Preview */}
          {selectedCard && recipientName && (
            <motion.div
              initial={{ opacity: 0, height: 0, scale: 0.9 }}
              animate={{ opacity: 1, height: "auto", scale: 1 }}
              transition={{ type: "spring", damping: 20 }}
              className="bg-linear-to-r from-rose-100 via-pink-100 to-orange-100 rounded-3xl p-8 mb-8 border-2 border-rose-200"
            >
              <div className="flex items-center gap-2 mb-6">
                <Sparkles className="text-rose-600" size={24} />
                <h4 className="text-2xl font-semibold text-rose-800">
                  Card Preview
                </h4>
              </div>
              <motion.div
                className={`bg-linear-to-br ${selectedCardData?.gradient} rounded-2xl p-12 text-center shadow-2xl relative overflow-hidden`}
                whileHover={{ scale: 1.02 }}
              >
                {/* Decorative elements */}
                <div className="absolute top-4 left-4 text-4xl opacity-30">
                  {selectedCardData?.pattern}
                </div>
                <div className="absolute bottom-4 right-4 text-4xl opacity-30">
                  {selectedCardData?.pattern}
                </div>

                <motion.p
                  className="text-5xl mb-6"
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  {selectedCardData?.pattern}
                </motion.p>
                <h3 className="text-3xl font-bold mb-4">
                  Dear {recipientName},
                </h3>
                <p className="text-xl text-gray-800 italic leading-relaxed max-w-2xl mx-auto">
                  "Wishing you a wonderful {occasion}! May this special day
                  bring you joy, happiness, and beautiful memories that last a
                  lifetime."
                </p>
                {senderName && (
                  <p className="text-xl text-gray-700 mt-8 flex items-center justify-center gap-2">
                    With love,{" "}
                    <span className="font-semibold">{senderName}</span> ❤️
                  </p>
                )}
              </motion.div>
            </motion.div>
          )}

          {/* Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="flex gap-4"
          >
            <Button
              type="button"
              variant="outline"
              onClick={onBack}
              className="flex-1 py-7 text-lg border-2 border-rose-300 hover:bg-rose-50"
            >
              <ArrowLeft className="mr-2" size={20} />
              Back
            </Button>
            <Button
              onClick={handleContinue}
              disabled={!selectedCard || !recipientName || !senderName}
              className="flex-1 py-7 text-lg bg-linear-to-r from-rose-600 via-pink-600 to-orange-600 disabled:opacity-50 shadow-lg hover:shadow-rose-500/50 transform hover:scale-105 transition-all"
            >
              Continue to Letter
              <ArrowRight className="ml-2" size={20} />
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
