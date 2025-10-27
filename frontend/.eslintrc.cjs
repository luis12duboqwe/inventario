module.exports = {
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint", "react", "react-hooks"],
  extends: [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  settings: { react: { version: "detect" } },
  rules: {
    "react/prop-types": "off",
    "no-console": "warn",
    "react/no-unescaped-entities": "off",
    "no-unused-vars": "warn"
  }
};
