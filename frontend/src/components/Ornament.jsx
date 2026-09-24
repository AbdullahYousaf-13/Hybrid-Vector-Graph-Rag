import { cx } from "../utils/cx.js";

export function Divider({ className }) {
  return (
    <svg viewBox="0 0 320 24" className={cx("h-6", className)} aria-hidden="true" fill="none">
      <path
        d="M4 12 C40 12 60 4 92 12 C112 17 126 17 142 12"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M316 12 C280 12 260 4 228 12 C208 17 194 17 178 12"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path d="M160 4 L168 12 L160 20 L152 12 Z" fill="currentColor" />
      <circle cx="142" cy="12" r="1.8" fill="currentColor" />
      <circle cx="178" cy="12" r="1.8" fill="currentColor" />
      <circle cx="4" cy="12" r="1.6" fill="currentColor" />
      <circle cx="316" cy="12" r="1.6" fill="currentColor" />
    </svg>
  );
}

export function CornerFlourish({ className }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true" fill="none">
      <path
        d="M2 46 V14 C2 8 6 4 12 4 H46"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <path
        d="M8 40 V18 C8 14 11 11 15 11 H40"
        stroke="currentColor"
        strokeWidth="0.8"
        strokeLinecap="round"
        opacity="0.7"
      />
      <path
        d="M14 22 C14 17 17 15 22 15 M14 22 C16 26 20 26 22 22"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" />
    </svg>
  );
}

export function WaxSeal({ className }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <circle cx="16" cy="16" r="14" fill="#5b0000" />
      <circle cx="16" cy="16" r="14" fill="none" stroke="#e8c766" strokeWidth="1" opacity="0.7" />
      <circle cx="16" cy="16" r="10.5" fill="none" stroke="#e8c766" strokeWidth="0.8" opacity="0.5" />
      <path d="M18.5 8.5 L11 18h4.5L14 25l7.5-11h-4.5z" fill="#e8c766" />
    </svg>
  );
}
