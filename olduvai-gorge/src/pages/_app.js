import dynamic from "next/dynamic";
import Navbar from "@/components/Navbar";
import { BodyProvider } from "@/lib/bodyState";
import "@/styles/globals.css";
import { AnimatePresence } from "framer-motion";
import { Montserrat, JetBrains_Mono } from "next/font/google";
import Head from "next/head";
import { useRouter } from "next/router";

// The anatomy panel contains three.js content — load client-side only.
const BodyPanel = dynamic(
  () => import("@/components/anatomy/BodyPanel"),
  { ssr: false }
);

const montserrat = Montserrat({ subsets: ["latin"], variable: "--font-mont" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export default function App({ Component, pageProps }) {
  const router = useRouter();

  return (
    <>
      <Head>
        <title>Olduvai — Closed-Circuit Charge Framework</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta
          name="description"
          content="Interactive tools for the closed non-grounded charge circuit framework. Rendering is computing is observation."
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <BodyProvider>
        <main
          className={`${montserrat.variable} ${jetbrains.variable} font-mont dark bg-dark text-light w-full min-h-screen h-full`}
        >
          <Navbar />
          <AnimatePresence initial={false} mode="wait">
            <Component key={router.asPath} {...pageProps} />
          </AnimatePresence>
          <BodyPanel />
        </main>
      </BodyProvider>
    </>
  );
}
