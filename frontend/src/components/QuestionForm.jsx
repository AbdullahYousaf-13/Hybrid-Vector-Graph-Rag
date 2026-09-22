import { Loader2, Send } from "lucide-react";
import { MAX_QUESTION_LENGTH } from "../constants.js";
import { cx } from "../utils/cx.js";

export default function QuestionForm({ question, onQuestionChange, onSubmit, loading }) {
  const trimmed = question.trim();
  const tooLong = question.length > MAX_QUESTION_LENGTH;
  const canSubmit = trimmed.length > 0 && !tooLong && !loading;

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

  return (
    <form onSubmit={handleSubmit} className="min-w-0">
      <label htmlFor="question" className="sr-only">
        Your question
      </label>

      <textarea
        id="question"
        rows={3}
        value={question}
        maxLength={MAX_QUESTION_LENGTH}
        disabled={loading}
        onChange={(event) => onQuestionChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="e.g. What does the invisibility cloak do?"
        className={cx(
          "w-full resize-y rounded-xl border border-parchment-300 bg-parchment-50 px-4 py-3 text-lg text-ink-900 shadow-inner transition",
          "placeholder:text-ink-400/80",
          "focus:border-gold-400 focus:ring-2 focus:ring-gold-400/40 focus:outline-none",
          "disabled:opacity-70"
        )}
      />

      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-ink-400">
          <kbd className="rounded border border-parchment-300 bg-parchment-200 px-1 py-0.5 font-sans">
            Ctrl
          </kbd>{" "}
          +{" "}
          <kbd className="rounded border border-parchment-300 bg-parchment-200 px-1 py-0.5 font-sans">
            Enter
          </kbd>{" "}
          to ask · {question.length}/{MAX_QUESTION_LENGTH} characters
        </p>

        <button
          type="submit"
          disabled={!canSubmit}
          className={cx(
            "inline-flex items-center gap-2 rounded-xl border border-gryffindor bg-gryffindor px-5 py-2.5 font-display text-sm font-semibold tracking-wide text-hufflepuff shadow-sm transition",
            "hover:bg-gryffindor/90 focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:ring-offset-2 focus-visible:ring-offset-parchment-100 focus-visible:outline-none",
            "disabled:cursor-not-allowed disabled:opacity-50"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Asking…
            </>
          ) : (
            <>
              <Send className="size-4" aria-hidden="true" />
              Ask
            </>
          )}
        </button>
      </div>
    </form>
  );
}
