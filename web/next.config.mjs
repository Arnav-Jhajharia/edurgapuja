/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // `next build` and `next dev` both write to .next by default, so building
  // while the dev server is running corrupts its chunks and every page dies
  // with "__webpack_modules__[moduleId] is not a function". Giving the build
  // its own directory makes that impossible rather than merely unlikely.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // The API and the web tier are separate origins in production. Browser calls
  // are proxied through the pandal's own host so they are same-origin and CORS
  // never enters the picture (API contract §1).
  async rewrites() {
    const api = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${api}/api/v1/:path*` }];
  },
};
export default nextConfig;
