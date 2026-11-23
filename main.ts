// The Daily Compass — entry program.
//
// Copies the bundled poster (assets/poster.png, next to this program) to
// <output>/entry.png, where <output> is process.env.MAKEFUN_OUTPUT_DIR
// when set and /output otherwise. Deterministic: no network access, no
// clock, no randomness — the same bytes come out on every run.

import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const outputDir: string = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
const programDir: string = resolve(dirname(process.argv[1] ?? "."));
const source: string = join(programDir, "assets", "poster.png");
const target: string = join(outputDir, "entry.png");

mkdirSync(outputDir, { recursive: true });
copyFileSync(source, target);
