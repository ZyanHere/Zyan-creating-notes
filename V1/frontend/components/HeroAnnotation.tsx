// The margin annotation.
//
// A proof comes back with something scribbled next to it. This is that: the
// shape of what the product does, written in the margin rather than stated as
// a feature list — Ideas → Notes → Progress.
//
// Inline SVG rather than a script webfont: the handwritten quality here is in
// the *arrows and the swoosh*, not in the letterforms, and drawing them costs
// nothing while a display face for three words would add a build-time network
// dependency for decoration. The words themselves are the app's italic serif
// on a slight rotation, which reads as written-by-hand without pretending to
// be handwriting.
//
// Decorative in the strict sense — it states nothing the page does not say
// elsewhere — so it is hidden from assistive technology entirely.

export function HeroAnnotation() {
  return (
    <div aria-hidden className="pointer-events-none select-none">
      <div className="relative font-[family-name:var(--font-serif)] italic leading-none text-[color:var(--muted)]">
        <span className="block -rotate-[7deg] text-[0.95rem]">Ideas</span>
        <span className="mt-2 block translate-x-5 -rotate-[4deg] text-[0.95rem]">
          <Arrow /> Notes
        </span>
        <span className="mt-2 block translate-x-10 -rotate-[1deg] text-[0.95rem]">
          <Arrow /> Progress
        </span>

        {/* The underline swoosh, drawn rather than typed — a straight rule
            would read as a border, and this has to read as a pen stroke. */}
        <svg
          viewBox="0 0 120 14"
          className="mt-1.5 h-3.5 w-[7.5rem] translate-x-3 text-[color:var(--accent)]"
          fill="none"
        >
          <path
            d="M2 9C22 3.5 47 1.6 71 3.2c14 1 26 3.4 47 7.6"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            opacity="0.75"
          />
        </svg>
      </div>

      <div className="mt-7">
        <span className="block h-px w-6 bg-[color:var(--line-strong)]" />
        <p className="mt-2.5 font-[family-name:var(--font-serif)] text-[0.9rem] italic leading-6 text-[color:var(--muted)]">
          Same idea.
          <br />
          Higher standards.
        </p>
      </div>
    </div>
  );
}

/** A drawn arrow. The typographic → is too even to sit beside rotated script. */
function Arrow() {
  return (
    <svg
      viewBox="0 0 22 10"
      className="mr-1 inline-block h-2.5 w-5 text-[color:var(--soft)]"
      fill="none"
    >
      <path
        d="M1 5.2C6 5 12 4.7 20 4.6"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <path
        d="M16.2 1.8 20.4 4.6 16.4 7.8"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
