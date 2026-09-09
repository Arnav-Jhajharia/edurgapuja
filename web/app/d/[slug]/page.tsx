import { notFound, redirect } from "next/navigation";

import { slugFromHost } from "@/lib/host";

/**
 * The short form of a shared donation link.
 *
 * On a pandal's own subdomain the slug is already in the host, so repeating it
 * in the path gives you `some-pandal.edurgapuja.app/d/some-pandal/gqvNj6F3j5`
 * — which is what somebody has to paste into WhatsApp. The long form still
 * works, because links already shared cannot be taken back.
 *
 * The folder is `[slug]` to match its parent segment — Next refuses two
 * different dynamic names at the same position — but the value here is a token.
 */
export default async function ShortDonationLink(
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug: token } = await params;
  const pandal = await slugFromHost();

  // On a bare host there is no pandal in the URL at all, and a token alone
  // cannot find one: tokens are only unique within a pandal.
  if (!pandal) notFound();

  redirect(`/d/${pandal}/${token}`);
}
