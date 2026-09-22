import { useState } from "react";
import { DEFAULT_MODE } from "./constants.js";
import { useAsk } from "./hooks/useAsk.js";
import AnswerPanel from "./components/AnswerPanel.jsx";
import CategoryTabs from "./components/CategoryTabs.jsx";
import Footer from "./components/Footer.jsx";
import Header from "./components/Header.jsx";
import ModeSelector from "./components/ModeSelector.jsx";
import QuestionForm from "./components/QuestionForm.jsx";

export default function App() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState(DEFAULT_MODE);
  const { status, result, error, asked, elapsed, ask } = useAsk();

  const loading = status === "loading";

  // Suggestions only prefill the form — the user still presses Ask.
  function handlePick(suggestion) {
    setQuestion(suggestion.text);
    setMode(suggestion.mode);
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 sm:px-6">
        <div className="space-y-5 rounded-2xl border border-parchment-300 bg-parchment-50/70 p-4 shadow-sm sm:p-6">
          <CategoryTabs onPick={handlePick} disabled={loading} />
          <ModeSelector value={mode} onChange={setMode} disabled={loading} />
          <QuestionForm
            question={question}
            onQuestionChange={setQuestion}
            onSubmit={() => ask(question.trim(), mode)}
            loading={loading}
          />
        </div>

        <div className="mt-5">
          <AnswerPanel
            status={status}
            result={result}
            error={error}
            asked={asked}
            elapsed={elapsed}
          />
        </div>
      </main>

      <Footer />
    </div>
  );
}
