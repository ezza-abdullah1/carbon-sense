import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle,
  Clock,
  TrendingUp,
  Shield,
  BarChart3,
  Lightbulb,
  CheckCircle2,
  Download,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  Database,
  Search,
  Brain,
  FileText,
  Sparkles,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { useState } from "react";
import { RecommendationFeedback } from "@/components/recommendation-feedback";
import { RecommendationChatPanel } from "@/components/recommendation-chat-panel";

interface PipelineTraceStep {
  step: number;
  name: string;
  status: string;
  duration_ms: number;
  data: Record<string, any>;
  error?: string;
}

interface PipelineTrace {
  total_duration_ms: number;
  steps: PipelineTraceStep[];
  step_count: number;
}

interface RecommendationsResponse {
  success: boolean;
  recommendation_id?: string;
  query: {
    area_name: string;
    area_id: string;
    sector: string;
    coordinates: { lat: number; lng: number };
  };
  recommendations: {
    summary: string;
    immediate_actions: string[];
    long_term_strategies: string[];
    policy_recommendations: string[];
    monitoring_metrics: string[];
    risk_factors: string[];
  };
  confidence?: {
    overall: number;
    evidence_strength: number;
    data_completeness: number;
    geographic_relevance: number;
  };
  pipeline_trace?: PipelineTrace;
  from_cache?: boolean;
  raw_response?: string;
  generated_at: string;
}

const STEP_ICONS: Record<number, React.ReactNode> = {
  1: <Search className="h-4 w-4" />,
  2: <Database className="h-4 w-4" />,
  3: <FileText className="h-4 w-4" />,
  4: <Brain className="h-4 w-4" />,
  5: <Sparkles className="h-4 w-4" />,
};

const STEP_COLORS: Record<number, string> = {
  1: 'text-blue-500 bg-blue-500/10 border-blue-500/30',
  2: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30',
  3: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
  4: 'text-purple-500 bg-purple-500/10 border-purple-500/30',
  5: 'text-cyan-500 bg-cyan-500/10 border-cyan-500/30',
};

