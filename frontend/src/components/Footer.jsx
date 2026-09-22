import HouseStripe from "./HouseStripe.jsx";

export default function Footer() {
  return (
    <footer className="mt-12">
      <HouseStripe className="h-1 opacity-70" />
      <p className="py-4 text-center text-xs text-ink-400">
        Neo4j knowledge graph · Gemini embeddings &amp; generation · 7-book corpus
      </p>
    </footer>
  );
}
