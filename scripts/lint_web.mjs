import { spawnSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = dirname(dirname(fileURLToPath(import.meta.url)));
const eslintBin = join(rootDir, "node_modules", ".bin", process.platform === "win32" ? "eslint.cmd" : "eslint");

if (!existsSync(eslintBin)) {
  console.error("Local ESLint is not installed. Run `npm install` before `npm run lint:web`.");
  process.exit(1);
}

function collectJsFiles(relativeDir) {
  const absoluteDir = join(rootDir, relativeDir);
  return readdirSync(absoluteDir, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = join(relativeDir, entry.name);
    if (entry.isDirectory()) return collectJsFiles(relativePath);
    return entry.isFile() && entry.name.endsWith(".js") ? [relativePath] : [];
  });
}

const jsFiles = collectJsFiles("web");

const result = spawnSync(eslintBin, jsFiles, {
  cwd: rootDir,
  stdio: "inherit",
});

process.exit(result.status ?? 1);
