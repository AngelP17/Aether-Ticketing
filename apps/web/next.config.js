/** @type {import('next').NextConfig} */
const nextConfig = {
  skipTrailingSlashRedirect: true,
  // Support alternate dev ports (e.g. 3002 for `make verify-mobile` with API on 8002)
  // and cross-origin access from 127.0.0.1 vs localhost during playwright/mobile checks.
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  async rewrites() {
    const apiBaseUrl = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
