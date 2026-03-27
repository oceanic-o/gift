import { motion } from "motion/react";
import { Gift } from "lucide-react";
import { FloatingEmojiBackground } from "./FloatingEmojiBackground";

interface LoadingScreenProps {
  message?: string;
  detail?: string;
  fullScreen?: boolean;
}

export function LoadingScreen({
  message = "Loading",
  detail = "Preparing something special for you",
  fullScreen = true,
}: LoadingScreenProps) {
  return (
    <div
      className={`${
        fullScreen ? "min-h-screen" : "min-h-[240px]"
      } relative overflow-hidden flex items-center justify-center bg-gradient-to-br from-stone-50 via-rose-50 to-orange-50`}
    >
      <FloatingEmojiBackground />
      <div className="relative z-10">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="rounded-3xl bg-white/80 backdrop-blur-xl border border-white/60 shadow-xl px-10 py-8 flex flex-col items-center"
        >
          <motion.div
            animate={{ y: [0, -8, 0], rotate: [0, -6, 6, 0] }}
            transition={{ duration: 2.4, repeat: Infinity }}
            className="w-16 h-16 rounded-2xl bg-gradient-to-br from-rose-500 to-orange-400 flex items-center justify-center shadow-lg"
          >
            <Gift className="text-white" size={32} />
          </motion.div>

          <div className="mt-6 text-center">
            <h2 className="text-xl font-semibold text-rose-700">
              {message}
              <motion.span
                aria-hidden
                className="inline-flex ml-2 gap-1"
                animate={{ opacity: [0.2, 1, 0.2] }}
                transition={{ duration: 1.4, repeat: Infinity }}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
                <span className="h-1.5 w-1.5 rounded-full bg-pink-500" />
                <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
              </motion.span>
            </h2>
            <p className="text-sm text-gray-600 mt-2 max-w-xs">{detail}</p>
          </div>
        </motion.div>

        <motion.div
          className="absolute -inset-8 rounded-[32px] border border-rose-200/60"
          animate={{ opacity: [0.4, 0.7, 0.4], scale: [1, 1.04, 1] }}
          transition={{ duration: 2.4, repeat: Infinity }}
        />
      </div>
    </div>
  );
}
