import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  /* Capture hygiene: no Next dev badge in screenshots or the demo video. Errors still surface. */
  devIndicators: false,
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
