import Link from "next/link";
import { useRouter } from "next/router";
import React, { useState } from "react";
import { motion } from "framer-motion";
import Logo from "./Logo";

const NAV = [
  { href: "/", title: "Field" },
  { href: "/framework", title: "Framework" },
  { href: "/tools", title: "Tools" },
  { href: "/papers", title: "Papers" },
];

const CustomLink = ({ href, title, className = "" }) => {
  const router = useRouter();
  const active = router.asPath === href || (href !== "/" && router.asPath.startsWith(href));
  return (
    <Link
      href={href}
      className={`relative rounded text-sm tracking-wide uppercase mono ${className}`}
    >
      <span className={active ? "text-primary" : "text-light hover:text-primary transition-colors"}>
        {title}
      </span>
      <span
        className={`absolute -bottom-1 left-0 h-px bg-primary transition-[width] duration-300 ${
          active ? "w-full" : "w-0"
        }`}
      />
    </Link>
  );
};

const MobileLink = ({ href, title, toggle }) => {
  const router = useRouter();
  const active = router.asPath === href;
  const handleClick = () => {
    toggle();
    router.push(href);
  };
  return (
    <button
      onClick={handleClick}
      className={`my-3 text-lg tracking-wide uppercase mono ${
        active ? "text-primary" : "text-light"
      }`}
    >
      {title}
    </button>
  );
};

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const toggle = () => setIsOpen((v) => !v);

  return (
    <header className="fixed top-0 left-0 right-0 z-20 flex items-center justify-between px-8 py-4 lg:px-6 border-b border-darkBorder bg-dark/70 backdrop-blur-md">
      {/* Mobile toggle */}
      <button
        type="button"
        className="hidden lg:flex flex-col items-center justify-center"
        aria-controls="mobile-menu"
        aria-expanded={isOpen}
        onClick={toggle}
      >
        <span className="sr-only">Open main menu</span>
        <span className={`bg-light block h-0.5 w-6 transition ${isOpen ? "rotate-45 translate-y-1" : "-translate-y-0.5"}`} />
        <span className={`bg-light block h-0.5 w-6 my-0.5 transition ${isOpen ? "opacity-0" : "opacity-100"}`} />
        <span className={`bg-light block h-0.5 w-6 transition ${isOpen ? "-rotate-45 -translate-y-1" : "translate-y-0.5"}`} />
      </button>

      {/* Desktop */}
      <div className="flex w-full items-center justify-between lg:hidden">
        <div className="flex items-center gap-3">
          <Logo />
          <span className="mono text-xs uppercase tracking-widest text-muted">
            olduvai · closed-circuit framework
          </span>
        </div>

        <nav className="flex items-center gap-6">
          {NAV.map((n) => (
            <CustomLink key={n.href} href={n.href} title={n.title} />
          ))}
        </nav>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="fixed top-16 left-4 right-4 z-30 flex flex-col items-center justify-center rounded-lg bg-darkSoft/95 backdrop-blur-md border border-darkBorder p-6"
        >
          {NAV.map((n) => (
            <MobileLink key={n.href} href={n.href} title={n.title} toggle={toggle} />
          ))}
        </motion.div>
      )}
    </header>
  );
};

export default Navbar;
