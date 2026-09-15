import type { NextConfig } from "next";

import pkg from "./package.json" with { type: "json" };

const nextConfig: NextConfig = {
  env: {
    // One source of truth for the version the footer prints. Hardcoding it in
    // a component is how a UI ends up claiming a release that was never cut.
    NEXT_PUBLIC_APP_VERSION: pkg.version,
  },
};

export default nextConfig;
