import { defineConfig } from "vitest/config";

// tests/scitex_ui/ts/*.test.ts are plain Node scripts (node --experimental-strip-types);
// vitest owns only tests/scitex_ui/vitest/.
export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/scitex_ui/vitest/**/*.test.ts"],
  },
});
