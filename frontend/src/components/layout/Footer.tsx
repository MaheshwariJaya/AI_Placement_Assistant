import React from 'react';
import { Layers, Database, Cpu, Lock } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 mt-auto transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-xs text-slate-500 dark:text-slate-400">
          <div>
            <div className="font-semibold text-slate-800 dark:text-slate-200 mb-2">Architectural Blueprint</div>
            <p className="leading-relaxed">
              Modular Monolithic engine integrating deterministic eligibility rules and weighted compatibility scoring.
            </p>
          </div>
          <div>
            <div className="font-semibold text-slate-800 dark:text-slate-200 mb-2">Technology Stack</div>
            <ul className="space-y-1">
              <li className="flex items-center gap-1.5"><Layers className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" /> React 18 + Vite + Tailwind</li>
              <li className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" /> FastAPI + Async SQLAlchemy</li>
              <li className="flex items-center gap-1.5"><Database className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" /> PostgreSQL 16 + Alembic</li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-slate-800 dark:text-slate-200 mb-2">AI Abstraction Layer</div>
            <p className="leading-relaxed">
              Unified interface supporting Google Gemini, OpenAI, and deterministic offline mock mode without silent fallbacks.
            </p>
          </div>
          <div>
            <div className="font-semibold text-slate-800 dark:text-slate-200 mb-2">Security & Privacy</div>
            <p className="leading-relaxed flex items-center gap-1">
              <Lock className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 inline shrink-0" />
              Private server resume storage outside public web root with magic-byte validation.
            </p>
          </div>
        </div>
        <div className="pt-6 mt-6 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
          <div>AI-Powered Placement Intelligence System &copy; 2026. All rights reserved.</div>
          <div className="mt-2 sm:mt-0">Live PostgreSQL & AI Intelligence Platform</div>
        </div>
      </div>
    </footer>
  );
};

