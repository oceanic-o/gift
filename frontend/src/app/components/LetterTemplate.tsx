import { motion } from "motion/react";
import { useState } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ArrowRight, ArrowLeft, FileText, Sparkles, X } from "lucide-react";
import { Navbar } from "./Navbar";
import { FloatingEmojiBackground } from "./FloatingEmojiBackground";

interface LetterTemplateProps {
  onComplete: (message: string | null, skipLetter: boolean) => void;
  onBack: () => void;
  recipientName: string;
  senderName: string;
  onLogoClick: () => void;
  onSignIn?: () => void;
  onSignUp?: () => void;
  showAuthButtons?: boolean;
}

const templates = [
  {
    id: "heartfelt",
    name: "Heartfelt & Warm",
    emoji: "💝",
    template: (recipient: string, sender: string) =>
      `Dear ${recipient},

On this special day, I wanted to take a moment to express just how much you mean to me. Your presence in my life has brought countless moments of joy, laughter, and warmth that I treasure deeply.

Every memory we've shared, every conversation we've had, and every smile you've given me has made my life infinitely richer. You have a unique way of making the world brighter just by being in it.

This gift is a small token of my appreciation and love for everything you are and everything you do. I hope it brings as much joy to you as you bring to everyone around you.

May this occasion be filled with happiness, surrounded by the love of those who care about you most.

With all my heart and warmest wishes,
${sender} ❤️`,
  },
  {
    id: "cheerful",
    name: "Cheerful & Fun",
    emoji: "🎉",
    template: (recipient: string, sender: string) =>
      `Hey ${recipient}! 🎉

Happy, happy day to you! I hope you're ready for an absolutely amazing celebration because you deserve nothing less!

You know what I love most about you? Everything! Your energy, your smile, your laugh - they're all contagious in the best way possible. You have this incredible ability to turn ordinary moments into extraordinary memories.

This gift is just a little something to show you how awesome you are. Seriously, you're one of a kind, and I'm so grateful to have you in my life!

So go ahead - celebrate big, laugh loud, and make today absolutely unforgettable!

Cheers to you!
${sender} 🎊✨`,
  },
  {
    id: "grateful",
    name: "Grateful & Thoughtful",
    emoji: "🙏",
    template: (recipient: string, sender: string) =>
      `Dear ${recipient},

I wanted to take this opportunity to express my sincere gratitude for your presence in my life. Your kindness, generosity, and unwavering support have meant more to me than words can adequately express.

In a world that often moves too quickly, you've shown me the importance of genuine connection and compassion. The way you care for others and the positive impact you have on everyone around you is truly inspiring.

This gift comes with my deepest appreciation for all that you do and all that you are. Thank you for being such a remarkable person and for enriching my life in countless ways.

May you always know how valued and appreciated you are.

With heartfelt gratitude,
${sender} 🌟`,
  },
  {
    id: "inspirational",
    name: "Inspirational & Uplifting",
    emoji: "✨",
    template: (recipient: string, sender: string) =>
      `Dear ${recipient},

Today is a celebration of you - your journey, your growth, and the incredible person you've become. I want you to know how much I admire your strength, your determination, and your beautiful spirit.

Life has a way of presenting challenges, but watching you face them with grace and courage has been truly inspiring. You remind me that anything is possible when we believe in ourselves and stay true to who we are.

This gift is a symbol of my belief in you and all that you're capable of achieving. Continue to shine your light brightly, because the world needs more people like you.

Here's to your continued success, happiness, and all the wonderful adventures that await you!

With admiration and support,
${sender} 🌈`,
  },
];

