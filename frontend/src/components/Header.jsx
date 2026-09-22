import HouseRibbon from "./HouseRibbon.jsx";
import { Divider } from "./Ornament.jsx";

export default function Header() {
  return (
    <header>
      <HouseRibbon className="pt-3" />

      <div className="mx-auto max-w-3xl px-4 pt-10 pb-8 text-center sm:px-6 sm:pt-14">
        <img
          src="/img/hogwarts-crest.webp"
          alt=""
          width="512"
          height="512"
          className="mx-auto h-28 w-28 drop-shadow-[0_10px_24px_rgba(0,0,0,0.7)] sm:h-36 sm:w-36"
        />

        <p className="legible mt-6 font-display text-[11px] font-semibold tracking-[0.35em] text-gold-300 uppercase">
          Hybrid Vector + Graph RAG
        </p>

        <h1 className="title-glow mt-5 font-title text-5xl leading-[1.1] text-gold-300 sm:text-6xl md:text-7xl">
          The Hogwarts Archive
        </h1>

        <Divider className="mx-auto mt-5 w-64 text-gold-400 sm:w-80" />

        <p className="legible mx-auto mt-5 max-w-xl font-body text-[17px] leading-relaxed text-parchment-300 italic">
          Seven volumes, one archive. Ask a question and choose how it should be answered -
          by searching the text, querying the knowledge graph, or both - and see exactly
          what the retriever found.
        </p>
      </div>
    </header>
  );
}
