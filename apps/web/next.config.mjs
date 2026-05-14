/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: { bodySizeLimit: "1gb" },
  },
  async rewrites() {
    const apiBase = process.env.API_BASE_URL || "http://localhost:8000";
    return [
      { source: "/api/proxy/:path*", destination: `${apiBase}/:path*` },
    ];
  },
};

export default nextConfig;
