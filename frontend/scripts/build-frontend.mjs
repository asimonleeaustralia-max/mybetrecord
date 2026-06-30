#!/usr/bin/env node
import * as esbuild from "esbuild";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "src");
const publicDir = join(root, "public");

const entries = [
  { in: join(src, "storage.js"), out: join(publicDir, "app", "storage.js") },
  { in: join(src, "i18n.js"), out: join(publicDir, "app", "i18n.js") },
  { in: join(src, "app.js"), out: join(publicDir, "app", "app.js") },
  { in: join(src, "marketing.js"), out: join(publicDir, "marketing.js") },
];

const shared = {
  bundle: false,
  minify: true,
  sourcemap: true,
  target: ["ios12", "chrome80", "firefox78", "safari12"],
  legalComments: "none",
};

async function build() {
  for (const { in: input, out: outfile } of entries) {
    mkdirSync(dirname(outfile), { recursive: true });
    await esbuild.build({ ...shared, entryPoints: [input], outfile });
  }
  console.log("frontend build ok");
}

const watch = process.argv.includes("--watch");
if (watch) {
  const ctx = await esbuild.context({
    ...shared,
    entryPoints: entries.map((e) => e.in),
    outdir: publicDir,
    outbase: src,
    entryNames: "[name]",
  });
  await ctx.watch();
  console.log("watching frontend/src …");
} else {
  await build();
}
