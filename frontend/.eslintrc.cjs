module.exports = {
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: "module",
    ecmaFeatures: {
      jsx: true
    }
  },
  plugins: ["@typescript-eslint", "react", "react-hooks"],
  extends: [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  settings: { react: { version: "detect" } },
  rules: {
    "react/prop-types": "off",
    "no-console": "warn",
    "react/no-unescaped-entities": "off",
    "no-unused-vars": "warn"
  }
};