export function LetterTemplate({
  onComplete,
  onBack,
  recipientName,
  senderName,
  onLogoClick,
  onSignIn,
  onSignUp,
  showAuthButtons = true,
}: LetterTemplateProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<string>(
    templates[0].id,
  );
  const [customMessage, setCustomMessage] = useState<string>(
    templates[0].template(recipientName, senderName),
  );
  const [skipLetter, setSkipLetter] = useState(false);

  const handleTemplateSelect = (templateId: string) => {
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setSelectedTemplate(templateId);
      setCustomMessage(template.template(recipientName, senderName));
    }
  };

  const handleContinue = () => {
    if (skipLetter) {
      onComplete(null, true);
    } else {
      onComplete(customMessage, false);
    }
  };

  const handleSkip = () => {
    setSkipLetter(true);
    onComplete(null, true);
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-stone-50 via-rose-50 to-orange-50 flex flex-col relative overflow-hidden">
      <FloatingEmojiBackground />
      <Navbar
        onLogoClick={onLogoClick}
        onSignIn={onSignIn}
        onSignUp={onSignUp}
        showAuthButtons={showAuthButtons}
        showNavLinks={false}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="flex-1 flex items-center justify-center p-8 relative z-10"
      >
        <div className="bg-white/80 backdrop-blur-2xl rounded-3xl p-12 max-w-6xl w-full shadow-2xl border-4 border-rose-100">
          <motion.div
            initial={{ opacity: 0, y: -30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-center mb-10"
          >
            <div className="flex items-center justify-center gap-3 mb-4">
              <motion.div
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <FileText className="text-teal-600" size={40} />
              </motion.div>
              <h2 className="text-5xl bg-linear-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
                Compose a Personal Letter
              </h2>
            </div>
            <p className="text-gray-600 text-xl">
              Choose a template or write your own heartfelt message
            </p>
          </motion.div>

          {/* Skip Option */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-8 text-center"
          >
            <Button
              variant="ghost"
              onClick={handleSkip}
              className="text-gray-600 hover:text-rose-600 hover:bg-rose-50"
            >
              <X size={18} className="mr-2" />
              Skip Letter (Optional)
            </Button>
          </motion.div>

          {!skipLetter && (
            <>
              {/* Template Selector */}
              <div className="grid md:grid-cols-4 gap-4 mb-8">
                {templates.map((template, index) => (
                  <motion.button
                    key={template.id}
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 + index * 0.1, type: "spring" }}
                    whileHover={{ scale: 1.05, y: -5 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleTemplateSelect(template.id)}
                    className={`p-6 rounded-2xl transition-all shadow-lg ${
                      selectedTemplate === template.id
                        ? "bg-linear-to-br from-rose-500 via-pink-500 to-orange-500 text-white shadow-2xl ring-4 ring-rose-300"
                        : "bg-white/70 hover:bg-white"
                    }`}
                  >
                    <motion.div
                      animate={
                        selectedTemplate === template.id
                          ? { rotate: [0, 10, -10, 0] }
                          : {}
                      }
                      transition={{ duration: 0.5 }}
                      className="text-5xl mb-3"
                    >
                      {template.emoji}
                    </motion.div>
                    <div className="font-semibold text-lg">{template.name}</div>
                  </motion.button>
                ))}
              </div>

              {/* Letter Editor */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
                className="mb-8"
              >
                <div className="relative">
                  {/* Paper texture background */}
                  <div className="absolute inset-0 bg-linear-to-br from-amber-50 via-yellow-50 to-orange-50 rounded-3xl opacity-80" />

                  {/* Lined paper effect */}
                  <div
                    className="absolute inset-0 opacity-10"
                    style={{
                      backgroundImage:
                        "repeating-linear-gradient(transparent, transparent 30px, #10b981 30px, #10b981 31px)",
                      marginTop: "60px",
                    }}
                  />

                  {/* Letter content */}
                  <div className="relative p-8">
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <Sparkles className="text-emerald-600" size={24} />
                        <h4 className="text-2xl font-semibold text-emerald-800">
                          Your Letter
                        </h4>
                      </div>
                      <div className="text-sm text-gray-600">
                        {customMessage.length} characters
                      </div>
                    </div>

                    <Textarea
                      value={customMessage}
                      onChange={(e) => setCustomMessage(e.target.value)}
                      className="min-h-[500px] bg-transparent border-0 text-lg leading-relaxed font-serif resize-none focus:ring-0"
                      placeholder="Write your heartfelt message here..."
                      style={{
                        backgroundImage:
                          "repeating-linear-gradient(transparent, transparent 30px, rgba(16, 185, 129, 0.1) 30px, rgba(16, 185, 129, 0.1) 31px)",
                        lineHeight: "31px",
                        paddingTop: "5px",
                      }}
                    />
                  </div>
                </div>
              </motion.div>

              {/* Preview */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 1 }}
                className="bg-linear-to-r from-rose-100 via-pink-100 to-orange-100 rounded-2xl p-6 mb-8 border-2 border-rose-200"
              >
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="text-emerald-600" size={20} />
                  <h5 className="font-semibold text-emerald-800">Preview</h5>
                </div>
                <div className="bg-white rounded-xl p-8 max-h-60 overflow-y-auto">
                  <pre className="whitespace-pre-wrap font-serif text-gray-700 leading-relaxed">
                    {customMessage}
                  </pre>
                </div>
              </motion.div>
            </>
          )}

          {/* Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2 }}
            className="flex gap-4"
          >
            <Button
              type="button"
              variant="outline"
              onClick={onBack}
              className="flex-1 py-7 text-lg border-2 border-emerald-300 hover:bg-emerald-50"
            >
              <ArrowLeft className="mr-2" size={20} />
              Back
            </Button>
            <Button
              onClick={handleContinue}
              disabled={!skipLetter && !customMessage.trim()}
              className="flex-1 py-7 text-lg bg-linear-to-r from-rose-600 via-pink-600 to-orange-600 disabled:opacity-50 shadow-lg hover:shadow-rose-500/50 transform hover:scale-105 transition-all"
            >
              Continue to Gift Selection
              <ArrowRight className="ml-2" size={20} />
            </Button>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
