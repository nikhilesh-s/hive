'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const TABS: [string, string][] = [
  ['/experimental/live', 'Live extraction'],
  ['/experimental/ask', 'Ask the evidence'],
  ['/experimental/densitometry', 'Densitometry'],
];

// Sub-navigation shared by the experimental pages. Everything under it is
// labelled experimental and kept apart from the reviewed beta surfaces.
export default function ExperimentalNav() {
  const path = usePathname();
  return (
    <nav className="hb-exp-nav" aria-label="Experimental features">
      {TABS.map(([href, label]) => (
        <Link key={href} href={href} className={path === href ? 'is-active' : ''}>{label}</Link>
      ))}
    </nav>
  );
}
