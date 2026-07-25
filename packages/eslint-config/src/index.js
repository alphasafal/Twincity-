/**
 * Minimal shared ESLint baseline for TwinPilot workspaces.
 * Apps using next/core-web-vitals can extend that instead.
 */
module.exports = {
  root: false,
  ignorePatterns: ["node_modules/", "dist/", ".next/", "coverage/"],
  rules: {
    "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "no-console": ["warn", { allow: ["warn", "error"] }],
  },
};
