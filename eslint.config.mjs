import js from "@eslint/js";
import { parse } from "espree";
import globals from "globals";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = dirname(fileURLToPath(import.meta.url));

function collectJsFiles(relativeDir) {
  const absoluteDir = join(rootDir, relativeDir);
  return readdirSync(absoluteDir, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = join(relativeDir, entry.name);
    if (entry.isDirectory()) return collectJsFiles(relativePath);
    return entry.isFile() && entry.name.endsWith(".js") ? [relativePath] : [];
  });
}

function collectPatternNames(pattern, names) {
  if (!pattern) return;
  if (pattern.type === "Identifier") {
    names.push(pattern.name);
    return;
  }
  if (pattern.type === "RestElement") {
    collectPatternNames(pattern.argument, names);
    return;
  }
  if (pattern.type === "AssignmentPattern") {
    collectPatternNames(pattern.left, names);
    return;
  }
  if (pattern.type === "ArrayPattern") {
    pattern.elements.forEach((element) => collectPatternNames(element, names));
    return;
  }
  if (pattern.type === "ObjectPattern") {
    pattern.properties.forEach((property) => collectPatternNames(property.value ?? property.argument, names));
  }
}

function projectScriptDeclarations(relativePaths) {
  const declarationsByFile = new Map();
  for (const relativePath of relativePaths) {
    const declarations = {};
    const source = readFileSync(join(rootDir, relativePath), "utf8");
    const program = parse(source, { ecmaVersion: 2022, sourceType: "script" });
    for (const statement of program.body) {
      if (statement.type === "FunctionDeclaration" || statement.type === "ClassDeclaration") {
        if (statement.id) declarations[statement.id.name] = "writable";
        continue;
      }
      if (statement.type !== "VariableDeclaration") continue;
      const names = [];
      statement.declarations.forEach((declaration) => collectPatternNames(declaration.id, names));
      for (const name of names) {
        const mode = statement.kind === "const" ? "readonly" : "writable";
        if (declarations[name] !== "writable") declarations[name] = mode;
      }
    }
    declarationsByFile.set(relativePath, declarations);
  }
  return declarationsByFile;
}

function globalsForFile(relativePath, declarationsByFile) {
  const shared = { L: "readonly" };
  for (const [sourcePath, declarations] of declarationsByFile) {
    if (sourcePath === relativePath) continue;
    for (const [name, mode] of Object.entries(declarations)) {
      if (shared[name] !== "writable") shared[name] = mode;
    }
  }
  return { ...globals.browser, ...shared };
}

const webJsFiles = collectJsFiles("web");
const declarationsByFile = projectScriptDeclarations(webJsFiles);
const webRules = {
  ...js.configs.recommended.rules,
  "no-empty": ["error", { allowEmptyCatch: true }],
  "no-console": "off",
  "no-undef": "error",
  "no-unused-vars": [
    "error",
    {
      vars: "local",
      args: "after-used",
      argsIgnorePattern: "^_",
      caughtErrors: "all",
      caughtErrorsIgnorePattern: "^_",
      ignoreRestSiblings: true,
    },
  ],
};

export default [
  {
    ignores: ["analiza/**", "node_modules/**"],
  },
  ...webJsFiles.map((relativePath) => ({
    files: [relativePath],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: globalsForFile(relativePath, declarationsByFile),
    },
    rules: webRules,
  })),
];
