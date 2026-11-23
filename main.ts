// Copies assets/poster.png to <output>/entry.png and verifies the copy matches the source byte size.
import * as fs from "node:fs";
import * as path from "node:path";

const programDir = path.dirname(path.resolve(process.argv[1]));
const sourcePath = path.join(programDir, "assets", "poster.png");
const outputDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
const destinationPath = path.join(outputDir, "entry.png");

fs.mkdirSync(outputDir, { recursive: true });
fs.copyFileSync(sourcePath, destinationPath);

const sourceSize = fs.statSync(sourcePath).size;
const destinationSize = fs.statSync(destinationPath).size;

if (destinationSize !== sourceSize) {
  throw new Error(
    `Copy integrity check failed: source is ${sourceSize} bytes but destination is ${destinationSize} bytes (${destinationPath})`
  );
}
