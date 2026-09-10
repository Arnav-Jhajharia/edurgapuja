/**
 * The lotus from the brand guide's decorative set.
 *
 * Used once in the console — in the rail's header and on the login card — and
 * nowhere else. The guide is explicit that decorative elements belong in
 * headers and special sections and should stay restrained, so this is the whole
 * of it rather than a motif sprinkled through the UI.
 */
export function Lotus({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <g fill="currentColor">
        {/* centre petal */}
        <path d="M16 4c2.6 3 3.9 6.1 3.9 9.3 0 3.2-1.3 6-3.9 8.4-2.6-2.4-3.9-5.2-3.9-8.4C12.1 10.1 13.4 7 16 4Z" />
        {/* inner pair */}
        <path d="M9.2 8.6c2.9 1.2 4.9 3 6 5.4 1.1 2.4 1.2 5-.1 7.8-2.9-.9-4.9-2.5-6.1-4.8-1.2-2.3-1.4-5.1-.4-8.4Z" opacity=".78" />
        <path d="M22.8 8.6c1 3.3.8 6.1-.4 8.4-1.2 2.3-3.2 3.9-6.1 4.8-1.3-2.8-1.2-5.4-.1-7.8 1.1-2.4 3.1-4.2 6.6-5.4Z" opacity=".78" />
        {/* outer pair */}
        <path d="M3.6 15.4c3.1-.1 5.6.6 7.4 2.1 1.8 1.5 2.9 3.7 3.3 6.7-3 .5-5.5 0-7.4-1.5-1.9-1.5-3.1-3.9-3.3-7.3Z" opacity=".55" />
        <path d="M28.4 15.4c-.2 3.4-1.4 5.8-3.3 7.3-1.9 1.5-4.4 2-7.4 1.5.4-3 1.5-5.2 3.3-6.7 1.8-1.5 4.3-2.2 7.4-2.1Z" opacity=".55" />
      </g>
      <path d="M11 26.5h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"
            opacity=".5" />
    </svg>
  );
}
