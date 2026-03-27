import { motion } from "motion/react";
import { Sparkles, Heart, Star, Gift, Zap } from "lucide-react";

const ICONS = [Sparkles, Heart, Star, Gift, Zap];
const COLORS = [
  "text-rose-300/30",
  "text-pink-300/30",
  "text-amber-300/25",
  "text-violet-300/25",
  "text-emerald-300/20",
];

const PARTICLES = Array.from({ length: 20 }, (_, i) => ({
  Icon: ICONS[i % ICONS.length],
  color: COLORS[i % COLORS.length],
  size: 10 + (i % 5) * 4,
  left: `${(i * 5.2 + 3) % 100}%`,
  top: `${(i * 7.7 + 5) % 100}%`,
  dur: 10 + (i % 6) * 2,
  delay: i * 0.5,
  yRange: 18 + (i % 4) * 6,
  xRange: 10 + (i % 3) * 5,
}));

export function FloatingAnimations() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      {PARTICLES.map((p, i) => (
        <motion.div
          key={i}
          className={`absolute ${p.color}`}
          style={{ left: p.left, top: p.top }}
          animate={{
            y: [0, -p.yRange, 0, p.yRange * 0.6, 0],
            x: [0, p.xRange, -p.xRange * 0.5, p.xRange * 0.3, 0],
            rotate: [0, 180, 360],
            scale: [0.6, 1, 0.8, 0.9, 0.6],
          }}
          transition={{
            duration: p.dur,
            repeat: Infinity,
            ease: "easeInOut",
            delay: p.delay,
          }}
        >
          <p.Icon size={p.size} />
        </motion.div>
      ))}
    </div>
  );
}
