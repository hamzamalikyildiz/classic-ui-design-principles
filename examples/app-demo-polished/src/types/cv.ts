export type ApplicationStatus = "accepted" | "in_review" | "draft" | "failed";

export interface ScoreRevision {
  id: string;
  label: string;
  score: number;
}

export interface ScoreBreakdownItem {
  label: string;
  value: number;
}

export type RecommendationStatus = "accepted" | "pending" | "dismissed";

export interface Recommendation {
  id: string;
  delta: string;
  title: string;
  status: RecommendationStatus;
}

export interface InterviewQuestion {
  id: string;
  question: string;
  answer: string | null;
  score: string | null;
  status: "answered" | "partial";
}

export interface Application {
  id: string;
  candidate: string;
  role: string;
  company: string;
  score: number;
  salary: number | null;
  status: ApplicationStatus;
  updatedLabel: string;
  updatedAt: string;
  skills: string[];
  scoreHistory: ScoreRevision[];
  scoreBreakdown: ScoreBreakdownItem[];
  recommendations: Recommendation[];
  interviewQuestions: InterviewQuestion[];
}

export interface SeedPayload {
  applications: Application[];
}
