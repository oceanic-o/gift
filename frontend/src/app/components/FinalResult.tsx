import { motion } from "motion/react";
import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import {
  Gift,
  Mail,
  Heart,
  Download,
  RotateCcw,
  Star,
  MessageSquare,
} from "lucide-react";
import { FeedbackForm } from "./FeedbackForm";
import { Navbar } from "./Navbar";
import { FloatingEmojiBackground } from "./FloatingEmojiBackground";
import { recordInteraction } from "@/lib/api/recommendations";

interface FinalResultProps {
  gift: any;
  cardId: string;
  message: string | null;
  recipientName: string;
  senderName: string;
  onStartOver: () => void;
  onLogoClick: () => void;
  onSignIn?: () => void;
  onSignUp?: () => void;
  showAuthButtons?: boolean;
  onAdminClick?: () => void;
}

export function FinalResult({
  gift,
  cardId,
  message,
  recipientName,
  senderName,
  onStartOver,
  onLogoClick,
  onSignIn,
  onSignUp,
  showAuthButtons = true,
  onAdminClick,
}: FinalResultProps) {
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [selectedRating, setSelectedRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [ratingMessage, setRatingMessage] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    if (gift?.id) {
      recordInteraction(gift.id, "click").catch(() => {
        // silently ignore — user may not be logged in
      });
    }
  }, [gift?.id]);

  const activeRating = hoverRating || selectedRating;

  const handleRate = async (rating: number) => {
    setSelectedRating(rating);
    setRatingMessage(`Thank you for rating ${rating} stars.`);
    if (gift?.id) {
      try {
        await recordInteraction(gift.id, "rating", rating);
      } catch {
        // ignore when user is not authenticated
      }
    }
  };

  const giftName = gift?.name ?? gift?.title ?? "Gift";
  const giftPrice = gift?.price ?? "";
  const giftImage = gift?.image ?? gift?.image_url ?? "";
  const giftCategory = gift?.category ?? gift?.category_name ?? "";
  const giftDescription = gift?.description ?? "";
  const giftProductUrl = gift?.product_url ?? gift?.productUrl ?? "";
  const cardText =
    "Wishing you joy and happiness on this special occasion. May every moment be filled with love and beautiful memories.";
  const cardPreview = [
    `Dear ${recipientName || "Recipient"},`,
    `"${cardText}"`,
    `With love, ${senderName || "Sender"}`,
  ].join("\n");
  const packageSummary = [
    `Gift: ${giftName}`,
    giftPrice ? `Price: ${giftPrice}` : null,
    giftCategory ? `Category: ${giftCategory}` : null,
    giftDescription ? `Gift Description: ${giftDescription}` : null,
    giftProductUrl ? `Product URL: ${giftProductUrl}` : null,
    recipientName ? `Recipient: ${recipientName}` : null,
    senderName ? `Sender: ${senderName}` : null,
    cardId ? `Card Template: ${cardId}` : null,
    "Greeting Card:",
    cardPreview,
    "",
    "Letter:",
    message ? `Message: ${message}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  const downloadAsText = () => {
    const blob = new Blob([packageSummary], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "gift-package.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const buildSimplePdf = (lines: string[]) => {
    const esc = (s: string) =>
      s
        .replace(/[^\x20-\x7E]/g, "?")
        .replaceAll("\\", "\\\\")
        .replaceAll("(", "\\(")
        .replaceAll(")", "\\)");

    const maxLines = 44;
    const chunks: string[][] = [];
    for (let i = 0; i < lines.length; i += maxLines) {
      chunks.push(lines.slice(i, i + maxLines));
    }
    if (chunks.length === 0) chunks.push(["Gift Package"]);

    const objects: string[] = [];
    const pageObjects: string[] = [];
    const pageCount = chunks.length;
    const fontObjId = 3 + pageCount * 2;

    objects.push("<< /Type /Catalog /Pages 2 0 R >>");
    objects.push("<< /Type /Pages /Kids [__KIDS__] /Count __COUNT__ >>");

    let objId = 3;
    const contentIds: number[] = [];
    for (const pageLines of chunks) {
      const contentObjId = objId + 1;
      contentIds.push(contentObjId);
      pageObjects.push(`${objId} 0 R`);
      const pageObj = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${fontObjId} 0 R >> >> /Contents ${contentObjId} 0 R >>`;
      objects.push(pageObj);

      const body = [
        "BT",
        "/F1 12 Tf",
        "48 800 Td",
        ...pageLines.flatMap((line, index) =>
          index === 0 ? [`(${esc(line)}) Tj`] : ["0 -17 Td", `(${esc(line)}) Tj`],
        ),
        "ET",
      ].join("\n");
      objects.push(`<< /Length ${body.length} >>\nstream\n${body}\nendstream`);
      objId += 2;
    }

    objects.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");

    objects[1] = objects[1]
      .replace("__KIDS__", pageObjects.join(" "))
      .replace("__COUNT__", String(pageCount));

    let pdf = "%PDF-1.4\n";
    const offsets: number[] = [0];
    objects.forEach((body, i) => {
      offsets.push(pdf.length);
      pdf += `${i + 1} 0 obj\n${body}\nendobj\n`;
    });

    const xrefStart = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n`;
    pdf += "0000000000 65535 f \n";
    offsets.slice(1).forEach((off) => {
      pdf += `${String(off).padStart(10, "0")} 00000 n \n`;
    });
    pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;
    return new Blob([pdf], { type: "application/pdf" });
  };

  const handleDownloadPdf = () => {
    setActionStatus(null);
    try {
      const lines = [
        "Gift Package",
        "",
        "Gift Details",
        `Name: ${giftName}`,
        giftPrice ? `Price: ${giftPrice}` : "",
        giftCategory ? `Category: ${giftCategory}` : "",
        giftDescription ? `Description: ${giftDescription}` : "",
        giftProductUrl ? `Product URL: ${giftProductUrl}` : "",
        giftImage ? `Image URL: ${giftImage}` : "",
        "",
        "Greeting Card",
        `Template: ${cardId || "N/A"}`,
        cardPreview,
        "",
        "Letter",
        message || "No personal letter added.",
      ].filter(Boolean);

      const blob = buildSimplePdf(lines);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "gift-package.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      setActionStatus({
        type: "success",
        text: "Gift package PDF downloaded.",
      });
    } catch {
      downloadAsText();
      setActionStatus({
        type: "error",
        text: "PDF generation failed. Downloaded package as text instead.",
      });
    }
  };

  const handleShareEmail = () => {
    setActionStatus(null);
    const subject = `Gift package for ${recipientName || "someone special"}`;
    const body = `${packageSummary}\n\nShared from the gift app.`;
    window.open(
      `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`,
      "_blank",
      "noopener,noreferrer",
    );
    setActionStatus({
      type: "success",
      text: "Email draft opened in your mail app.",
    });
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
        onAdminClick={onAdminClick}
      />

      {/* Main Content */}
      <div className="flex-1 max-w-7xl mx-auto px-8 py-12 w-full relative z-10">
        {/* Success Header */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <motion.div
            animate={{ rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="inline-block mb-6"
          >
            <div className="w-24 h-24 bg-linear-to-br from-rose-500 via-pink-500 to-orange-500 rounded-3xl flex items-center justify-center shadow-2xl">
              <Gift className="text-white" size={48} />
            </div>
          </motion.div>
          <h1 className="text-6xl mb-4 bg-linear-to-r from-rose-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
            Your Gift is Perfect!
          </h1>
          <p className="text-gray-600 text-2xl">
            Everything is beautifully packaged and ready to share
          </p>
        </motion.div>

        {/* Gift Package Display */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white/80 backdrop-blur-xl rounded-3xl p-10 shadow-2xl border-4 border-rose-100 mb-12"
        >
          <div className="grid md:grid-cols-3 gap-8">
            {/* Wrapped Gift */}
            <motion.div
              whileHover={{ scale: 1.05, rotateY: 10 }}
              transition={{ type: "spring" }}
              className="bg-linear-to-br from-rose-100 via-pink-100 to-orange-100 rounded-3xl p-8 shadow-xl relative overflow-hidden"
              style={{ perspective: "1000px" }}
            >
              <div className="absolute top-0 left-0 right-0 h-1/2 bg-linear-to-b from-white/40 to-transparent rounded-t-3xl" />

              <h3 className="text-2xl font-bold text-center mb-6 flex items-center justify-center gap-2">
                <Gift className="text-rose-600" size={28} />
                Your Gift
              </h3>

              <div className="relative mb-6">
                <div className="absolute inset-0 bg-linear-to-br from-red-200 to-rose-300 rounded-2xl blur-xl opacity-50" />
                <div className="relative h-64 rounded-2xl overflow-hidden border-4 border-white shadow-xl">
                  <img
                    src={gift.image}
                    alt={gift.name}
                    className="w-full h-full object-cover"
                  />
                  {/* Ribbon overlay */}
                  <div className="absolute left-1/2 top-0 bottom-0 w-12 -translate-x-1/2 bg-linear-to-b from-rose-500 to-orange-500 opacity-80" />
                  <div className="absolute left-0 right-0 top-1/2 h-12 -translate-y-1/2 bg-linear-to-r from-rose-500 via-pink-500 to-orange-500 opacity-80" />
                  {/* Bow */}
                  <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-linear-to-br from-rose-400 via-pink-400 to-orange-400 rounded-full shadow-lg" />
                </div>
              </div>

              <div className="text-center">
                <h4 className="text-xl font-semibold mb-2">{gift.name}</h4>
                <div className="inline-block bg-rose-600 text-white px-6 py-2 rounded-full font-bold text-lg">
                  {gift.price}
                </div>
              </div>
            </motion.div>

            {/* Greeting Card */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              transition={{ type: "spring" }}
              className="bg-linear-to-br from-amber-100 via-yellow-100 to-orange-100 rounded-3xl p-8 shadow-xl"
            >
              <h3 className="text-2xl font-bold text-center mb-6 flex items-center justify-center gap-2">
                <Mail className="text-amber-600" size={28} />
                Greeting Card
              </h3>

              <div className="bg-white rounded-2xl p-6 shadow-inner mb-4 min-h-80 flex flex-col justify-center border-4 border-amber-200">
                <div className="text-center mb-4">
                  <div className="text-5xl mb-4">🎉</div>
                  <h4 className="text-2xl font-bold mb-3">
                    Dear {recipientName},
                  </h4>
                  <p className="text-gray-700 italic leading-relaxed">
                    "Wishing you joy and happiness on this special occasion. May
                    every moment be filled with love and beautiful memories."
                  </p>
                </div>
                <div className="text-center mt-6 pt-6 border-t-2 border-amber-200">
                  <p className="text-gray-600 flex items-center justify-center gap-2">
                    With love,{" "}
                    <span className="font-semibold">{senderName}</span> ❤️
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Personal Letter */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              transition={{ type: "spring" }}
              className="bg-linear-to-br from-rose-100 via-pink-100 to-orange-100 rounded-3xl p-8 shadow-xl"
            >
              <h3 className="text-2xl font-bold text-center mb-6 flex items-center justify-center gap-2">
                <Heart className="text-emerald-600" size={28} />
                {message ? "Personal Letter" : "No Letter"}
              </h3>

              {message ? (
                <div className="bg-white rounded-2xl p-6 shadow-inner min-h-80 max-h-80 overflow-y-auto border-4 border-rose-200">
                  <pre className="whitespace-pre-wrap font-serif text-gray-700 leading-relaxed text-sm">
                    {message}
                  </pre>
                </div>
              ) : (
                <div className="bg-white rounded-2xl p-6 shadow-inner min-h-80 flex items-center justify-center border-4 border-emerald-200">
                  <div className="text-center text-gray-400">
                    <Heart size={48} className="mx-auto mb-4 opacity-30" />
                    <p className="italic">No letter added</p>
                    <p className="text-sm mt-2">
                      The gift speaks for itself ✨
                    </p>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="grid md:grid-cols-3 gap-6 mb-16"
        >
          <Button
            size="lg"
            variant="outline"
            className="py-8 text-lg border-2 border-emerald-300 hover:bg-emerald-50"
            onClick={handleDownloadPdf}
          >
            <Download className="mr-2" size={24} />
            Download PDF
          </Button>

          <Button
            size="lg"
            variant="outline"
            className="py-8 text-lg border-2 border-teal-300 hover:bg-teal-50"
            onClick={handleShareEmail}
          >
            <Mail className="mr-2" size={24} />
            Share via Email
          </Button>

          <Button
            size="lg"
            className="py-8 text-lg bg-linear-to-r from-emerald-600 via-teal-600 to-cyan-600 shadow-lg hover:shadow-emerald-500/50"
            onClick={onStartOver}
          >
            <RotateCcw className="mr-2" size={24} />
            Create Another Gift
          </Button>
        </motion.div>
        {actionStatus && (
          <div
            className={`mb-10 rounded-xl border px-4 py-3 text-sm ${
              actionStatus.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-rose-200 bg-rose-50 text-rose-700"
            }`}
          >
            {actionStatus.text}
          </div>
        )}

        {/* Rate Your Experience */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="bg-linear-to-br from-white via-amber-50 to-yellow-50 rounded-3xl p-10 shadow-xl border-4 border-amber-100 text-center mb-16"
        >
          <h3 className="text-3xl font-bold mb-4 bg-linear-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
            How was your experience?
          </h3>
          <p className="text-gray-600 mb-6 text-lg">
            Your feedback helps us improve
          </p>

          <div className="flex justify-center gap-4 mb-6">
            {[1, 2, 3, 4, 5].map((rating) => (
              <motion.button
                key={rating}
                whileHover={{ scale: 1.3, rotate: 10 }}
                whileTap={{ scale: 0.9 }}
                onMouseEnter={() => setHoverRating(rating)}
                onMouseLeave={() => setHoverRating(0)}
                onClick={() => handleRate(rating)}
                className="group"
              >
                <Star
                  size={48}
                  className={
                    rating <= activeRating
                      ? "text-amber-400 fill-amber-400 transition-colors"
                      : "text-gray-300 transition-colors"
                  }
                />
              </motion.button>
            ))}
          </div>
          {ratingMessage && (
            <p className="text-sm text-amber-700 font-medium mb-6">
              {ratingMessage}
            </p>
          )}

          <Button
            onClick={() => setFeedbackOpen(true)}
            variant="outline"
            className="border-2 border-amber-400 hover:bg-amber-50 px-8 py-6 text-lg"
          >
            <MessageSquare className="mr-2" size={20} />
            Leave Detailed Feedback
          </Button>
        </motion.div>
      </div>

      {/* Floating elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute"
            initial={{
              x:
                Math.random() *
                (typeof window !== "undefined" ? window.innerWidth : 1000),
              y:
                typeof window !== "undefined" ? window.innerHeight + 100 : 1000,
              rotate: 0,
            }}
            animate={{
              y: -100,
              rotate: 360,
            }}
            transition={{
              duration: 10 + Math.random() * 8,
              repeat: Infinity,
              delay: Math.random() * 8,
              ease: "linear",
            }}
          >
            {i % 4 === 0 ? (
              <Heart
                className="text-pink-300 opacity-40"
                size={20 + Math.random() * 25}
              />
            ) : i % 4 === 1 ? (
              <Gift
                className="text-emerald-300 opacity-40"
                size={20 + Math.random() * 25}
              />
            ) : i % 4 === 2 ? (
              <Star
                className="text-amber-300 opacity-40"
                size={20 + Math.random() * 25}
              />
            ) : (
              <div className="text-3xl opacity-40">✨</div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Feedback Form Modal */}
      <FeedbackForm
        isOpen={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
      />
    </div>
  );
}
