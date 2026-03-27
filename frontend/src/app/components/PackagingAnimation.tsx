import { motion, AnimatePresence } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "./ui/button";
import { Navbar } from "./Navbar";
import { FloatingEmojiBackground } from "./FloatingEmojiBackground";

interface PackagingAnimationProps {
  gift: any;
  card?: { cardId: string; recipientName: string; senderName: string };
  letter?: { letterData: string };
  onComplete: () => void;
  onBack: () => void;
}

// ---------- helpers ----------

function rand(seed: number, min: number, max: number) {
  const s = Math.sin(seed * 9301 + 49297) * 233280;
  return min + (s - Math.floor(s)) * (max - min);
}

// ---------- Confetti ----------

function ConfettiBurst() {
  const pcs = useMemo(
    () =>
      Array.from({ length: 48 }, (_, i) => ({
        id: i,
        a: (i / 48) * 360 + rand(i, -8, 8),
        d: 90 + rand(i, 0, 120),
        c: [
          "#e63946",
          "#f4a261",
          "#2a9d8f",
          "#ffd166",
          "#8b5cf6",
          "#60a5fa",
          "#ff6b6b",
          "#feca57",
        ][i % 8],
        w: 6 + rand(i, 0, 8),
        h: 3 + rand(i, 0, 5),
        rot: rand(i, 0, 720),
      })),
    [],
  );
  return (
    <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
      <div className="relative">
        {pcs.map((p) => (
          <motion.div
            key={p.id}
            className="absolute rounded-sm"
            style={{
              width: p.w,
              height: p.h,
              background: p.c,
              left: 0,
              top: 0,
            }}
            initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }}
            animate={{
              x: Math.cos((p.a * Math.PI) / 180) * p.d,
              y: Math.sin((p.a * Math.PI) / 180) * p.d,
              opacity: 0,
              rotate: p.rot,
            }}
            transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
          />
        ))}
      </div>
    </div>
  );
}

// ---------- Snowflake path generator ----------

function snowflakePath(cx: number, cy: number, r: number, spokes = 6): string {
  const step = (Math.PI * 2) / spokes;
  const parts: string[] = [];
  for (let i = 0; i < spokes; i++) {
    const angle = i * step - Math.PI / 2;
    const x1 = cx + Math.cos(angle) * r;
    const y1 = cy + Math.sin(angle) * r;
    parts.push(`M${cx},${cy} L${x1},${y1}`);
    // small crossbars
    const xm = cx + Math.cos(angle) * r * 0.55;
    const ym = cy + Math.sin(angle) * r * 0.55;
    const bx1 = xm + Math.cos(angle + Math.PI / 2) * r * 0.22;
    const by1 = ym + Math.sin(angle + Math.PI / 2) * r * 0.22;
    const bx2 = xm - Math.cos(angle + Math.PI / 2) * r * 0.22;
    const by2 = ym - Math.sin(angle + Math.PI / 2) * r * 0.22;
    parts.push(`M${bx1},${by1} L${bx2},${by2}`);
    // tip fork
    const tx1 = x1 + Math.cos(angle + Math.PI / 6) * r * 0.18;
    const ty1 = y1 + Math.sin(angle + Math.PI / 6) * r * 0.18;
    const tx2 = x1 + Math.cos(angle - Math.PI / 6) * r * 0.18;
    const ty2 = y1 + Math.sin(angle - Math.PI / 6) * r * 0.18;
    parts.push(`M${x1},${y1} L${tx1},${ty1}`);
    parts.push(`M${x1},${y1} L${tx2},${ty2}`);
  }
  return parts.join(" ");
}

// ---------- Main component ----------

