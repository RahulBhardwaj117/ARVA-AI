import { defineConfig, globalIgnores } from "eslint/config";
import tseslint from "typescript-eslint";

const eslintConfig = defineConfig([
  ...tseslint.configs.recommended,
  globalIgnores([
    "dist/**",
    ".next/**",
    ".wrangler/**",
    "coverage/**",
    "node_modules/**",
    "out/**",
    "build/**",
  ]),
]);

export default eslintConfig;
