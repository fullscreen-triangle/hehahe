import Link from "next/link";
import React from "react";

/**
 * Brand mark — a ring that hints at a closed non-grounded circuit:
 * the charge path has no ground, only recurrence.
 */
const Logo = () => {
  return (
    <Link
      href="/"
      aria-label="Olduvai — home"
      className="flex items-center justify-center rounded-full"
    >
      <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="lg-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#58E6D9" stopOpacity="0.9" />
            <stop offset="60%" stopColor="#B63E96" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#0a0a0f" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="20" cy="20" r="9" fill="url(#lg-core)" />
        <circle cx="20" cy="20" r="14" fill="none" stroke="#58E6D9" strokeOpacity="0.6" strokeWidth="1" />
        <circle cx="20" cy="20" r="18" fill="none" stroke="#B63E96" strokeOpacity="0.3" strokeWidth="1" />
      </svg>
    </Link>
  );
};

export default Logo;
