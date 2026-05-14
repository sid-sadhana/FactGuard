"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";

import { cn } from "@/lib/cn";

interface Props {
  score: number;
  size?: number;
  className?: string;
  label?: string;
}

function bandColor(score: number) {
  if (score >= 80) return "#5dd99a";
  if (score >= 60) return "#8DECB4";
  if (score >= 40) return "#fbbf24";
  return "#f87171";
}

export function ScoreRing({ score, size = 160, className, label = "Accuracy" }: Props) {
  const circleRef = useRef<SVGCircleElement | null>(null);
  const numberRef = useRef<HTMLSpanElement | null>(null);
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    const clamped = Math.max(0, Math.min(100, score));
    const dashOffset = circumference - (clamped / 100) * circumference;
    if (circleRef.current) {
      gsap.fromTo(
        circleRef.current,
        { strokeDashoffset: circumference },
        { strokeDashoffset: dashOffset, duration: 1.2, ease: "expo.out" },
      );
    }
    if (numberRef.current) {
      const obj = { val: 0 };
      gsap.to(obj, {
        val: clamped,
        duration: 1.2,
        ease: "expo.out",
        onUpdate: () => {
          if (numberRef.current) numberRef.current.textContent = Math.round(obj.val).toString();
        },
      });
    }
  }, [score, circumference]);

  const color = bandColor(score);

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#1c2238"
          strokeWidth={stroke}
        />
        <circle
          ref={circleRef}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          style={{ filter: `drop-shadow(0 0 8px ${color}40)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          ref={numberRef}
          className="text-3xl sm:text-4xl font-semibold"
          style={{ color }}
        >
          0
        </span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-fg-subtle">{label}</span>
      </div>
    </div>
  );
}
