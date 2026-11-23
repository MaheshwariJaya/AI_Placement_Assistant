import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Server,
  ShieldCheck,
  ArrowRight,
  GraduationCap,
  Briefcase,
  Users
} from 'lucide-react';
import { Navbar } from '../components/layout/Navbar';
import { Footer } from '../components/layout/Footer';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { healthApi } from '../services/api';
import { HealthLiveResponse, HealthReadyResponse } from '../types';

export const LandingPage: React.FC = () => {
  const [live, setLive] = useState<HealthLiveResponse | null>(null);
  const [ready, setReady] = useState<HealthReadyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function checkHealth() {
      try {
        const [liveRes, readyRes] = await Promise.all([
          healthApi.getLive(),
          healthApi.getReady(),
        ]);
        setLive(liveRes);
        setReady(readyRes);
      } catch (e) {
        console.error('Health check probe error:', e);
      } finally {
        setLoading(false);
      }
    }
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 transition-colors">
      <Navbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-white to-slate-50 dark:from-slate-900 dark:to-slate-950 border-b border-slate-200/80 dark:border-slate-800 py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-300 text-xs font-semibold mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Powered Campus Recruitment &amp; Eligibility Platform</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight max-w-4xl mx-auto leading-tight">
            AI-Powered <span className="bg-gradient-to-r from-brand-600 to-indigo-600 dark:from-brand-400 dark:to-indigo-400 bg-clip-text text-transparent">Placement Intelligence</span> System
          </h1>

          <p className="mt-4 text-base sm:text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed">
            A modular monolithic platform combining deterministic academic eligibility, weighted skill compatibility scoring, and AI-assisted recruitment management for collegiate institutions.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/student">
              <Button size="lg" icon={<GraduationCap className="w-4 h-4" />}>
                Student Portal
              </Button>
            </Link>
            <Link to="/tpo">
              <Button variant="secondary" size="lg" icon={<Users className="w-4 h-4" />}>
                TPO Console
              </Button>
            </Link>
            <Link to="/recruiter">
              <Button variant="outline" size="lg" icon={<Briefcase className="w-4 h-4" />}>
                Recruiter Hub
              </Button>
            </Link>
            <Link to="/admin">
              <Button variant="ghost" size="lg" icon={<ShieldCheck className="w-4 h-4" />}>
                Admin
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Live System Diagnostic Probe */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-8 w-full z-10">
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-md p-5 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800 gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                  Full-Stack Architecture Health Status
                </h2>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Real-time communication probe between React (Port 5173) and FastAPI (Port 8000)
              </p>
            </div>
            <div className="flex items-center gap-2">
              {loading ? (
                <Badge variant="neutral">Probing Backend...</Badge>
              ) : live?.status === 'alive' ? (
                <Badge variant="success">FastAPI: Alive</Badge>
              ) : (
                <Badge variant="danger">FastAPI: Offline</Badge>
              )}

              {ready?.database?.status === 'connected' ? (
                <Badge variant="success">PostgreSQL: Connected</Badge>
              ) : (
                <Badge variant="warning">PostgreSQL: Standby / Configuring</Badge>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 text-xs">
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
              <div className="text-slate-500 dark:text-slate-400 font-medium">FastAPI Engine</div>
              <div className="font-semibold text-slate-800 dark:text-slate-100 text-sm mt-0.5">
                {live ? `${live.app} (v1.0.0)` : 'Connecting to http://127.0.0.1:8000...'}
              </div>
              <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">
                Liveness: {live?.status === 'alive' ? '200 OK (/health/live)' : 'Checking...'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
              <div className="text-slate-500 dark:text-slate-400 font-medium">PostgreSQL Relational DB</div>
              <div className="font-semibold text-slate-800 dark:text-slate-100 text-sm mt-0.5">
                {ready?.database?.status === 'connected'
                  ? `Connected (${ready.database.latency_ms}ms latency)`
                  : 'PostgreSQL Configured (.env ready)'}
              </div>
              <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">
                Async SQLAlchemy 2.0 + Alembic Driver
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-100 dark:border-slate-800">
              <div className="text-slate-500 dark:text-slate-400 font-medium">AI Intelligence Layer</div>
              <div className="font-semibold text-slate-800 dark:text-slate-100 text-sm mt-0.5">
                Provider: {ready?.ai_engine?.active_provider ? ready.ai_engine.active_provider.toUpperCase() : 'MOCK MODE'}
              </div>
              <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">
                Zero hardcoded models • Gemini & OpenAI Configurable
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Role Navigation Gateways */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Four Tailored User Experiences</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Unified portals connecting students, placement cells, recruiters, and administrators</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Student Card */}
          <Link to="/student" className="group">
            <Card hoverable className="h-full flex flex-col justify-between border-slate-200 dark:border-slate-800 group-hover:border-brand-500/50">
              <div>
                <div className="w-10 h-10 rounded-lg bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 flex items-center justify-center mb-4 group-hover:bg-brand-600 group-hover:text-white transition-colors">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-base text-slate-900 dark:text-slate-100">Student Portal</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                  Private scope: Academic profile, resume parsing preview, eligibility checking, skill-gap analysis, and AI career guidance.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs font-semibold text-brand-600 dark:text-brand-400">
                <span>View Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </Card>
          </Link>

          {/* TPO Card */}
          <Link to="/tpo" className="group">
            <Card hoverable className="h-full flex flex-col justify-between border-slate-200 dark:border-slate-800 group-hover:border-indigo-500/50">
              <div>
                <div className="w-10 h-10 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-4 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                  <Users className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-base text-slate-900 dark:text-slate-100">TPO Console</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                  Institutional scope: Campus placement KPIs, department-wise analytics, drive coordination, and student eligibility queries.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                <span>View Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </Card>
          </Link>

          {/* Recruiter Card */}
          <Link to="/recruiter" className="group">
            <Card hoverable className="h-full flex flex-col justify-between border-slate-200 dark:border-slate-800 group-hover:border-sky-500/50">
              <div>
                <div className="w-10 h-10 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center mb-4 group-hover:bg-sky-600 group-hover:text-white transition-colors">
                  <Briefcase className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-base text-slate-900 dark:text-slate-100">Recruiter Hub</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                  Corporate scope: Job creation with cutoffs, candidate pipeline, score-based ranking, and interview advancement.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs font-semibold text-sky-600 dark:text-sky-400">
                <span>View Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </Card>
          </Link>

          {/* Admin Card */}
          <Link to="/admin" className="group">
            <Card hoverable className="h-full flex flex-col justify-between border-slate-200 dark:border-slate-800 group-hover:border-slate-500/50">
              <div>
                <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 flex items-center justify-center mb-4 group-hover:bg-slate-800 group-hover:text-white transition-colors">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-base text-slate-900 dark:text-slate-100">System Admin</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                  Platform scope: Institution setup, user lifecycle management, AI provider diagnostics, and security auditing.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
                <span>View Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </Card>
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
};
