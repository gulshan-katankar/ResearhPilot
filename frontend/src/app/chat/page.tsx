"use client";

import { useState, useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Upload, Bot, User, FileText, Loader2, X } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function ChatPage() {
  const [isIndexing, setIsIndexing] = useState(false);
  const [sources, setSources] = useState<{name: string}[]>([]);
  const [messages, setMessages] = useState<{role: 'user' | 'assistant', content: string}[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/sources")
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (data.sources) setSources(data.sources);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setIsIndexing(true);
      
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        });
        if (res.ok) {
          setSources(prev => {
            // Prevent duplicates in UI
            if (!prev.find(s => s.name === file.name)) {
              return [...prev, { name: file.name }];
            }
            return prev;
          });
        }
      } catch (err) {
        console.error(err);
      } finally {
        setIsIndexing(false);
        // Reset file input
        e.target.value = '';
      }
    }
  };

  const handleDeleteSource = async (filename: string) => {
    // Optimistically remove from UI to feel instant
    setSources(prev => prev.filter(s => s.name !== filename));
    try {
      await fetch(`/api/sources/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg }),
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, there was an error processing your request." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-background/50">
      <ScrollArea className="flex-1 p-4 md:p-6 lg:p-8">
        <div className="max-w-3xl mx-auto space-y-8 pb-20">
          
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center opacity-70">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-6">
                <Bot className="w-8 h-8 text-primary" />
              </div>
              <h2 className="text-2xl font-semibold mb-2">How can I help you research today?</h2>
              <p className="text-muted-foreground max-w-md">
                Upload a document to synthesize its contents, or ask a question about your existing knowledge base.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg, idx) => (
                <div key={idx} className="flex items-start gap-4">
                  <Avatar className={`w-8 h-8 border ${msg.role === 'user' ? 'border-border' : 'border-primary/20'}`}>
                    <AvatarFallback className={msg.role === 'user' ? 'bg-primary/10 text-primary' : 'bg-primary text-primary-foreground'}>
                      {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </AvatarFallback>
                  </Avatar>
                  <div className={`flex-1 p-4 text-sm shadow-sm ${
                    msg.role === 'user' 
                      ? 'bg-card border border-border/50 rounded-2xl rounded-tl-sm' 
                      : 'bg-primary/5 border border-primary/10 rounded-2xl rounded-tl-sm prose prose-sm max-w-none dark:prose-invert'
                  }`}>
                    {msg.role === 'user' ? (
                      msg.content
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex items-start gap-4">
                  <Avatar className="w-8 h-8 border border-primary/20">
                    <AvatarFallback className="bg-primary text-primary-foreground"><Bot className="w-4 h-4" /></AvatarFallback>
                  </Avatar>
                  <div className="flex items-center gap-2 px-4 py-3 bg-primary/5 border border-primary/10 rounded-2xl rounded-tl-sm text-sm shadow-sm text-primary">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Thinking...
                  </div>
                </div>
              )}
              <div ref={scrollRef} />
            </div>
          )}
          
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 md:p-6 bg-background/80 backdrop-blur-md border-t border-border absolute bottom-0 left-0 w-full">
        <div className="max-w-3xl mx-auto">
          
          {/* Sources and Indexing Status */}
          {(sources.length > 0 || isIndexing) && (
            <div className="flex flex-wrap gap-2 mb-3 px-2">
              {sources.map((source, i) => (
                <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary text-secondary-foreground text-xs rounded-full border border-border/50 group pr-1.5">
                  <FileText className="w-3.5 h-3.5" />
                  <span className="max-w-[150px] truncate">{source.name}</span>
                  <button 
                    onClick={() => handleDeleteSource(source.name)}
                    disabled={isIndexing}
                    className="ml-1 p-0.5 rounded-full hover:bg-destructive/10 hover:text-destructive opacity-50 group-hover:opacity-100 transition-all disabled:opacity-30"
                    title="Delete source"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {isIndexing && (
                <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-primary font-medium animate-pulse">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Indexing document...
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSend} className="flex items-end gap-2 relative">
            <label className="flex items-center justify-center h-12 w-12 rounded-full shrink-0 shadow-sm border border-input bg-background hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors" title="Upload Document">
              <Upload className="w-5 h-5 text-muted-foreground" />
              <input type="file" className="hidden" onChange={handleUpload} accept=".pdf,.txt,.docx" disabled={isIndexing || isLoading} />
            </label>
            <div className="flex-1 relative">
            <Input 
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={isLoading || isIndexing}
              placeholder="Ask anything or search your documents..." 
              className="h-12 pl-4 pr-12 rounded-full border-border bg-card shadow-sm text-base focus-visible:ring-primary"
            />
            <Button 
              type="submit"
              disabled={isLoading || !input.trim() || isIndexing}
              size="icon" 
              className="absolute right-1 top-1 h-10 w-10 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              <Send className="w-4 h-4 ml-0.5" />
            </Button>
          </div>
        </form>
        </div>
        <p className="text-center text-xs text-muted-foreground mt-3">
          ResearchPilot can make mistakes. Consider verifying important information.
        </p>
      </div>
    </div>
  );
}
