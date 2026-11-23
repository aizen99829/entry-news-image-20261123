// Entrypoint for the news-image-20261123 poster.
//
// Copies the pre-rendered poster (assets/poster.png) to entry.png in the
// output directory. Standard library only, no network access. The output
// directory comes from MAKEFUN_OUTPUT_DIR, defaulting to /output.
// The poster bytes are fixed, so every run writes identical output.
//
// The poster is The Daily Compass for Monday 23 November 2026: an
// art-led newspaper front page of 40 verified stories — three lead
// cards with large scene illustrations (Asia's markets sliding again
// as the AI rout rolls into Monday; Nepal's PM meeting Modi in Delhi;
// Russia starting to tow the drone-hit ship Sparta II), twelve
// illustrated panels with bold headlines, and a readable numbered
// index for the rest. Every story carries its source outlet; the
// key-numbers strip holds verified figures only; the regions bar is
// computed from the story list; and a DATE CHECK box fences off other
// days' news (COP31's collapse, the Kyiv strike and India's 720, all
// 22 Nov; the Sparta II hit, 'Chapo Isidro' and the Hormuz tankers,
// 20–21 Nov; GTA VI's release, 19 Nov).

import { copyFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const poster = fileURLToPath(new URL("./assets/poster.png", import.meta.url));
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";

mkdirSync(outDir, { recursive: true });
const target = join(outDir, "entry.png");
copyFileSync(poster, target);
console.log(target);
