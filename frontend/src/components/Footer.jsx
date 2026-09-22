import HouseRibbon from "./HouseRibbon.jsx";

export default function Footer() {
  return (
    <footer className="mt-14">
      <HouseRibbon />
      <p className="legible px-4 py-5 text-center font-display text-[11px] tracking-[0.2em] text-gold-300 uppercase">
        Neo4j knowledge graph · Gemini embeddings &amp; generation · 7-book corpus
      </p>
    </footer>
  );
}
