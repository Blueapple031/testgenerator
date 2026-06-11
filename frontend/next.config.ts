import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: frontendRoot,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