export function PackagingAnimation({
  gift,
  card,
  letter,
  onComplete,
  onBack,
}: PackagingAnimationProps) {
  const [stage, setStage] = useState(-1);
  const [burst, setBurst] = useState(false);
  const timers = useRef<number[]>([]);

  const stages = useMemo(
    () => [
      "Dropping the box...",
      "Dropping your chosen gift...",
      "Settling gift inside...",
      "Dropping the lid...",
      "Wrapping the box...",
      "Tying ribbon...",
      "Adding greeting card...",
      "Adding letter...",
      "Ready to send ✨",
    ],
    [],
  );

  const durations = useMemo(
    () => [1320, 1540, 1180, 1360, 1240, 1360, 1240, 1240, 900],
    [],
  );

  useEffect(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    let t = 480;
    durations.forEach((d, i) => {
      timers.current.push(window.setTimeout(() => setStage(i), t));
      t += d;
    });
    timers.current.push(window.setTimeout(() => setBurst(true), t - 1100));
    timers.current.push(window.setTimeout(() => onComplete(), t + 1000));
    return () => timers.current.forEach(clearTimeout);
  }, [durations, onComplete]);

  const after = (i: number) => stage >= i;
  const progress = stage < 0 ? 0 : ((stage + 1) / stages.length) * 100;

  const recipient = (card?.recipientName || "For You").slice(0, 14);
  const letterSnippet = (
    letter?.letterData || "With love and warm wishes"
  ).slice(0, 24);

  // Box dimensions (isometric 3-face view)
  // Front face: parallelogram-ish trapezoid for a bold 3/4 perspective
  // We use a classic isometric-ish layout: front, right side, top

  // ─── box geometry ───────────────────────────────────────────────
  // Anchor point (bottom-left of front face):
  const bx = 120,
    by = 410;
  const fw = 220,
    fh = 190; // front face width/height
  const sx = 80,
    sy = -50; // right-side skew vector (going right-up)
  const th = 45; // top face height (in screen Y after skew)

  // Front face corners: bottom-left, bottom-right, top-right, top-left
  const FL = [bx, by];
  const FR = [bx + fw, by];
  const FT = [bx + fw, by - fh];
  const FTLL = [bx, by - fh];

  // Right side (skew from front-right edge)
  const RBR = [FR[0] + sx, FR[1] + sy];
  const RTR = [FT[0] + sx, FT[1] + sy];

  // Top face (from top of front and top of right side)
  const TFL = FTLL;
  const TFR = FT;
  const TRTR = RTR;
  const TRL = [FTLL[0] + sx, FTLL[1] + sy];

  // Inner cavity geometry so the box reads as hollow from the top.
  const insetFront = 18;
  const insetBack = 14;
  const insetY = 16;
  const holeDepth = 58;
  const IF_TL = [TFL[0] + insetFront, TFL[1] + insetY];
  const IF_TR = [TFR[0] - insetFront, TFR[1] + insetY];
  const IF_BR = [TRTR[0] - insetBack, TRTR[1] + insetY];
  const IF_BL = [TRL[0] + insetBack, TRL[1] + insetY];
  const IF_WALL_TL = IF_TL;
  const IF_WALL_TR = IF_TR;
  const IF_WALL_FR_BL = [IF_TL[0], IF_TL[1] + holeDepth];
  const IF_WALL_FR_BR = [IF_TR[0], IF_TR[1] + holeDepth];
  const IF_WALL_RT_TR = IF_BR;
  const IF_WALL_RT_TL = IF_TR;
  const IF_WALL_RT_BR = [IF_BR[0], IF_BR[1] + holeDepth];
  const IF_WALL_RT_BL = [IF_TR[0], IF_TR[1] + holeDepth];
  const IF_FLOOR_FL = IF_WALL_FR_BL;
  const IF_FLOOR_FR = IF_WALL_FR_BR;
  const IF_FLOOR_BR = IF_WALL_RT_BR;
  const IF_FLOOR_BL = [IF_BL[0], IF_BL[1] + holeDepth];

  const pts = (arr: number[][]) => arr.map((p) => p.join(",")).join(" ");

  // LID geometry (same footprint, sits on top, 24px tall)
  const lidH = 28;
  const LFL = [bx - 6, by - fh - lidH];
  const LFR = [bx + fw + 6, by - fh - lidH];
  const LFBR = [bx + fw + 6, by - fh + 4];
  const LFBL = [bx - 6, by - fh + 4];
  const LRTR = [LFR[0] + sx, LFR[1] + sy];
  const LRBR = [LFBR[0] + sx, LFBR[1] + sy];
  const LTFL = LFL;
  const LTFR = LFR;
  const LTRTR = LRTR;
  const LTRL = [LFL[0] + sx, LFL[1] + sy];

  return (
    <div
      className="min-h-screen relative overflow-hidden flex flex-col"
      style={{
        background:
          "linear-gradient(135deg, #fafaf9 0%, #fff1f2 48%, #ffedd5 100%)",
      }}
    >
      <FloatingEmojiBackground />

      <Navbar
        showAuthButtons={false}
        showNavLinks={false}
        onLogoClick={onBack}
      />

      {/* top bar */}
      <div className="relative z-20 flex items-center justify-between px-6 pt-6 pb-3">
        <Button
          variant="outline"
          onClick={onBack}
          className="border-rose-200 bg-white/75 hover:bg-white text-rose-600 shadow-sm backdrop-blur-sm"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <AnimatePresence mode="wait">
          <motion.p
            key={stage}
            initial={{ opacity: 0, y: 6, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -6, filter: "blur(4px)" }}
            transition={{ duration: 0.36 }}
            className="text-[11px] tracking-[0.22em] uppercase font-semibold text-rose-500"
          >
            {stages[Math.max(0, Math.min(stage, stages.length - 1))]}
          </motion.p>
        </AnimatePresence>

        <span className="text-[10px] uppercase tracking-[0.16em] font-semibold text-rose-400 bg-white/70 border border-rose-100 rounded-full px-3 py-1">
          Gift Pack v5
        </span>
      </div>

      {/* progress bar */}
      <div className="relative z-20 px-6 pb-2">
        <div className="h-1 w-full rounded-full overflow-hidden bg-rose-200/60">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-rose-500 to-orange-400"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.86, ease: "easeInOut" }}
          />
        </div>
      </div>

      {/* scene */}
      <div className="flex-1 flex items-center justify-center relative z-10 py-4">
        <div className="relative" style={{ width: 540, height: 580 }}>
          {/* floor shadow */}
          <div
            className="absolute"
            style={{
              left: "10%",
              right: "10%",
              bottom: 28,
              height: 28,
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse at center, rgba(100,20,20,0.30) 0%, rgba(100,20,20,0.12) 55%, transparent 100%)",
              filter: "blur(4px)",
            }}
          />

          <svg
            viewBox="0 0 540 520"
            style={{
              width: "100%",
              height: "100%",
              overflow: "visible",
              filter:
                "drop-shadow(0 24px 28px rgba(140,20,20,0.22)) drop-shadow(0 4px 8px rgba(0,0,0,0.10))",
            }}
          >
            <defs>
              {/* ── BOX COLORS ── */}
              <linearGradient id="boxFront" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef1c1c" />
                <stop offset="100%" stopColor="#a80d0d" />
              </linearGradient>
              <linearGradient id="boxRight" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#c01010" />
                <stop offset="100%" stopColor="#7a0a0a" />
              </linearGradient>
              <linearGradient id="boxTop" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#f84444" />
                <stop offset="100%" stopColor="#c91515" />
              </linearGradient>

              {/* ── LID COLORS (slightly lighter red) ── */}
              <linearGradient id="lidFront" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f62020" />
                <stop offset="100%" stopColor="#b81010" />
              </linearGradient>
              <linearGradient id="lidRight" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#d41414" />
                <stop offset="100%" stopColor="#8c0c0c" />
              </linearGradient>
              <linearGradient id="lidTop" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#ff5050" />
                <stop offset="100%" stopColor="#d81a1a" />
              </linearGradient>

              {/* ── RIBBON (gold/cream) ── */}
              <linearGradient id="ribbonV" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#c8a740" />
                <stop offset="40%" stopColor="#f0d070" />
                <stop offset="60%" stopColor="#f5e080" />
                <stop offset="100%" stopColor="#b89030" />
              </linearGradient>
              <linearGradient id="ribbonH" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#d4b44a" />
                <stop offset="50%" stopColor="#f0d468" />
                <stop offset="100%" stopColor="#b89030" />
              </linearGradient>
              <linearGradient id="ribbonLidV" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#c09030" />
                <stop offset="50%" stopColor="#f2dc6a" />
                <stop offset="100%" stopColor="#c09030" />
              </linearGradient>
              <linearGradient id="ribbonLidH" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#c09030" />
                <stop offset="50%" stopColor="#f2dc6a" />
                <stop offset="100%" stopColor="#c09030" />
              </linearGradient>

              {/* ── BOW ── */}
              <radialGradient id="bowLeft" cx="60%" cy="40%" r="60%">
                <stop offset="0%" stopColor="#c91c1c" />
                <stop offset="100%" stopColor="#7a0808" />
              </radialGradient>
              <radialGradient id="bowRight" cx="40%" cy="40%" r="60%">
                <stop offset="0%" stopColor="#c91c1c" />
                <stop offset="100%" stopColor="#7a0808" />
              </radialGradient>
              <radialGradient id="bowCenter" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#e02020" />
                <stop offset="100%" stopColor="#900808" />
              </radialGradient>

              {/* ── CARTON INTERIOR (before lid) ── */}
              <linearGradient id="cartonInner" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f0cba0" />
                <stop offset="100%" stopColor="#d0a060" />
              </linearGradient>
              <linearGradient id="cartonFloor" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#cfa870" />
                <stop offset="100%" stopColor="#b08540" />
              </linearGradient>
              <linearGradient id="cartonRim" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#e8c890" />
                <stop offset="100%" stopColor="#c09050" />
              </linearGradient>
              <linearGradient id="cartonInnerFront" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f3d7af" />
                <stop offset="100%" stopColor="#c8904d" />
              </linearGradient>
              <linearGradient id="cartonInnerRight" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#d6a66f" />
                <stop offset="100%" stopColor="#b77e3f" />
              </linearGradient>
              <linearGradient id="cavityDepth" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(90,42,20,0.20)" />
                <stop offset="100%" stopColor="rgba(40,18,10,0.46)" />
              </linearGradient>

              {/* ── WRAP PATTERN ── */}
              <pattern
                id="wrapPat"
                patternUnits="userSpaceOnUse"
                width="30"
                height="30"
              >
                <rect width="30" height="30" fill="#ef1c1c" />
                {/* small snowflake dots for the wrap texture */}
                <circle cx="15" cy="15" r="1.5" fill="rgba(255,255,255,0.25)" />
                <circle cx="0" cy="0" r="1" fill="rgba(255,255,255,0.15)" />
                <circle cx="30" cy="0" r="1" fill="rgba(255,255,255,0.15)" />
                <circle cx="0" cy="30" r="1" fill="rgba(255,255,255,0.15)" />
                <circle cx="30" cy="30" r="1" fill="rgba(255,255,255,0.15)" />
              </pattern>
              <pattern
                id="wrapPatR"
                patternUnits="userSpaceOnUse"
                width="30"
                height="30"
              >
                <rect width="30" height="30" fill="#c01010" />
                <circle cx="15" cy="15" r="1.5" fill="rgba(255,255,255,0.18)" />
              </pattern>
            </defs>

            {/* ══════════════════════════════════════════════
                1.  CARDBOARD BOX (drops in first)
            ══════════════════════════════════════════════ */}
            <motion.g
              initial={{ y: -440, opacity: 0 }}
              animate={{
                y: after(0) ? [0, 34, -12, 5, 0] : -440,
                x: after(0) ? [0, -10, 6, -3, 0] : 0,
                scale: after(0) ? [1, 1.02, 0.994, 1.006, 1] : 1,
                opacity: after(0) ? 1 : 0,
              }}
              transition={{
                y: {
                  duration: 1.42,
                  times: [0, 0.45, 0.7, 0.88, 1],
                  ease: [0.22, 0.9, 0.28, 1],
                },
                x: {
                  duration: 1.42,
                  times: [0, 0.45, 0.7, 0.88, 1],
                  ease: [0.2, 0.9, 0.3, 1],
                },
                scale: {
                  duration: 1.42,
                  times: [0, 0.45, 0.7, 0.88, 1],
                  ease: [0.2, 0.9, 0.3, 1],
                },
                opacity: { duration: 0.26 },
              }}
            >
              {/* outer shell */}
              <polygon
                points={`${FL.join()},${FR.join()},${FT.join()},${FTLL.join()}`}
                fill="url(#boxFront)"
              />
              <polygon
                points={`${FR.join()},${RBR.join()},${RTR.join()},${FT.join()}`}
                fill="url(#boxRight)"
              />

              {/* box opening rim (keeps outside solid while inside is hollow) */}
              <polygon
                points={`${TFL.join()},${TFR.join()},${IF_TR.join()},${IF_TL.join()}`}
                fill="url(#cartonRim)"
                opacity="0.92"
              />
              <polygon
                points={`${TFR.join()},${TRTR.join()},${IF_BR.join()},${IF_TR.join()}`}
                fill="url(#cartonRim)"
                opacity="0.86"
              />
              <polygon
                points={`${TRTR.join()},${TRL.join()},${IF_BL.join()},${IF_BR.join()}`}
                fill="url(#cartonRim)"
                opacity="0.74"
              />

              {/* interior walls and floor */}
              <polygon
                points={`${IF_WALL_TL.join()},${IF_WALL_TR.join()},${IF_WALL_FR_BR.join()},${IF_WALL_FR_BL.join()}`}
                fill="url(#cartonInnerFront)"
              />
              <polygon
                points={`${IF_WALL_RT_TL.join()},${IF_WALL_RT_TR.join()},${IF_WALL_RT_BR.join()},${IF_WALL_RT_BL.join()}`}
                fill="url(#cartonInnerRight)"
              />
              <polygon
                points={`${IF_FLOOR_FL.join()},${IF_FLOOR_FR.join()},${IF_FLOOR_BR.join()},${IF_FLOOR_BL.join()}`}
                fill="url(#cartonFloor)"
              />
              <polygon
                points={`${IF_TL.join()},${IF_TR.join()},${IF_BR.join()},${IF_BL.join()}`}
                fill="url(#cavityDepth)"
              />
            </motion.g>

            {/* ══════════════════════════════════════════════
                2.  INNER GIFT (drops from above into box)
            ══════════════════════════════════════════════ */}
            <AnimatePresence>
              {after(1) && (
                <motion.g
                  initial={{ y: -290, opacity: 0, scale: 1.06 }}
                  animate={{
                    y: after(2) ? [0, 24, -9, 3, 0] : 0,
                    opacity: 1,
                    scale: 1,
                  }}
                  exit={{ opacity: 0 }}
                  transition={{
                    y: after(2)
                      ? {
                          duration: 0.96,
                          times: [0, 0.48, 0.72, 0.88, 1],
                          ease: [0.24, 0.9, 0.3, 1],
                        }
                      : { type: "spring", stiffness: 120, damping: 14 },
                    opacity: { duration: 0.28 },
                    scale: { duration: 0.32 },
                  }}
                >
                  {/* small red gift box sitting inside */}
                  <polygon
                    points="188,355 248,355 248,395 188,395"
                    fill="#d41020"
                  />
                  <polygon
                    points="248,355 272,337 272,377 248,395"
                    fill="#9a0a18"
                  />
                  <polygon
                    points="188,355 248,355 272,337 212,337"
                    fill="#ee3030"
                  />
                  {/* inner gift ribbon */}
                  <rect
                    x="212"
                    y="337"
                    width="10"
                    height="58"
                    fill="#f0d068"
                    opacity="0.9"
                  />
                  <rect
                    x="188"
                    y="368"
                    width="60"
                    height="8"
                    fill="#f0d068"
                    opacity="0.9"
                  />
                  {/* inner gift bow */}
                  <path
                    d="M217,340 C210,325 195,320 190,330 C186,338 199,346 217,340Z"
                    fill="#cc1020"
                  />
                  <path
                    d="M217,340 C224,325 239,320 244,330 C248,338 235,346 217,340Z"
                    fill="#cc1020"
                  />
                  <circle cx="217" cy="339" r="6" fill="#a80c1a" />
                </motion.g>
              )}
            </AnimatePresence>

            {/* ══════════════════════════════════════════════
                BOX FRONT FACE overlay (re-renders above gift)
            ══════════════════════════════════════════════ */}
            <motion.g
              initial={{ y: -440, opacity: 0 }}
              animate={{
                y: after(0) ? [0, 34, -12, 5, 0] : -440,
                x: after(0) ? [0, -10, 6, -3, 0] : 0,
                scale: after(0) ? [1, 1.02, 0.994, 1.006, 1] : 1,
                opacity: after(0) ? 1 : 0,
              }}
              transition={{
                y: {
                  duration: 1.42,
                  times: [0, 0.45, 0.7, 0.88, 1],
                  ease: [0.22, 0.9, 0.28, 1],
                },
                x: {
                  duration: 1.42,
                  times: [0, 0.45, 0.7, 0.88, 1],
                  ease: [0.2, 0.9, 0.3, 1],
                },
                scale: {
                  duration: 1.42,
                  times: [0, 0.45, 0.7, 0.88, 1],
                  ease: [0.2, 0.9, 0.3, 1],
                },
                opacity: { duration: 0.26 },
              }}
            >
              {/* front face on top (clips gift that would show through front wall) */}
              <polygon
                points={`${FL.join()},${FR.join()},${[FR[0], by - fh + 60].join()},${[FL[0], by - fh + 60].join()}`}
                fill="url(#boxFront)"
                opacity="0.92"
              />
            </motion.g>

            {/* ══════════════════════════════════════════════
                3.  LID (drops down)
            ══════════════════════════════════════════════ */}
            <motion.g
              initial={{ y: -340, opacity: 0 }}
              animate={{
                y: after(3) ? [0, 24, -9, 3, 0] : -340,
                opacity: after(3) ? 1 : 0,
              }}
              transition={{
                y: {
                  duration: 1.12,
                  times: [0, 0.48, 0.72, 0.88, 1],
                  ease: [0.24, 0.9, 0.3, 1],
                },
                opacity: { duration: 0.24 },
              }}
            >
              {/* lid front */}
              <polygon
                points={`${LFL.join()},${LFR.join()},${LFBR.join()},${LFBL.join()}`}
                fill="url(#lidFront)"
              />
              {/* lid right */}
              <polygon
                points={`${LFR.join()},${LRTR.join()},${LRBR.join()},${LFBR.join()}`}
                fill="url(#lidRight)"
              />
              {/* lid top */}
              <polygon
                points={`${LTFL.join()},${LTFR.join()},${LTRTR.join()},${LTRL.join()}`}
                fill="url(#lidTop)"
              />
            </motion.g>

            {/* ══════════════════════════════════════════════
                4.  WRAPPING PAPER overlay
            ══════════════════════════════════════════════ */}
            <AnimatePresence>
              {after(4) && (
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                >
                  {/* front wrap + snowflakes */}
                  <polygon
                    points={`${FL.join()},${FR.join()},${FT.join()},${FTLL.join()}`}
                    fill="url(#wrapPat)"
                    opacity="0.95"
                  />
                  {/* right wrap */}
                  <polygon
                    points={`${FR.join()},${RBR.join()},${RTR.join()},${FT.join()}`}
                    fill="url(#wrapPatR)"
                    opacity="0.95"
                  />
                  {/* lid front wrap */}
                  <polygon
                    points={`${LFL.join()},${LFR.join()},${LFBR.join()},${LFBL.join()}`}
                    fill="url(#wrapPat)"
                    opacity="0.95"
                  />
                  {/* lid right wrap */}
                  <polygon
                    points={`${LFR.join()},${LRTR.join()},${LRBR.join()},${LFBR.join()}`}
                    fill="url(#wrapPatR)"
                    opacity="0.95"
                  />
                  {/* lid top wrap */}
                  <polygon
                    points={`${LTFL.join()},${LTFR.join()},${LTRTR.join()},${LTRL.join()}`}
                    fill="#f84444"
                    opacity="0.9"
                  />

                  {/* ── snowflake decorations (front face) ── */}
                  {[
                    [155, 320, 18],
                    [200, 375, 14],
                    [270, 340, 22],
                    [310, 290, 12],
                    [160, 250, 10],
                    [240, 410, 16],
                    [290, 390, 10],
                  ].map(([cx, cy, r], i) => (
                    <motion.path
                      key={i}
                      d={snowflakePath(cx, cy, r)}
                      stroke="rgba(255,255,255,0.55)"
                      strokeWidth="1.4"
                      fill="none"
                      strokeLinecap="round"
                      initial={{ opacity: 0, scale: 0.4 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.05 * i, duration: 0.4 }}
                      style={{ transformOrigin: `${cx}px ${cy}px` }}
                    />
                  ))}
                  {/* star sparkles */}
                  {[
                    [175, 380, 5],
                    [240, 310, 4],
                    [300, 370, 6],
                    [155, 290, 4],
                  ].map(([cx, cy, r], i) => (
                    <motion.path
                      key={`star-${i}`}
                      d={`M${cx},${cy - r} L${cx + 1.5},${cy - 1.5} L${cx + r},${cy} L${cx + 1.5},${cy + 1.5} L${cx},${cy + r} L${cx - 1.5},${cy + 1.5} L${cx - r},${cy} L${cx - 1.5},${cy - 1.5}Z`}
                      fill="rgba(255,255,255,0.60)"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.3 + 0.05 * i }}
                    />
                  ))}

                  {/* ── snowflakes on right face ── */}
                  {[
                    [345, 330, 12],
                    [370, 380, 9],
                  ].map(([cx, cy, r], i) => (
                    <motion.path
                      key={`rs-${i}`}
                      d={snowflakePath(cx, cy, r)}
                      stroke="rgba(255,255,255,0.35)"
                      strokeWidth="1.2"
                      fill="none"
                      strokeLinecap="round"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.4 + 0.06 * i }}
                    />
                  ))}

                  {/* ── snowflakes on lid top ── */}
                  {[
                    [200, 205, 10],
                    [240, 195, 7],
                    [270, 210, 8],
                  ].map(([cx, cy, r], i) => (
                    <motion.path
                      key={`lt-${i}`}
                      d={snowflakePath(cx, cy, r)}
                      stroke="rgba(255,255,255,0.45)"
                      strokeWidth="1.2"
                      fill="none"
                      strokeLinecap="round"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.5 + 0.06 * i }}
                    />
                  ))}
                </motion.g>
              )}
            </AnimatePresence>

            {/* ══════════════════════════════════════════════
                5.  RIBBON (gold vertical + horizontal)
            ══════════════════════════════════════════════ */}
            <AnimatePresence>
              {after(5) && (
                <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  {/* ── VERTICAL ribbon (front face) ── */}
                  <motion.rect
                    x={bx + fw / 2 - 10}
                    y={by - fh}
                    width="20"
                    height={fh}
                    fill="url(#ribbonV)"
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: 1 }}
                    style={{ transformOrigin: `${bx + fw / 2}px ${by - fh}px` }}
                    transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
                  />
                  {/* ── VERTICAL ribbon (right face, skewed) ── */}
                  <motion.polygon
                    points={`${FR[0]},${by - fh} ${FR[0] + 20},${by - fh} ${FR[0] + 20 + sx},${by - fh + sy} ${FR[0] + sx},${by - fh + sy}`}
                    fill="url(#ribbonV)"
                    opacity="0.7"
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: 1 }}
                    style={{ transformOrigin: `${FR[0] + 10}px ${by - fh}px` }}
                    transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
                  />
                  {/* ── HORIZONTAL ribbon (front face) ── */}
                  <motion.rect
                    x={bx}
                    y={by - fh / 2 - 10}
                    width={fw}
                    height="20"
                    fill="url(#ribbonH)"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    style={{ transformOrigin: `${bx}px ${by - fh / 2}px` }}
                    transition={{
                      duration: 0.42,
                      delay: 0.1,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  />
                  {/* ── HORIZONTAL ribbon (right face, skewed) ── */}
                  <motion.polygon
                    points={`${FR[0]},${by - fh / 2 - 10} ${RBR[0]},${by - fh / 2 - 10 + sy} ${RBR[0]},${by - fh / 2 + 10 + sy} ${FR[0]},${by - fh / 2 + 10}`}
                    fill="url(#ribbonH)"
                    opacity="0.7"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    style={{ transformOrigin: `${FR[0]}px ${by - fh / 2}px` }}
                    transition={{
                      duration: 0.42,
                      delay: 0.1,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  />

                  {/* ── LID RIBBON ── */}
                  {/* vertical on lid front */}
                  <motion.rect
                    x={bx + fw / 2 - 10}
                    y={by - fh - lidH}
                    width="20"
                    height={lidH + 4}
                    fill="url(#ribbonLidV)"
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: 1 }}
                    style={{
                      transformOrigin: `${bx + fw / 2}px ${by - fh - lidH}px`,
                    }}
                    transition={{
                      duration: 0.28,
                      delay: 0.04,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  />
                  {/* horizontal on lid front */}
                  <motion.rect
                    x={LFL[0]}
                    y={LFL[1] + lidH / 2 - 8}
                    width={LFR[0] - LFL[0]}
                    height="16"
                    fill="url(#ribbonLidH)"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    style={{
                      transformOrigin: `${LFL[0]}px ${LFL[1] + lidH / 2}px`,
                    }}
                    transition={{
                      duration: 0.28,
                      delay: 0.1,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  />
                  {/* vertical on lid top (across isometric top) */}
                  <motion.polygon
                    points={`
                      ${LTFL[0] + fw / 2 - 10},${LTFL[1]}
                      ${LTFL[0] + fw / 2 + 10},${LTFL[1]}
                      ${LTRL[0] + fw / 2 + 10 - 14},${LTRL[1]}
                      ${LTRL[0] + fw / 2 - 10 - 14},${LTRL[1]}
                    `}
                    fill="url(#ribbonLidV)"
                    opacity="0.9"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    style={{
                      transformOrigin: `${LTFL[0] + fw / 2}px ${(LTFL[1] + LTRL[1]) / 2}px`,
                    }}
                    transition={{
                      duration: 0.3,
                      delay: 0.08,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  />

                  {/* ══ BOW ══════════════════════════════════ */}
                  {/* Center of bow sits at top of lid */}
                  {(() => {
                    const bowCX = bx + fw / 2 + 10;
                    const bowCY = LFL[1] - 2;
                    return (
                      <>
                        {/* left loop */}
                        <motion.path
                          d={`
                            M${bowCX},${bowCY}
                            C${bowCX - 18},${bowCY - 18}
                              ${bowCX - 58},${bowCY - 54}
                              ${bowCX - 52},${bowCY - 26}
                            C${bowCX - 46},${bowCY - 8}
                              ${bowCX - 18},${bowCY - 6}
                              ${bowCX},${bowCY}Z
                          `}
                          fill="url(#bowLeft)"
                          stroke="rgba(80,0,0,0.25)"
                          strokeWidth="0.8"
                          initial={{ scale: 0, rotate: -15 }}
                          animate={{ scale: 1, rotate: 0 }}
                          style={{ transformOrigin: `${bowCX}px ${bowCY}px` }}
                          transition={{
                            delay: 0.14,
                            type: "spring",
                            stiffness: 260,
                            damping: 20,
                          }}
                        />
                        {/* left loop highlight */}
                        <motion.path
                          d={`M${bowCX - 8},${bowCY - 10} C${bowCX - 24},${bowCY - 30} ${bowCX - 42},${bowCY - 46} ${bowCX - 44},${bowCY - 30}`}
                          stroke="rgba(255,120,120,0.45)"
                          strokeWidth="3"
                          fill="none"
                          strokeLinecap="round"
                          initial={{ pathLength: 0, opacity: 0 }}
                          animate={{ pathLength: 1, opacity: 1 }}
                          transition={{ delay: 0.3, duration: 0.4 }}
                        />
                        {/* right loop */}
                        <motion.path
                          d={`
                            M${bowCX},${bowCY}
                            C${bowCX + 18},${bowCY - 18}
                              ${bowCX + 58},${bowCY - 54}
                              ${bowCX + 52},${bowCY - 26}
                            C${bowCX + 46},${bowCY - 8}
                              ${bowCX + 18},${bowCY - 6}
                              ${bowCX},${bowCY}Z
                          `}
                          fill="url(#bowRight)"
                          stroke="rgba(80,0,0,0.25)"
                          strokeWidth="0.8"
                          initial={{ scale: 0, rotate: 15 }}
                          animate={{ scale: 1, rotate: 0 }}
                          style={{ transformOrigin: `${bowCX}px ${bowCY}px` }}
                          transition={{
                            delay: 0.18,
                            type: "spring",
                            stiffness: 260,
                            damping: 20,
                          }}
                        />
                        {/* right loop highlight */}
                        <motion.path
                          d={`M${bowCX + 8},${bowCY - 10} C${bowCX + 24},${bowCY - 30} ${bowCX + 42},${bowCY - 46} ${bowCX + 44},${bowCY - 30}`}
                          stroke="rgba(255,120,120,0.40)"
                          strokeWidth="3"
                          fill="none"
                          strokeLinecap="round"
                          initial={{ pathLength: 0, opacity: 0 }}
                          animate={{ pathLength: 1, opacity: 1 }}
                          transition={{ delay: 0.35, duration: 0.4 }}
                        />
                        {/* left tail */}
                        <motion.path
                          d={`M${bowCX},${bowCY} C${bowCX - 20},${bowCY + 8} ${bowCX - 34},${bowCY + 28} ${bowCX - 22},${bowCY + 34}`}
                          stroke="#991010"
                          strokeWidth="13"
                          fill="none"
                          strokeLinecap="round"
                          initial={{ pathLength: 0 }}
                          animate={{ pathLength: 1 }}
                          transition={{ delay: 0.22, duration: 0.32 }}
                        />
                        {/* right tail */}
                        <motion.path
                          d={`M${bowCX},${bowCY} C${bowCX + 20},${bowCY + 8} ${bowCX + 34},${bowCY + 28} ${bowCX + 22},${bowCY + 34}`}
                          stroke="#991010"
                          strokeWidth="13"
                          fill="none"
                          strokeLinecap="round"
                          initial={{ pathLength: 0 }}
                          animate={{ pathLength: 1 }}
                          transition={{ delay: 0.26, duration: 0.32 }}
                        />
                        {/* center knot */}
                        <motion.ellipse
                          cx={bowCX}
                          cy={bowCY}
                          rx="15"
                          ry="12"
                          fill="url(#bowCenter)"
                          stroke="rgba(80,0,0,0.30)"
                          strokeWidth="0.8"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          style={{ transformOrigin: `${bowCX}px ${bowCY}px` }}
                          transition={{
                            delay: 0.28,
                            type: "spring",
                            stiffness: 320,
                            damping: 22,
                          }}
                        />
                        {/* knot highlight */}
                        <motion.ellipse
                          cx={bowCX - 2}
                          cy={bowCY - 3}
                          rx="5"
                          ry="4"
                          fill="rgba(255,160,160,0.35)"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: 0.38, duration: 0.3 }}
                        />
                      </>
                    );
                  })()}
                </motion.g>
              )}
            </AnimatePresence>

            {/* ══════════════════════════════════════════════
                6.  GREETING CARD (floats in upper-right)
            ══════════════════════════════════════════════ */}
            <AnimatePresence>
              {after(6) && (
                <motion.g
                  initial={{ opacity: 0, y: -110, rotate: 20 }}
                  animate={{ opacity: 1, y: 0, rotate: -9 }}
                  transition={{ type: "spring", stiffness: 95, damping: 16 }}
                  style={{ transformOrigin: "450px 230px" }}
                >
                  <rect
                    x="390"
                    y="200"
                    width="108"
                    height="70"
                    rx="8"
                    fill="rgba(0,0,0,0.08)"
                    transform="translate(2,3)"
                  />
                  <rect
                    x="390"
                    y="200"
                    width="108"
                    height="70"
                    rx="8"
                    fill="#fdf8ed"
                    stroke="#d9b256"
                    strokeWidth="1.6"
                  />
                  <path
                    d="M390,215 L444,245 L498,215"
                    fill="none"
                    stroke="#e8c880"
                    strokeWidth="1.2"
                  />
                  <text
                    x="444"
                    y="230"
                    textAnchor="middle"
                    fontSize="8.5"
                    fill="#8a5b10"
                    fontFamily="Georgia, serif"
                  >
                    Greeting Card
                  </text>
                  <line
                    x1="404"
                    y1="248"
                    x2="486"
                    y2="248"
                    stroke="#e8d5a0"
                    strokeWidth="0.8"
                  />
                  <text
                    x="444"
                    y="262"
                    textAnchor="middle"
                    fontSize="11"
                    fill="#5c3800"
                    fontFamily="Georgia, serif"
                    fontWeight="bold"
                  >
                    {recipient}
                  </text>
                </motion.g>
              )}
            </AnimatePresence>

            {/* ══════════════════════════════════════════════
                7.  LETTER (floats in upper-left)
            ══════════════════════════════════════════════ */}
            <AnimatePresence>
              {after(7) && (
                <motion.g
                  initial={{ opacity: 0, y: -120, x: -40, rotate: -12 }}
                  animate={{ opacity: 1, y: 0, x: 0, rotate: 6 }}
                  transition={{ type: "spring", stiffness: 90, damping: 16 }}
                  style={{ transformOrigin: "102px 268px" }}
                >
                  <rect
                    x="34"
                    y="228"
                    width="122"
                    height="82"
                    rx="9"
                    fill="rgba(0,0,0,0.09)"
                    transform="translate(2,3)"
                  />
                  <rect
                    x="34"
                    y="228"
                    width="122"
                    height="82"
                    rx="9"
                    fill="#fffef7"
                    stroke="#d6c7a5"
                    strokeWidth="1.4"
                  />
                  <path
                    d="M34,240 L95,278 L156,240"
                    fill="#f8f1e0"
                    stroke="#d6c7a5"
                    strokeWidth="1.2"
                  />
                  <text
                    x="95"
                    y="295"
                    textAnchor="middle"
                    fontSize="8.4"
                    fill="#6b7280"
                    fontFamily="Georgia, serif"
                  >
                    {letterSnippet}
                  </text>
                </motion.g>
              )}
            </AnimatePresence>

            {/* ══════════════════════════════════════════════
                CONFETTI + glow burst
            ══════════════════════════════════════════════ */}
            <AnimatePresence>
              {after(8) && (
                <motion.g>
                  <motion.ellipse
                    cx="270"
                    cy="300"
                    rx="200"
                    ry="140"
                    fill="rgba(249,178,79,0.14)"
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={{ opacity: 1, scale: 1.1 }}
                    transition={{ duration: 0.9, ease: "easeOut" }}
                  />
                </motion.g>
              )}
            </AnimatePresence>
          </svg>

          {/* React confetti (above SVG) */}
          <AnimatePresence>{burst && <ConfettiBurst />}</AnimatePresence>
        </div>
      </div>
    </div>
  );
}
