import { headers } from "next/headers";

const SITE_DOMAIN = process.env.SITE_DOMAIN ?? "edurgapuja.app";

/**
 * Which pandal is this request for?
 *
 * In production the host is `<slug>.edurgapuja.app`. In development it is
 * `<slug>.localhost:3000`, which Chrome resolves without any hosts-file editing.
 * A bare `localhost` returns null and the index page is shown instead.
 */
export async function slugFromHost(): Promise<string | null> {
  const host = (await headers()).get("host")?.toLowerCase().split(":")[0] ?? "";

  for (const suffix of [`.${SITE_DOMAIN}`, ".localhost"]) {
    if (host.endsWith(suffix)) {
      const slug = host.slice(0, -suffix.length);
      return slug && slug !== "www" ? slug : null;
    }
  }
  return null;
}
