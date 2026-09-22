import { useState } from "react";
import { DEFAULT_MODE } from "./constants.js";
import { useAsk } from "./hooks/useAsk.js";
import AnswerPanel from "./components/AnswerPanel.jsx";
import CategoryTabs from "./components/CategoryTabs.jsx";
import Footer from "./components/Footer.jsx";
import Header from "./components/Header.jsx";
import ModeSelector from "./components/ModeSelector.jsx";
import Panel from "./components/Panel.jsx";
import QuestionForm from "./components/QuestionForm.jsx";

export default function App() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState(DEFAULT_MODE);
  const { status, result, error, asked, elapsed, ask } = useAsk();

  const loading = status === "loading";

  // Suggestions only prefill the form; the user still presses Ask.
  function handlePick(suggestion) {
    setQuestion(suggestion.text);
    setMode(suggestion.mode);
  }

  return (
    <>
      <div className="backdrop" aria-hidden="true">
        <div className="backdrop-photo" />
        <div className="backdrop-vignette" />
        <div className="candle candle-1" />
        <div className="candle candle-2" />
        <div className="candle candle-3" />
      </div>

      <div className="flex min-h-screen flex-col">
        <Header />

        <main className="mx-auto w-full max-w-3xl flex-1 px-4 sm:px-6">
          <Panel className="space-y-6">
            <CategoryTabs onPick={handlePick} disabled={loading} />
            <ModeSelector value={mode} onChange={setMode} disabled={loading} />
            <QuestionForm
              question={question}
              onQuestionChange={setQuestion}
              onSubmit={() => ask(question.trim(), mode)}
              loading={loading}
            />
          </Panel>

          <div className="mt-6">
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
    </>
  );
}
