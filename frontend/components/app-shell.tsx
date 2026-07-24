import Link from "next/link";
import type { ReactNode } from "react";
import { Icon } from "./icons";
import { getAvailableProducts } from "@/lib/product/product-api";

type NavigationItem = {
  href: string;
  label: string;
  icon: "overview" | "nameplate" | "technical" | "documents" | "upload";
  admin?: boolean;
};

const navigation: NavigationItem[] = [
  { href: "/", label: "Overview", icon: "overview" },
  { href: "/digital-nameplate", label: "Digital Nameplate", icon: "nameplate" },
  { href: "/technical-data", label: "Technical Data", icon: "technical" },
  { href: "/documents", label: "Documents", icon: "documents" },
  { href: "/admin-upload", label: "Admin Upload", icon: "upload", admin: true },
];

export async function AppShell({ children }: { children: ReactNode }) {
  const projects = await getAvailableProducts().catch(() => []);
  const query = (id: string) => `?aas=${encodeURIComponent(id)}`;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="AAS DPP home">
          <span className="brand-mark">A</span>
          <span><strong>AAS DPP</strong><small>Digital Product Passport</small></span>
        </Link>
        <nav className="desktop-nav" aria-label="Product passport">
          {projects.map((project, index) => (
            <Link className={`nav-link${index === 0 ? " active" : ""}`} href={`/${query(project.id)}`} key={project.id}>
              <Icon name="overview" />
              <span>{project.name}</span>
            </Link>
          ))}
          {navigation.map((item) => {
            const href = projects[0] ? `${item.href}${query(projects[0].id)}` : item.href;
            return (
              <Link className="nav-link" href={href} key={item.href}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.admin && <span className="admin-chip">Admin</span>}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" />
          <span><strong>Live AAS workspace</strong><small>Public passport data</small></span>
        </div>
      </aside>

      <header className="mobile-header">
        <Link className="mobile-brand" href="/"><span className="brand-mark">A</span><strong>AAS DPP</strong></Link>
        <span className="demo-pill">Live</span>
      </header>

      <main className="main-content">{children}</main>

      <nav className="mobile-nav" aria-label="Product passport">
          {navigation.map((item) => {
            const href = projects[0] ? `${item.href}${query(projects[0].id)}` : item.href;
            return (
              <Link className="" href={href} key={item.href} aria-label={item.label}>
              <Icon name={item.icon} />
              <span>{item.label.replace("Digital ", "").replace("Technical ", "")}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
