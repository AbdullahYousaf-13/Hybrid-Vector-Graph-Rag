import { useLayoutEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import { MAX_QUESTION_LENGTH } from "../constants.js";
import { WaxSeal } from "./Ornament.jsx";
import { cx } from "../utils/cx.js";

const MAX_VISIBLE_LINES = 2;

export default function QuestionForm({ question, onQuestionChange, onSubmit, loading }) {
  const trimmed = question.trim();
  const tooLong = question.length > MAX_QUESTION_LENGTH;
  const canSubmit = trimmed.length > 0 && !tooLong && !loading;
  const textareaRef = useRef(null);

  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    const style = getComputedStyle(el);
    const lineHeight = parseFloat(style.lineHeight);
    const chrome =
      parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) +
      parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
    const maxHeight = lineHeight * MAX_VISIBLE_LINES + chrome;
    el.style.height = "auto";
    const needed = el.scrollHeight + parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
    el.style.height = `${Math.min(needed, maxHeight)}px`;
    el.style.overflowY = needed > maxHeight ? "auto" : "hidden";
  }, [question]);

  function handleSubmit(event) {
    event.preventDefault();
    if (canSubmit) onSubmit();
  }

  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && canSubmit) {
      event.preventDefault();
      onSubmit();
    }
  }

  const kbd =
    "rounded-sm border border-gold-400/25 bg-white/[0.06] px-1 py-0.5 font-sans text-xs text-parchment-200";

  return (
    <form onSubmit={handleSubmit} className="min-w-0">
      <label
        htmlFor="question"
        className="mb-2.5 block font-display text-[11px] font-semibold tracking-[0.2em] text-gold-400/85 uppercase"
      >
        Your question
      </label>

      <textarea
        id="question"
        ref={textareaRef}
        rows={1}
        value={question}
        maxLength={MAX_QUESTION_LENGTH}
        disabled={loading}
        onChange={(event) => onQuestionChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="e.g. What does the invisibility cloak do?"
        className={cx(
          "gold-scroll block w-full resize-none rounded-sm border border-gold-400/25 bg-night-950/60 px-4 py-2.5 text-lg text-parchment-50 transition",
          "shadow-[inset_0_2px_10px_rgba(0,0,0,0.45)]",
          "placeholder:text-mist/60 placeholder:italic",
          "focus:border-gold-400/70 focus:ring-2 focus:ring-gold-400/30 focus:outline-none",
          "disabled:opacity-70"
        )}
      />

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-mist">
          <kbd className={kbd}>Ctrl</kbd> + <kbd className={kbd}>Enter</kbd> to ask ·{" "}
          {question.length}/{MAX_QUESTION_LENGTH} characters
        </p>

        <button
          type="submit"
          disabled={!canSubmit}
          className={cx(
            "inline-flex items-center gap-2.5 rounded-sm border border-gold-400/50 bg-gryffindor py-2 pr-5 pl-2.5 font-display text-[13px] font-bold tracking-[0.14em] text-gold-300 uppercase transition",
            "shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_8px_20px_-8px_rgba(0,0,0,0.8),0_0_24px_-8px_rgba(211,166,37,0.35)]",
            "hover:border-gold-300/80 hover:bg-[#8a0002]",
            "focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:ring-offset-2 focus-visible:ring-offset-night-900 focus-visible:outline-none",
            "disabled:cursor-not-allowed disabled:opacity-45 disabled:shadow-none"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="size-6 animate-spin" aria-hidden="true" />
              Asking…
            </>
          ) : (
            <>
              <WaxSeal className="size-6 drop-shadow" />
              Ask
            </>
          )}
        </button>
      </div>
    </form>
  );
}
