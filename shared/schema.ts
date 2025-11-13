import { z } from "zod";

export const sectors = ["transport", "industry", "energy", "waste", "buildings"] as const;
export type Sector = typeof sectors[number];

export const timeIntervals = ["monthly", "yearly", "custom"] as const;
export type TimeInterval = typeof timeIntervals[number];

export const dataTypes = ["historical", "forecast"] as const;
export type DataType = typeof dataTypes[number];

export interface EmissionData {
  areaId: string;
  areaName: string;
  date: string;
  transport: number;
  industry: number;
  energy: number;
  waste: number;
  buildings: number;
  total: number;
  type: DataType;
}

export interface AreaInfo {
  id: string;
  name: string;
  coordinates: [number, number];
  bounds: [[number, number], [number, number]];
}

export interface LeaderboardEntry {
  rank: number;
  areaId: string;
  areaName: string;
  emissions: number;
  trend: "up" | "down" | "stable";
  trendPercentage: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  password: string;
}

export const emissionQuerySchema = z.object({
  areaId: z.string().optional(),
  sector: z.enum(sectors).optional(),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
  dataType: z.enum(dataTypes).optional(),
  interval: z.enum(timeIntervals).optional(),
});

export type EmissionQuery = z.infer<typeof emissionQuerySchema>;

export const signupSchema = z.object({
  email: z.string().email("Invalid email address"),
  name: z.string().min(2, "Name must be at least 2 characters"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export type SignupInput = z.infer<typeof signupSchema>;

export const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

export type LoginInput = z.infer<typeof loginSchema>;
