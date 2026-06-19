"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ArrowRight, Bot, BookOpen, BrainCircuit } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col font-sans">
      {/* Navigation */}
      <header className="px-6 lg:px-12 py-4 flex items-center justify-between fixed top-0 w-full bg-background/40 backdrop-blur-md z-50 border-b border-border/20 transition-all">
        <div className="flex items-center gap-2 font-bold text-xl text-foreground">
          <Bot className="w-6 h-6 text-primary" />
          <span>ResearchPilot</span>
        </div>
        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
          <Link href="#product" className="hover:text-primary transition-colors">Products</Link>
          <Link href="#solutions" className="hover:text-primary transition-colors">Solutions</Link>
          <Link href="#resources" className="hover:text-primary transition-colors">Resources</Link>
          <Link href="#pricing" className="hover:text-primary transition-colors">Pricing</Link>
        </nav>
        <div className="flex items-center gap-4">
          <Link href="/sign-in" className="hidden md:block text-sm font-medium hover:text-primary transition-colors">
            Sign In
          </Link>
          <Link href="/sign-up" passHref>
            <Button className="rounded-full px-6 bg-primary text-primary-foreground hover:bg-primary/90 transition-transform active:scale-95 shadow-lg shadow-primary/20">
              Get Started
            </Button>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center">
        {/* Hero Section with Full Background Video */}
        <section className="relative w-full min-h-[85vh] flex flex-col items-center justify-center text-center px-6 py-24 overflow-hidden">
          {/* Background Video */}
          <div className="absolute inset-0 w-full h-full z-0">
            <video 
              autoPlay 
              loop 
              muted 
              playsInline 
              className="w-full h-full object-cover"
            >
              <source src="/middle_animation.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            {/* Very thin white cloth overlay to blend with light theme */}
            <div className="absolute inset-0 bg-background/80 backdrop-blur-[1px]" />
            {/* Bottom gradient to seamlessly blend into the next section */}
            <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-background to-transparent" />
          </div>

          {/* Hero Content */}
          <div className="relative z-10 flex flex-col items-center w-full max-w-4xl mx-auto">
            <motion.h1 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-5xl md:text-7xl font-extrabold tracking-tight text-foreground max-w-4xl"
            >
              The future of research is <span className="font-serif italic text-primary">human + AI</span>
            </motion.h1>
            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl font-medium"
            >
              We help you synthesize massive amounts of data, map connections across papers, and uncover insights to thrive in a GenAI world.
            </motion.p>
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="mt-10"
            >
              <Link href="/sign-up" passHref>
                <Button size="lg" className="rounded-full px-8 text-lg h-14 bg-foreground text-background hover:bg-foreground/90 shadow-xl shadow-foreground/10 group">
                  Join The Community
                  <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
            </motion.div>
          </div>
        </section>

        {/* Product Sections */}
        <section id="product" className="w-full max-w-7xl mx-auto px-6 py-24 md:py-32 flex flex-col gap-32">
          {/* Feature 1 */}
          <div className="flex flex-col md:flex-row items-center gap-12 md:gap-24">
            <div className="flex-1 space-y-6">
              <div className="w-12 h-12 rounded-2xl bg-primary/20 flex items-center justify-center text-primary mb-6">
                <BookOpen className="w-6 h-6" />
              </div>
              <h2 className="text-3xl md:text-5xl font-bold text-foreground leading-tight">
                Analyze Papers Instantly
              </h2>
              <p className="text-lg text-muted-foreground">
                Upload massive PDFs and let our Retrieval-Augmented Generation (RAG) engine extract exactly what you need. Stop skimming and start synthesizing.
              </p>
              <Button variant="outline" className="rounded-full mt-4">Learn More</Button>
            </div>
            <div className="flex-1 w-full aspect-square md:aspect-video rounded-3xl bg-secondary relative overflow-hidden flex items-center justify-center">
              <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=1200" alt="Dashboard visualization" className="w-full h-full object-cover" />
            </div>
          </div>

          {/* Feature 2 */}
          <div className="flex flex-col md:flex-row-reverse items-center gap-12 md:gap-24">
            <div className="flex-1 space-y-6">
              <div className="w-12 h-12 rounded-2xl bg-primary/20 flex items-center justify-center text-primary mb-6">
                <BrainCircuit className="w-6 h-6" />
              </div>
              <h2 className="text-3xl md:text-5xl font-bold text-foreground leading-tight">
                Deep Dive with AI
              </h2>
              <p className="text-lg text-muted-foreground">
                Chat intelligently with your documents. Ask complex questions and get accurate, cited answers backed by your own curated knowledge base.
              </p>
              <Button variant="outline" className="rounded-full mt-4">See in Action</Button>
            </div>
            <div className="flex-1 w-full aspect-square md:aspect-video rounded-3xl bg-accent relative overflow-hidden flex items-center justify-center">
              <img src="https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?auto=format&fit=crop&q=80&w=1200" alt="Chat interface" className="w-full h-full object-cover" />
            </div>
          </div>
        </section>
      </main>

      <footer className="w-full border-t border-border bg-background py-12 px-6 flex flex-col md:flex-row justify-between items-center text-muted-foreground text-sm">
        <p>© 2026 ResearchPilot. All rights reserved.</p>
        <div className="flex gap-6 mt-4 md:mt-0">
          <Link href="#" className="hover:text-primary">Privacy Policy</Link>
          <Link href="#" className="hover:text-primary">Terms of Service</Link>
        </div>
      </footer>
    </div>
  );
}
