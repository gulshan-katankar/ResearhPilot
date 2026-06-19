import Link from "next/link";
import { Bot } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col font-sans">
      <header className="px-6 py-6 absolute top-0 left-0 w-full z-10">
        <Link href="/" className="flex items-center gap-2 font-bold text-xl text-foreground w-fit hover:opacity-80 transition-opacity">
          <Bot className="w-6 h-6 text-primary" />
          <span>ResearchPilot</span>
        </Link>
      </header>
      <main className="flex-1 flex items-center justify-center p-6 relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/5 rounded-full blur-[100px] pointer-events-none" />
        
        <div className="relative z-10 w-full max-w-md">
          {children}
        </div>
      </main>
    </div>
  );
}
