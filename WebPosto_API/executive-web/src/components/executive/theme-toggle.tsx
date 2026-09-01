"use client";
import { Moon, Sun } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
export function ThemeToggle() { const [dark, setDark] = useState(false); return <Button className="size-9 bg-muted p-0 text-foreground" onClick={() => { document.documentElement.classList.toggle("dark"); setDark(v => !v); }} aria-label="Alternar tema">{dark ? <Sun size={16}/> : <Moon size={16}/>}</Button>; }