function PipelineTracePanel({ trace, fromCache }: { trace?: PipelineTrace; fromCache?: boolean }) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  if (fromCache) {
    return (
      <div className="px-6 py-2 border-b border-border bg-muted/20">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Database className="h-3 w-3" />
          <span>Served from cache</span>
        </div>
      </div>
    );
  }

  if (!trace) return null;

  const toggleStep = (step: number) => {
    const next = new Set(expandedSteps);
    if (next.has(step)) next.delete(step);
    else next.add(step);
    setExpandedSteps(next);
  };

  return (
    <div className="border-b border-border bg-muted/20 flex-shrink-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-2.5 flex items-center justify-between hover:bg-muted/40 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm">
          <Sparkles className="h-4 w-4 text-purple-500" />
          <span className="font-medium">Pipeline Trace</span>
          <Badge variant="secondary" className="text-xs">
            {trace.step_count} steps
          </Badge>
          <span className="text-xs text-muted-foreground">
            {(trace.total_duration_ms / 1000).toFixed(1)}s total
          </span>
        </div>
        {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>

      {isOpen && (
        <div className="px-6 pb-4 space-y-2">
          {/* Timeline bar */}
          <div className="flex gap-0.5 h-2 rounded-full overflow-hidden mb-3">
            {trace.steps.map((step) => {
              const pct = trace.total_duration_ms > 0
                ? (step.duration_ms / trace.total_duration_ms) * 100
                : 100 / trace.step_count;
              const colorClass = step.status === 'error' ? 'bg-red-500' :
                step.step === 1 ? 'bg-blue-500' :
                step.step === 2 ? 'bg-emerald-500' :
                step.step === 3 ? 'bg-amber-500' :
                step.step === 4 ? 'bg-purple-500' : 'bg-cyan-500';
              return (
                <div
                  key={step.step}
                  className={`${colorClass} rounded-sm`}
                  style={{ width: `${Math.max(pct, 3)}%` }}
                  title={`Step ${step.step}: ${step.duration_ms}ms`}
                />
              );
            })}
          </div>

          {/* Steps */}
          {trace.steps.map((step) => {
            const isExpanded = expandedSteps.has(step.step);
            const colors = STEP_COLORS[step.step] || 'text-gray-500 bg-gray-500/10 border-gray-500/30';

            return (
              <div key={step.step} className={`border rounded-lg overflow-hidden ${colors.split(' ').slice(2).join(' ')}`}>
                <button
                  onClick={() => toggleStep(step.step)}
                  className="w-full px-3 py-2 flex items-center gap-3 text-left hover:bg-muted/30 transition-colors"
                >
                  <div className={`flex items-center justify-center w-7 h-7 rounded-full ${colors.split(' ').slice(0, 2).join(' ')}`}>
                    {STEP_ICONS[step.step]}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{step.name}</span>
                      {step.status === 'completed' && <CheckCircle className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />}
                      {step.status === 'error' && <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />}
                      {step.status === 'running' && <Loader2 className="h-3.5 w-3.5 text-amber-500 animate-spin flex-shrink-0" />}
                    </div>
                  </div>

                  <span className="text-xs text-muted-foreground font-mono flex-shrink-0">
                    {step.duration_ms >= 1000
                      ? `${(step.duration_ms / 1000).toFixed(1)}s`
                      : `${step.duration_ms}ms`
                    }
                  </span>

                  {isExpanded ? <ChevronDown className="h-3.5 w-3.5 flex-shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />}
                </button>

                {isExpanded && step.data && Object.keys(step.data).length > 0 && (
                  <div className="px-3 pb-3 border-t border-border/50">
                    <div className="mt-2 space-y-2">
                      {renderStepData(step)}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function renderStepData(step: PipelineTraceStep) {
  const data = step.data;

  // Step 1: Policy retrieval — show retrieved policies
  if (step.step === 1 && data.policies_retrieved) {
    return (
      <>
        <div className="text-xs text-muted-foreground">
          <span className="font-medium">Search query:</span> {data.query}
        </div>
        <div className="text-xs font-medium mt-1">
          Retrieved {data.results_count} policies:
        </div>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {(data.policies_retrieved as any[]).map((p: any, i: number) => (
            <div key={i} className="flex items-center gap-2 text-xs bg-background/50 rounded px-2 py-1.5">
              <span className="font-mono text-muted-foreground w-4">{i + 1}.</span>
              <span className="flex-1 truncate">{p.title}</span>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">{p.country}</Badge>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">{p.year}</Badge>
              <span className="text-emerald-600 font-mono text-[10px] w-10 text-right">
                {(p.relevance_score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </>
    );
  }

  // Step 2: Emissions analysis — show key metrics
  if (step.step === 2) {
    return (
      <>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Area</div>
            <div className="text-xs font-medium">{data.area_name}</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Dominant Sector</div>
            <div className="text-xs font-medium capitalize">{data.dominant_sector}</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Overall Trend</div>
            <div className="text-xs font-medium">
              {data.overall_trend} ({data.trend_percent > 0 ? '+' : ''}{Number(data.trend_percent).toFixed(1)}%)
            </div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Forecast</div>
            <div className="text-xs font-medium capitalize">{data.forecast_direction}</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Historical Records</div>
            <div className="text-xs font-medium">{data.historical_records}</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Forecast Records</div>
            <div className="text-xs font-medium">{data.forecast_records}</div>
          </div>
        </div>
        {data.sector_totals && (
          <div className="mt-1">
            <div className="text-[10px] text-muted-foreground mb-1">Sector Totals (tonnes CO2e)</div>
            <div className="flex gap-1 flex-wrap">
              {Object.entries(data.sector_totals).map(([sector, value]) => (
                <Badge key={sector} variant="secondary" className="text-[10px]">
                  {sector}: {Number(value).toLocaleString()}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </>
    );
  }

  // Step 3: Prompt building
  if (step.step === 3) {
    return (
      <div className="space-y-1.5">
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">System Prompt</div>
            <div className="text-xs font-medium">{data.system_prompt_length?.toLocaleString()} chars</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">User Prompt</div>
            <div className="text-xs font-medium">{data.user_prompt_length?.toLocaleString()} chars</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Est. Tokens</div>
            <div className="text-xs font-medium">~{data.total_tokens_estimate?.toLocaleString()}</div>
          </div>
        </div>
        {data.prompt_preview && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              Preview prompt...
            </summary>
            <pre className="mt-1 p-2 bg-background/50 rounded text-[10px] max-h-32 overflow-y-auto whitespace-pre-wrap">
              {data.prompt_preview}
            </pre>
          </details>
        )}
      </div>
    );
  }

  // Step 4: LLM call
  if (step.step === 4) {
    return (
      <div className="space-y-1.5">
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Model</div>
            <div className="text-xs font-medium">{data.model}</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Temperature</div>
            <div className="text-xs font-medium">{data.temperature}</div>
          </div>
          <div className="bg-background/50 rounded px-2 py-1.5">
            <div className="text-[10px] text-muted-foreground">Response</div>
            <div className="text-xs font-medium">{data.response_length?.toLocaleString()} chars</div>
          </div>
        </div>
        {data.response_preview && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              Preview raw response...
            </summary>
            <pre className="mt-1 p-2 bg-background/50 rounded text-[10px] max-h-32 overflow-y-auto whitespace-pre-wrap">
              {data.response_preview}
            </pre>
          </details>
        )}
      </div>
    );
  }

  // Step 5: Formatting & confidence
  if (step.step === 5) {
    return (
      <div className="space-y-1.5">
        {data.confidence && (
          <div className="grid grid-cols-4 gap-2">
            <div className="bg-background/50 rounded px-2 py-1.5">
              <div className="text-[10px] text-muted-foreground">Overall</div>
              <div className="text-xs font-medium">{Math.round(data.confidence.overall * 100)}%</div>
            </div>
            <div className="bg-background/50 rounded px-2 py-1.5">
              <div className="text-[10px] text-muted-foreground">Evidence</div>
              <div className="text-xs font-medium">{Math.round(data.confidence.evidence_strength * 100)}%</div>
            </div>
            <div className="bg-background/50 rounded px-2 py-1.5">
              <div className="text-[10px] text-muted-foreground">Data</div>
              <div className="text-xs font-medium">{Math.round(data.confidence.data_completeness * 100)}%</div>
            </div>
            <div className="bg-background/50 rounded px-2 py-1.5">
              <div className="text-[10px] text-muted-foreground">Location</div>
              <div className="text-xs font-medium">{Math.round(data.confidence.geographic_relevance * 100)}%</div>
            </div>
          </div>
        )}
        {data.sections_generated && (
          <div className="flex gap-1 flex-wrap">
            {Object.entries(data.sections_generated).map(([key, val]) => (
              <Badge key={key} variant="secondary" className="text-[10px]">
                {key.replace(/_/g, ' ')}: {typeof val === 'boolean' ? (val ? 'Yes' : 'No') : String(val)}
              </Badge>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Fallback: render raw JSON
  return (
    <pre className="text-[10px] p-2 bg-background/50 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

// Helper function to clean text from markdown and LaTeX
function cleanText(str: string): string {
  return str
    // Remove bold markdown
    .replace(/\*\*/g, '')
    // Remove italic markdown
    .replace(/\*/g, '')
    // Convert LaTeX CO2e notation to plain text
    .replace(/\$\\text\{CO\}_2\\text\{e\}\$/g, 'CO₂e')
    .replace(/\$CO_2\$/g, 'CO₂')
    // Remove any remaining LaTeX
    .replace(/\$[^$]+\$/g, '')
    .trim();
}

// Helper function to parse action/strategy strings into structured data
function parseActionString(str: string): { title: string; details: string[] } {
  // Format: "**Title** - [Expected Impact]: ... - [Estimated Cost Range]: ..."
  const boldMatch = str.match(/^\*\*(.+?)\*\*/);
  const title = boldMatch ? cleanText(boldMatch[1]) : cleanText(str.split(' - ')[0]);

  // Extract bracketed sections as details
  // Use lookahead for " - [" (the actual separator) instead of bare dash
  const details: string[] = [];
  const detailMatches = str.matchAll(/\[([^\]]+)\]:\s*(.+?)(?=\s+-\s+\[|$)/g);
  for (const match of detailMatches) {
    details.push(`${cleanText(match[1])}: ${cleanText(match[2])}`);
  }

  return { title, details };
}

function parseStrategyString(str: string): { title: string; details: string[]; milestones: string[] } {
  const boldMatch = str.match(/^\*\*(.+?)\*\*/);
  const title = boldMatch ? cleanText(boldMatch[1]) : cleanText(str.split(' - ')[0]);

  const details: string[] = [];
  const milestones: string[] = [];

  // Extract bracketed sections — use " - [" as separator (not bare dash)
  const detailMatches = str.matchAll(/\[([^\]]+)\]:\s*(.+?)(?=\s+-\s+\[|$)/g);
  for (const match of detailMatches) {
    const label = cleanText(match[1]);
    const value = cleanText(match[2]);

    if (label === 'Key Milestones') {
      // Parse milestones like "Year 1: ... Year 2: ..."
      const yearMatches = value.matchAll(/Year \d+:\s*[^.]+\./g);
      for (const ym of yearMatches) {
        milestones.push(cleanText(ym[0]));
      }
    } else {
      details.push(`${label}: ${value}`);
    }
  }

  return { title, details, milestones };
}

interface RecommendationsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: RecommendationsResponse | null;
  areaName: string;
}

export function RecommendationsModal({
  open,
  onOpenChange,
  data,
  areaName,
}: RecommendationsModalProps) {
  if (!data) return null;

  const { recommendations } = data;

  // Provide safe defaults for all arrays in case they're undefined
  const safeRecommendations = {
    summary: recommendations?.summary || "No analysis summary available.",
    immediate_actions: recommendations?.immediate_actions || [],
    long_term_strategies: recommendations?.long_term_strategies || [],
    policy_recommendations: recommendations?.policy_recommendations || [],
    monitoring_metrics: recommendations?.monitoring_metrics || [],
    risk_factors: recommendations?.risk_factors || [],
  };

  // Function to generate and download report as text file
  const handleDownloadReport = () => {
    const stripMarkdown = (str: string) => {
      return str
        // Remove bold markdown
        .replace(/\*\*/g, '')
        // Remove italic markdown
        .replace(/\*/g, '')
        // Convert LaTeX CO2e notation to plain text
        .replace(/\$\\text\{CO\}_2\\text\{e\}\$/g, 'CO2e')
        .replace(/\$CO_2\$/g, 'CO2')
        .replace(/CO₂e/g, 'CO2e')
        .replace(/CO₂/g, 'CO2')
        // Remove any remaining LaTeX
        .replace(/\$[^$]+\$/g, '')
        // Clean up extra spaces
        .replace(/\s+/g, ' ')
        .trim();
    };

    let report = `EMISSION CONTROL RECOMMENDATIONS REPORT
${'='.repeat(50)}
Area: ${areaName}
Generated: ${new Date(data.generated_at).toLocaleString()}
${'='.repeat(50)}

EMISSION ANALYSIS SUMMARY
${'-'.repeat(30)}
${safeRecommendations.summary}

`;

    if (safeRecommendations.immediate_actions.length > 0) {
      report += `IMMEDIATE ACTIONS (0-6 months)
${'-'.repeat(30)}
`;
      safeRecommendations.immediate_actions.forEach((action, i) => {
        report += `${i + 1}. ${stripMarkdown(action)}\n\n`;
      });
    }

    if (safeRecommendations.long_term_strategies.length > 0) {
      report += `\nLONG-TERM STRATEGIES (6 months - 5 years)
${'-'.repeat(30)}
`;
      safeRecommendations.long_term_strategies.forEach((strategy, i) => {
        report += `${i + 1}. ${stripMarkdown(strategy)}\n\n`;
      });
    }

    if (safeRecommendations.policy_recommendations.length > 0) {
      report += `\nPOLICY RECOMMENDATIONS
${'-'.repeat(30)}
`;
      safeRecommendations.policy_recommendations.forEach((policy, i) => {
        report += `${i + 1}. ${stripMarkdown(policy)}\n\n`;
      });
    }

    if (safeRecommendations.monitoring_metrics.length > 0) {
      report += `\nMONITORING METRICS
${'-'.repeat(30)}
`;
      safeRecommendations.monitoring_metrics.forEach((metric, i) => {
        report += `• ${stripMarkdown(metric)}\n`;
      });
    }

    if (safeRecommendations.risk_factors.length > 0) {
      report += `\n\nRISK FACTORS
${'-'.repeat(30)}
`;
      safeRecommendations.risk_factors.forEach((risk, i) => {
        report += `${i + 1}. ${stripMarkdown(risk)}\n\n`;
      });
    }

    report += `\n${'='.repeat(50)}
Report generated by CarbonSense
`;

    // Create and download the file
    const blob = new Blob([report], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `emission-recommendations-${areaName.replace(/\s+/g, '-').toLowerCase()}-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-[95vw] max-h-[90vh] p-0 gap-0 overflow-hidden flex flex-col">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-border flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-emerald-500/10">
                <Lightbulb className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <DialogTitle className="text-xl">
                  Emission Control Recommendations
                </DialogTitle>
                <DialogDescription className="mt-1">
                  {areaName} • Generated on{" "}
                  {new Date(data.generated_at).toLocaleDateString("en-US", {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
                </DialogDescription>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadReport}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download Report
            </Button>
          </div>
        </DialogHeader>

        {/* Confidence Score Display */}
        {data.confidence && (
          <div className="px-6 py-3 border-b border-border bg-muted/30 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 flex-1">
                <ShieldCheck className={`h-4 w-4 ${
                  data.confidence.overall >= 0.7 ? 'text-emerald-500' :
                  data.confidence.overall >= 0.4 ? 'text-amber-500' : 'text-red-500'
                }`} />
                <span className="text-sm font-medium">Confidence:</span>
                <Progress
                  value={data.confidence.overall * 100}
                  className="h-2 w-24"
                  style={{
                    "--progress-background": data.confidence.overall >= 0.7
                      ? "hsl(160, 60%, 45%)"
                      : data.confidence.overall >= 0.4
                      ? "hsl(45, 93%, 47%)"
                      : "hsl(0, 72%, 51%)",
                  } as React.CSSProperties}
                />
                <span className={`text-sm font-semibold ${
                  data.confidence.overall >= 0.7 ? 'text-emerald-600' :
                  data.confidence.overall >= 0.4 ? 'text-amber-600' : 'text-red-600'
                }`}>
                  {Math.round(data.confidence.overall * 100)}%
                </span>
              </div>
              <div className="flex gap-2">
                <Badge variant="secondary" className="text-xs">
                  Evidence: {Math.round(data.confidence.evidence_strength * 100)}%
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  Data: {Math.round(data.confidence.data_completeness * 100)}%
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  Location: {Math.round(data.confidence.geographic_relevance * 100)}%
                </Badge>
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Trace */}
        <PipelineTracePanel trace={data.pipeline_trace} fromCache={data.from_cache} />

        <div className="flex-1 min-h-0 w-full overflow-y-auto">
          <div className="p-6 space-y-8 max-w-full overflow-hidden">
            {/* Emission Analysis Summary */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                <h3 className="font-semibold text-lg">Emission Analysis Summary</h3>
                {data.recommendation_id && (
                  <div className="ml-auto">
                    <RecommendationFeedback
                      recommendationId={data.recommendation_id}
                      section="summary"
                    />
                  </div>
                )}
              </div>
              <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-4">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {cleanText(safeRecommendations.summary)}
                </p>
              </div>
            </section>

            {/* Immediate Actions */}
            {safeRecommendations.immediate_actions.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="h-5 w-5 text-amber-500" />
                  <h3 className="font-semibold text-lg">Immediate Actions</h3>
                  <Badge variant="outline" className="ml-2 text-amber-600 border-amber-500/30">
                    0-6 months
                  </Badge>
                  {data.recommendation_id && (
                    <div className="ml-auto">
                      <RecommendationFeedback
                        recommendationId={data.recommendation_id}
                        section="immediate_actions"
                      />
                    </div>
                  )}
                </div>
                <div className="grid gap-4">
                  {safeRecommendations.immediate_actions.map((actionStr, index) => {
                    const parsed = parseActionString(actionStr);
                    return (
                      <div
                        key={index}
                        className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow overflow-hidden"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-500/10 text-amber-600 font-semibold text-sm flex-shrink-0">
                            {index + 1}
                          </div>
                          <div className="flex-1 min-w-0 space-y-2">
                            <h4 className="font-medium">{parsed.title}</h4>
                            {parsed.details.length > 0 && (
                              <div className="flex flex-wrap gap-2 pt-1">
                                {parsed.details.map((detail, dIndex) => (
                                  <Badge key={dIndex} variant="secondary" className="text-xs whitespace-normal">
                                    {detail}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Long-term Strategies */}
            {safeRecommendations.long_term_strategies.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="h-5 w-5 text-emerald-500" />
                  <h3 className="font-semibold text-lg">Long-term Strategies</h3>
                  <Badge variant="outline" className="ml-2 text-emerald-600 border-emerald-500/30">
                    6 months - 5 years
                  </Badge>
                  {data.recommendation_id && (
                    <div className="ml-auto">
                      <RecommendationFeedback
                        recommendationId={data.recommendation_id}
                        section="long_term_strategies"
                      />
                    </div>
                  )}
                </div>
                <div className="grid gap-4">
                  {safeRecommendations.long_term_strategies.map((strategyStr, index) => {
                    const parsed = parseStrategyString(strategyStr);
                    return (
                      <div
                        key={index}
                        className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow overflow-hidden"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-emerald-500/10 text-emerald-600 font-semibold text-sm flex-shrink-0">
                            {index + 1}
                          </div>
                          <div className="flex-1 min-w-0 space-y-3">
                            <h4 className="font-medium">{parsed.title}</h4>
                            {parsed.details.length > 0 && (
                              <div className="flex flex-wrap gap-2">
                                {parsed.details.map((detail, dIndex) => (
                                  <Badge key={dIndex} variant="secondary" className="text-xs whitespace-normal">
                                    {detail}
                                  </Badge>
                                ))}
                              </div>
                            )}
                            {parsed.milestones.length > 0 && (
                              <div className="bg-muted/50 rounded-md p-3 mt-2">
                                <p className="text-xs font-medium text-muted-foreground mb-2">
                                  Key Milestones
                                </p>
                                <ul className="space-y-1">
                                  {parsed.milestones.map((milestone, mIndex) => (
                                    <li
                                      key={mIndex}
                                      className="text-xs text-muted-foreground flex items-start gap-2"
                                    >
                                      <CheckCircle2 className="h-3 w-3 mt-0.5 text-emerald-500 flex-shrink-0" />
                                      {milestone}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Policy Recommendations */}
            {safeRecommendations.policy_recommendations.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="h-5 w-5 text-purple-500" />
                  <h3 className="font-semibold text-lg">Policy Recommendations</h3>
                  {data.recommendation_id && (
                    <div className="ml-auto">
                      <RecommendationFeedback
                        recommendationId={data.recommendation_id}
                        section="policy_recommendations"
                      />
                    </div>
                  )}
                </div>
                <div className="grid gap-3">
                  {safeRecommendations.policy_recommendations.map((policy, index) => {
                    const boldMatch = policy.match(/^\*\*(.+?)\*\*:?\s*/);
                    const title = boldMatch ? cleanText(boldMatch[1]) : null;
                    const description = boldMatch ? cleanText(policy.replace(boldMatch[0], '')) : cleanText(policy);

                    return (
                      <div
                        key={index}
                        className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-4 overflow-hidden"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-500/20 text-purple-600 text-xs font-semibold flex-shrink-0">
                            {index + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            {title && <h4 className="font-medium text-sm mb-1">{title}</h4>}
                            <p className="text-sm leading-relaxed text-muted-foreground break-words">{description}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Monitoring Metrics */}
            {safeRecommendations.monitoring_metrics.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 className="h-5 w-5 text-cyan-500" />
                  <h3 className="font-semibold text-lg">Monitoring Metrics</h3>
                  {data.recommendation_id && (
                    <div className="ml-auto">
                      <RecommendationFeedback
                        recommendationId={data.recommendation_id}
                        section="monitoring_metrics"
                      />
                    </div>
                  )}
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {safeRecommendations.monitoring_metrics.map((metric, index) => {
                    const boldMatch = metric.match(/^\*\*(.+?)\*\*:?\s*/);
                    const title = boldMatch ? cleanText(boldMatch[1]) : null;
                    const description = boldMatch ? cleanText(metric.replace(boldMatch[0], '')) : cleanText(metric);

                    return (
                      <div
                        key={index}
                        className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-3 overflow-hidden"
                      >
                        <div className="flex items-start gap-2">
                          <div className="w-2 h-2 rounded-full bg-cyan-500 mt-1.5 flex-shrink-0" />
                          <div className="min-w-0">
                            {title && <span className="font-medium text-sm">{title}: </span>}
                            <span className="text-sm text-muted-foreground break-words">{description}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Risk Factors */}
            {safeRecommendations.risk_factors.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <h3 className="font-semibold text-lg">Risk Factors</h3>
                  {data.recommendation_id && (
                    <div className="ml-auto">
                      <RecommendationFeedback
                        recommendationId={data.recommendation_id}
                        section="risk_factors"
                      />
                    </div>
                  )}
                </div>
                <div className="grid gap-3">
                  {safeRecommendations.risk_factors.map((risk, index) => {
                    const boldMatch = risk.match(/^\*\*(.+?)\*\*:?\s*/);
                    const title = boldMatch ? cleanText(boldMatch[1]) : null;
                    const description = boldMatch ? cleanText(risk.replace(boldMatch[0], '')) : cleanText(risk);

                    return (
                      <div
                        key={index}
                        className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 overflow-hidden"
                      >
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            {title && <h4 className="font-medium text-sm mb-1">{title}</h4>}
                            <p className="text-sm leading-relaxed text-muted-foreground break-words">{description}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
          </div>

          {data.recommendation_id && (
            <RecommendationChatPanel
              recommendationId={data.recommendation_id}
              areaName={areaName}
              sector={data.query?.sector ?? "transport"}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
