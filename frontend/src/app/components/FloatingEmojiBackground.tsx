import { motion } from "motion/react";
import { useMemo } from "react";

const EMOJIS = [
  "🎁",
  "🌸",
  "💕",
  "✨",
  "🌷",
  "💐",
  "🌼",
  "⭐",
  "🎀",
  "💝",
  "🧸",
  "❤️",
];

interface FloatingEmojiBackgroundProps {
  count?: number;
  className?: string;
}

export function FloatingEmojiBackground({
  count = 45,
  className = "",
}: FloatingEmojiBackgroundProps) {
  const floaters = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        icon: EMOJIS[i % EMOJIS.length],
        x: 4 + ((i * 11 + i * 5) % 92),
        y: 6 + ((i * 9 + i * 7) % 86),
        size: 14 + (i % 6) * 4,
        delay: i * 0.35,
        duration: 4 + (i % 6) * 0.6,
      })),
    [count],
  );

  return (
    <div
      className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`}
    >
      {floaters.map((floater) => (
        <motion.div
          key={floater.id}
          className="absolute select-none"
          style={{
            left: `${floater.x}%`,
            top: `${floater.y}%`,
            fontSize: floater.size,
          }}
          animate={{
            y: [0, -18, 0],
            x: [0, 6, 0],
            rotate: [-8, 8, -8],
            opacity: [0.08, 0.26, 0.08],
          }}
          transition={{
            delay: floater.delay,
            duration: floater.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          {floater.icon}
        </motion.div>
      ))}
    </div>
  );
}
