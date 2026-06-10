/** @type {import('next').NextConfig} */
const nextConfig = {
  skipTrailingSlashRedirect: true,
  // Support alternate dev ports (e.g. 3002 for `make verify-mobile` with API on 8002)
  // and cross-origin access from 127.0.0.1 vs localhost during playwright/mobile checks.
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  async rewrites() {
    const configuredApiBaseUrl = (process.env.API_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    const apiBaseUrl = configuredApiBaseUrl.endsWith("/api") ? configuredApiBaseUrl : `${configuredApiBaseUrl}/api`;
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
