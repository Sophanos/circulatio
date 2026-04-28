import Link from "next/link"

const navItems = [
  { href: "/capture/new", label: "Capture" },
  { href: "/artifacts/ritual-river-gate", label: "Ritual" },
  { href: "/artifacts/broadcast-myth-weather-0422", label: "Broadcast" },
  { href: "/artifacts/cinema-river-gate", label: "Cinema" },
  { href: "/artifacts/weekly-ritual-dry-run", label: "Manifest" }
]

export function TopNav() {
  return (
    <header className="sticky top-0 z-50 px-4 py-4 sm:px-6">
      <nav className="floating-nav mx-auto flex max-w-[1440px] items-center justify-between rounded-full px-4 py-3 sm:px-6">
        <Link href="/" className="text-sm font-medium tracking-[0.26em] uppercase text-graphite-950">
          Hermes Rituals
        </Link>
        <div className="hidden items-center gap-5 md:flex">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} className="eyebrow-link">
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  )
}
