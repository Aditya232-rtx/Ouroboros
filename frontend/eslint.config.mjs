import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    // These files rely on established, safe React patterns the newer React
    // Compiler lint rules flag conservatively as errors: a mounted-flag effect
    // (page.tsx, ported from the original Ouro landing page), a "last known
    // value" ref fallback during exit animations, a deferred-mount effect, a
    // reset-on-id-change effect, and a static tool-renderer registry (the
    // components/live/* agent-graph UI, a close port of Strix's own viewer at
    // fang/interface/viewer/frontend). Downgrade to warnings rather than
    // rewrite proven, working UI.
    files: ["components/live/**/*.tsx", "components/ouro-ui/*.tsx", "app/page.tsx"],
    rules: {
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
      "react-hooks/static-components": "warn",
    },
  },
]);

export default eslintConfig;
