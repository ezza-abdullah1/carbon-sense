import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
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
} from "lucide-react";

interface RecommendationsResponse {
  success: boolean;
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
  raw_response: string;
  generated_at: string;
}

// Helper function to parse action/strategy strings into structured data
function parseActionString(str: string): { title: string; details: string[] } {
  // Format: "**Title** - [Expected Impact]: ... - [Estimated Cost Range]: ..."
  const boldMatch = str.match(/^\*\*(.+?)\*\*/);
  const title = boldMatch ? boldMatch[1] : str.split(' - ')[0];

  // Extract bracketed sections as details
  const details: string[] = [];
  const detailMatches = str.matchAll(/\[([^\]]+)\]:\s*([^[\-]+?)(?=\s*-\s*\[|$)/g);
  for (const match of detailMatches) {
    details.push(`${match[1]}: ${match[2].trim()}`);
  }

  return { title, details };
}

function parseStrategyString(str: string): { title: string; details: string[]; milestones: string[] } {
  const boldMatch = str.match(/^\*\*(.+?)\*\*/);
  const title = boldMatch ? boldMatch[1] : str.split(' - ')[0];

  const details: string[] = [];
  const milestones: string[] = [];

  // Extract bracketed sections
  const detailMatches = str.matchAll(/\[([^\]]+)\]:\s*([^[\-]+?)(?=\s*-\s*\[|$)/g);
  for (const match of detailMatches) {
    const label = match[1];
    const value = match[2].trim();

    if (label === 'Key Milestones') {
      // Parse milestones like "Year 1: ... Year 2: ..."
      const yearMatches = value.matchAll(/Year \d+:\s*[^.]+\./g);
      for (const ym of yearMatches) {
        milestones.push(ym[0].trim());
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
    const stripMarkdown = (str: string) => str.replace(/\*\*/g, '');

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
      <DialogContent className="max-w-4xl max-h-[90vh] p-0 gap-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-border">
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

        <ScrollArea className="h-[calc(90vh-120px)]">
          <div className="p-6 space-y-8">
            {/* Emission Analysis Summary */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                <h3 className="font-semibold text-lg">Emission Analysis Summary</h3>
              </div>
              <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-4">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {safeRecommendations.summary}
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
                </div>
                <div className="grid gap-4">
                  {safeRecommendations.immediate_actions.map((actionStr, index) => {
                    const parsed = parseActionString(actionStr);
                    return (
                      <div
                        key={index}
                        className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-500/10 text-amber-600 font-semibold text-sm flex-shrink-0">
                            {index + 1}
                          </div>
                          <div className="flex-1 space-y-2">
                            <h4 className="font-medium">{parsed.title}</h4>
                            {parsed.details.length > 0 && (
                              <div className="flex flex-wrap gap-2 pt-1">
                                {parsed.details.map((detail, dIndex) => (
                                  <Badge key={dIndex} variant="secondary" className="text-xs">
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
                </div>
                <div className="grid gap-4">
                  {safeRecommendations.long_term_strategies.map((strategyStr, index) => {
                    const parsed = parseStrategyString(strategyStr);
                    return (
                      <div
                        key={index}
                        className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-emerald-500/10 text-emerald-600 font-semibold text-sm flex-shrink-0">
                            {index + 1}
                          </div>
                          <div className="flex-1 space-y-3">
                            <h4 className="font-medium">{parsed.title}</h4>
                            {parsed.details.length > 0 && (
                              <div className="flex flex-wrap gap-2">
                                {parsed.details.map((detail, dIndex) => (
                                  <Badge key={dIndex} variant="secondary" className="text-xs">
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
                </div>
                <div className="grid gap-3">
                  {safeRecommendations.policy_recommendations.map((policy, index) => {
                    const boldMatch = policy.match(/^\*\*(.+?)\*\*:?\s*/);
                    const title = boldMatch ? boldMatch[1] : null;
                    const description = boldMatch ? policy.replace(boldMatch[0], '') : policy;

                    return (
                      <div
                        key={index}
                        className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-4"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-500/20 text-purple-600 text-xs font-semibold flex-shrink-0">
                            {index + 1}
                          </div>
                          <div className="flex-1">
                            {title && <h4 className="font-medium text-sm mb-1">{title}</h4>}
                            <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
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
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {safeRecommendations.monitoring_metrics.map((metric, index) => {
                    const boldMatch = metric.match(/^\*\*(.+?)\*\*:?\s*/);
                    const title = boldMatch ? boldMatch[1] : null;
                    const description = boldMatch ? metric.replace(boldMatch[0], '') : metric;

                    return (
                      <div
                        key={index}
                        className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-3"
                      >
                        <div className="flex items-start gap-2">
                          <div className="w-2 h-2 rounded-full bg-cyan-500 mt-1.5 flex-shrink-0" />
                          <div>
                            {title && <span className="font-medium text-sm">{title}: </span>}
                            <span className="text-sm text-muted-foreground">{description}</span>
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
                </div>
                <div className="grid gap-3">
                  {safeRecommendations.risk_factors.map((risk, index) => {
                    const boldMatch = risk.match(/^\*\*(.+?)\*\*:?\s*/);
                    const title = boldMatch ? boldMatch[1] : null;
                    const description = boldMatch ? risk.replace(boldMatch[0], '') : risk;

                    return (
                      <div
                        key={index}
                        className="bg-red-500/5 border border-red-500/20 rounded-lg p-4"
                      >
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                          <div className="flex-1">
                            {title && <h4 className="font-medium text-sm mb-1">{title}</h4>}
                            <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
