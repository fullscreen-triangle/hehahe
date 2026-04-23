import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  // Single theme: always dark. The `dark` class is pinned on <html>.
  return (
    <Html lang="en" className="dark">
      <Head />
      <body className="bg-dark text-light">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
