import { useState } from "react";
import { ThumbsDown, ThumbsUp, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { submitRecommendationFeedback } from "@/lib/api";
import type { RecommendationSection } from "@/lib/api";

interface RecommendationFeedbackProps {
  recommendationId: string;
  section: RecommendationSection;
  className?: string;
}

export function RecommendationFeedback({
  recommendationId,
  section,
  className,
}: RecommendationFeedbackProps) {
  const [rating, setRating] = useState<1 | -1 | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [comment, setComment] = useState("");
  const [showCommentBox, setShowCommentBox] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (value: 1 | -1, withComment = "") => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await submitRecommendationFeedback(
        recommendationId,
        section,
        value,
        withComment,
      );
      setRating(value);
      setDone(true);
      if (value === -1) {
        setShowCommentBox(false);
      }
    } catch (err) {
      console.error("Feedback submit failed", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleThumbDown = () => {
    if (rating === -1) return; // already submitted
    setShowCommentBox(true);
    setRating(-1);
  };

  const handleSubmitNegative = async () => {
    await submit(-1, comment.trim());
  };

  return (
    <div className={`flex flex-col gap-2 ${className ?? ""}`}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>Helpful?</span>
        <button
          type="button"
          aria-label="Thumbs up"
          onClick={() => submit(1)}
          disabled={submitting || done}
          className={`p-1 rounded-md border transition-colors ${
            rating === 1
              ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-600"
              : "border-border hover:bg-muted"
          }`}
        >
          <ThumbsUp className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          aria-label="Thumbs down"
          onClick={handleThumbDown}
          disabled={submitting || done}
          className={`p-1 rounded-md border transition-colors ${
            rating === -1
              ? "bg-red-500/15 border-red-500/40 text-red-600"
              : "border-border hover:bg-muted"
          }`}
        >
          <ThumbsDown className="h-3.5 w-3.5" />
        </button>
        {done && (
          <span className="flex items-center gap-1 text-emerald-600">
            <Check className="h-3 w-3" /> Thanks!
          </span>
        )}
      </div>

      {showCommentBox && !done && (
        <div className="flex flex-col gap-2 mt-1">
          <Textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What was off about this section? (optional)"
            className="text-xs min-h-[60px]"
            maxLength={500}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleSubmitNegative}
              disabled={submitting}
            >
              {submitting ? "Sending..." : "Send"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setShowCommentBox(false);
                setRating(null);
              }}
              disabled={submitting}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
