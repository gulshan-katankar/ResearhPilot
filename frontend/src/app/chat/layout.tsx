import { Bot, LogOut, Settings, PanelLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { signout } from "@/app/(auth)/actions";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background font-sans">
      <header className="flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-2 font-bold text-lg">
          <Bot className="w-6 h-6 text-primary" />
          <span>ResearchPilot</span>
        </div>
        
        <Sheet>
          <SheetTrigger 
            render={<Button variant="ghost" size="icon" />}
          >
            <PanelLeft className="w-6 h-6" />
          </SheetTrigger>
          <SheetContent side="left" className="w-64 flex flex-col p-0">
            <SheetHeader className="p-6 border-b border-border text-left">
              <SheetTitle className="flex items-center gap-2 font-bold">
                <Bot className="w-5 h-5 text-primary" />
                ResearchPilot
              </SheetTitle>
            </SheetHeader>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {/* No recent chats loaded yet */}
            </div>
            
            <div className="p-4 border-t border-border space-y-2">
              <Button variant="ghost" className="w-full justify-start gap-2">
                <Settings className="w-4 h-4" />
                Settings
              </Button>
              <form action={signout}>
                <Button type="submit" variant="ghost" className="w-full justify-start gap-2 text-destructive hover:text-destructive hover:bg-destructive/10">
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </Button>
              </form>
            </div>
          </SheetContent>
        </Sheet>
      </header>

      <main className="flex-1 overflow-hidden relative">
        {children}
      </main>
    </div>
  );
}
